"""Validated theme data and reversible sessions, independent of Blender UI."""

from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
import tempfile
import stat
from dataclasses import dataclass, field
from pathlib import Path


MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
_PATH = re.compile(r"preferences\.(?:themes|ui_styles)\[0\](?:\.[a-z][a-z_0-9]*(?:\[\d+\])?)+\Z")
_SESSIONS = {}  # Keep live sessions reachable until explicit cancel/confirm.


class ValidationError(ValueError):
    pass


class ConflictError(RuntimeError):
    def __init__(self, paths):
        self.paths = tuple(sorted(paths))
        super().__init__(f"External changes conflict with this operation: {', '.join(self.paths)}")


class ApplyError(RuntimeError):
    def __init__(self, cause, rollback_errors=()):
        self.rollback_errors = tuple(rollback_errors)
        super().__init__(f"Theme application failed: {cause}; rollback errors: {self.rollback_errors}")


@dataclass(frozen=True)
class Field:
    path: str
    kind: str
    length: int = 0
    subtype: str = ""
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    editable: bool = True
    group: str = ""
    label: str = ""

    def validate(self, value):
        def scalar(item):
            if self.kind == "BOOLEAN":
                valid = type(item) is bool
            elif self.kind == "STRING":
                valid = isinstance(item, str) and len(item) <= 4096
            elif self.kind == "ENUM":
                valid = isinstance(item, str) and item in self.choices
            elif self.kind in {"FLOAT", "INT"}:
                valid = type(item) is int if self.kind == "INT" else type(item) in {int, float}
                if valid:
                    try:
                        valid = math.isfinite(item)
                    except OverflowError:
                        valid = False
                if valid and self.minimum is not None:
                    valid = item >= self.minimum
                if valid and self.maximum is not None:
                    valid = item <= self.maximum
            else:
                valid = False
            if not valid:
                raise ValidationError(f"Invalid value for {self.path}")
            return item

        if self.length:
            if not isinstance(value, (list, tuple)) or len(value) != self.length:
                raise ValidationError(f"Expected {self.length} components for {self.path}")
            return [scalar(item) for item in value]
        return scalar(value)


class Registry:
    def __init__(self, fields, recipes, *, build_hash):
        self.fields = {}
        for spec in fields:
            if not _PATH.fullmatch(spec.path) or spec.path in self.fields:
                raise ValidationError(f"Invalid or duplicate catalog path: {spec.path}")
            self.fields[spec.path] = spec
        self.editable_paths = frozenset(path for path, spec in self.fields.items() if spec.editable)
        self.recipes = {}
        for name, paths in recipes.items():
            paths = tuple(paths)
            if not paths or len(paths) != len(set(paths)) or not set(paths) <= self.editable_paths:
                raise ValidationError(f"Invalid recipe: {name}")
            self.recipes[name] = paths
        self.build_hash = build_hash

    def validate(self, values, *, complete=False, allow_metadata=False):
        if not isinstance(values, dict):
            raise ValidationError("Values must be an object")
        allowed = set(self.fields) if allow_metadata else self.editable_paths
        if not set(values) <= allowed or (complete and set(values) != allowed):
            raise ValidationError("Unknown, disallowed or missing theme fields")
        return {path: self.fields[path].validate(value) for path, value in values.items()}


@dataclass(frozen=True)
class ChangeReport:
    changed: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()


_RECOVERY_STAGES = frozenset({
    "draft", "applying", "preview", "failed", "cancelled",
    "cancelled_with_conflicts", "confirmed",
})
_AUTO_SAVE_PATH = "preferences.use_preferences_save"


@dataclass(frozen=True)
class RecoveryConflict:
    path: str
    actual: object
    initial: object


@dataclass(frozen=True)
class RecoveryPlan:
    restore: tuple[tuple[str, object], ...]
    conflicts: tuple[RecoveryConflict, ...]
    requires_choice: bool
    recorded_conflicts: tuple[str, ...] = ()


def parse_recovery(document, registry):
    """Validate and copy a schema-1 or schema-2 journal without modifying it."""
    if not isinstance(document, dict):
        raise ValidationError("Recovery journal must be an object")
    version = document.get("schema_version")
    expected = {
            "format", "schema_version", "build_hash", "stage", "initial",
            "auto_save", "owned", "pending", "conflicts"}
    if type(version) is int and version == 2:
        expected |= {"decisions", "restore_pending", "restore_before", "settled"}
    if set(document) != expected:
        raise ValidationError("Unexpected recovery fields")
    if (document["format"] != "theme-studio-recovery"
            or type(version) is not int or version not in {1, 2}):
        raise ValidationError("Unsupported recovery format")
    if not isinstance(document["build_hash"], str) or document["build_hash"] != registry.build_hash:
        raise ValidationError("Recovery journal targets a different Blender build")
    if (not isinstance(document["stage"], str) or document["stage"] not in _RECOVERY_STAGES
            or type(document["auto_save"]) is not bool):
        raise ValidationError("Invalid recovery state")
    initial = registry.validate(document["initial"], complete=True, allow_metadata=True)
    if not isinstance(document["owned"], dict) or not isinstance(document["pending"], dict):
        raise ValidationError("Invalid recovery value maps")
    owned = registry.validate(document["owned"])
    pending = {}
    for path, entry in document["pending"].items():
        if path not in registry.editable_paths or not isinstance(entry, dict) or set(entry) != {"before", "requested"}:
            raise ValidationError("Invalid pending recovery value")
        pending[path] = {
            "before": registry.validate({path: entry["before"]})[path],
            "requested": registry.validate({path: entry["requested"]})[path],
        }
    if document["stage"] in {"confirmed", "cancelled"} and pending:
        raise ValidationError("Terminal recovery journal contains pending writes")
    conflicts = document["conflicts"]
    if not isinstance(conflicts, list) or any(
            not isinstance(path, str) or (path not in registry.editable_paths and path != _AUTO_SAVE_PATH)
            for path in conflicts) or len(conflicts) != len(set(conflicts)):
        raise ValidationError("Invalid recovery conflicts")
    decisions, restore_pending, restore_before, settled = {}, {}, {}, ()
    if version == 2:
        raw_decisions = document["decisions"]
        raw_restore = document["restore_pending"]
        raw_before = document["restore_before"]
        raw_settled = document["settled"]
        if not isinstance(raw_decisions, dict) or not isinstance(raw_restore, dict) or not isinstance(raw_before, dict):
            raise ValidationError("Invalid recovery decisions")
        allowed_decisions = set(owned) | set(pending) | set(conflicts)
        for path, choice in raw_decisions.items():
            if (not isinstance(path, str) or path not in registry.editable_paths and path != _AUTO_SAVE_PATH
                    or path not in allowed_decisions
                    or not isinstance(choice, str) or choice not in {"restore", "keep"}):
                raise ValidationError("Invalid recovery decision")
            if path == _AUTO_SAVE_PATH and choice != "keep":
                raise ValidationError("Auto-save recovery may only be kept")
        restore_pending = registry.validate(raw_restore)
        restore_before = registry.validate(raw_before)
        if any(restore_pending[path] != initial[path] for path in restore_pending):
            raise ValidationError("Pending recovery target does not match initial value")
        if not set(restore_pending) <= set(raw_decisions) or any(
                raw_decisions[path] != "restore" for path in restore_pending):
            raise ValidationError("Invalid pending restorations")
        if not set(restore_before) <= set(restore_pending):
            raise ValidationError("Invalid restoration observations")
        if not isinstance(raw_settled, list) or any(
                not isinstance(path, str) or path not in raw_decisions for path in raw_settled
                ) or len(raw_settled) != len(set(raw_settled)):
            raise ValidationError("Invalid settled recovery paths")
        settled = tuple(sorted(raw_settled))
    return {
        "format": document["format"], "schema_version": version, "build_hash": document["build_hash"],
        "stage": document["stage"], "initial": initial,
        "auto_save": document["auto_save"],
        "owned": owned, "pending": pending, "conflicts": tuple(sorted(conflicts)),
        "decisions": decisions if version == 1 else dict(raw_decisions),
        "restore_pending": restore_pending, "restore_before": restore_before, "settled": settled,
    }


def _reviewed_registry(build_hash):
    if not isinstance(build_hash, str):
        raise ValidationError("Recovery journal build hash must be text")
    catalogs = {
        "9e2066aef7ef": "catalog-5.2.1.json",
        "f75ffda59776": "catalog.json",
    }
    filename = catalogs.get(build_hash)
    if filename is None:
        raise ValidationError("Recovery journal targets an unknown Blender build")
    data = read_document(Path(__file__).with_name(filename))
    if data.get("build_hash") != build_hash:
        raise ValidationError("Reviewed recovery catalog build mismatch")
    return Registry([Field(**spec) for spec in data["fields"]], data["recipes"], build_hash=build_hash)


def classify_recovery(document, registry):
    """Classify a journal without changing it or the active registry."""
    if not isinstance(document, dict):
        return "invalid", "Recovery journal must be an object"
    target = document.get("build_hash")
    if not isinstance(target, str):
        return "invalid", "Recovery journal build hash must be text"
    foreign = target != registry.build_hash
    try:
        catalog = _reviewed_registry(target) if foreign else registry
    except (ValidationError, OSError) as exc:
        return "incompatible", str(exc)
    try:
        journal = parse_recovery(document, catalog)
    except (ValidationError, TypeError, ValueError) as exc:
        return "invalid", str(exc)
    if foreign:
        if journal["stage"] not in {"confirmed", "cancelled"}:
            return "incompatible", "Recovery journal is unfinished for a different Blender build"
        if (journal["owned"] or journal["pending"] or journal["conflicts"]
                or journal["restore_pending"] or journal["restore_before"]
                or journal["settled"] or journal["decisions"]):
            return "incompatible", "Foreign terminal recovery journal contains unresolved work"
        return "resolved", "Terminal recovery journal targets a reviewed different Blender build"
    if journal["stage"] in {"confirmed", "cancelled"}:
        return "resolved", "Terminal recovery journal has no remaining work"
    if journal["schema_version"] == 2 and journal["restore_pending"]:
        return "pending", "Recovery journal has pending restorations"
    return "pending", "Recovery journal may require recovery"


def _check_recovery_components(path):
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValidationError("Recovery paths may not contain links or reparse points")


def _recovery_source(path):
    path = Path(path)
    if ".." in path.parts or not path.name.startswith("recovery-") or path.suffix.lower() != ".json":
        raise ValidationError("Not a recovery journal path")
    _check_recovery_components(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValidationError("Recovery source must be a regular file")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
            raise ValidationError("Recovery journal changed while reading")
        raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValidationError("Recovery journal exceeds the supported size")
    return path, info, raw


def _recovery_digest(expected_digest):
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_digest):
        raise ValidationError("Invalid recovery digest")
    return expected_digest.lower()


def archive_recovery(path, expected_digest):
    """Preserve an exact copy and acknowledge only that version; never move the source."""
    digest = _recovery_digest(expected_digest)
    path, source_stat, raw = _recovery_source(path)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValidationError("Recovery journal changed before archival")
    archive_root = path.parent / "archive"
    _check_recovery_components(archive_root)
    if archive_root.exists() and not archive_root.is_dir():
        raise ValidationError("Unsafe recovery archive directory")
    archive_root.mkdir(exist_ok=True)
    _check_recovery_components(archive_root)
    owned = Path(tempfile.mkdtemp(prefix="recovery-", dir=archive_root))
    _check_recovery_components(owned)
    destination = owned / path.name
    # Failures retain the original and any incomplete archive evidence.
    with destination.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if destination.read_bytes() != raw:
        raise OSError(f"Recovery copy verification failed; evidence retained at {destination}")
    _, current_stat, current = _recovery_source(path)
    if ((current_stat.st_dev, current_stat.st_ino) != (source_stat.st_dev, source_stat.st_ino)
            or current != raw):
        raise ValidationError(f"Recovery journal changed; unconfirmed copy retained at {destination}")
    receipt = {"format": "theme-studio-archive", "schema_version": 1,
               "source_name": path.name, "sha256": digest}
    with (owned / "acknowledged.json").open("xb") as stream:
        stream.write((json.dumps(receipt, sort_keys=True) + "\n").encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    if _recovery_source(path)[2] != raw:
        raise ValidationError(f"Recovery journal changed; previous version retained at {destination}")
    return destination


def is_archived_recovery(path, expected_digest):
    """Recognize consent only while both original and preserved copy match its digest."""
    digest = _recovery_digest(expected_digest)
    path, _, raw = _recovery_source(path)
    if hashlib.sha256(raw).hexdigest() != digest:
        return False
    archive_root = path.parent / "archive"
    if not archive_root.exists():
        return False
    _check_recovery_components(archive_root)
    if not archive_root.is_dir():
        raise ValidationError("Unsafe recovery archive directory")
    expected = {"format": "theme-studio-archive", "schema_version": 1,
                "source_name": path.name, "sha256": digest}
    for receipt in archive_root.glob("recovery-*/acknowledged.json"):
        try:
            _check_recovery_components(receipt)
            if read_document(receipt) != expected:
                continue
            preserved = receipt.parent / path.name
            _, _, copy_bytes = _recovery_source(preserved)
            if hashlib.sha256(copy_bytes).hexdigest() == digest and _recovery_source(path)[2] == raw:
                return True
        except (OSError, ValueError, TypeError):
            continue
    return False


def plan_recovery(document, current_values, registry):
    journal = parse_recovery(document, registry)
    current = registry.validate(current_values)
    required = set(journal["owned"]) | set(journal["pending"])
    if not required <= set(current):
        raise ValidationError("Missing current recovery values")
    if journal["stage"] in {"confirmed", "cancelled"}:
        return RecoveryPlan((), (), False, ())
    restore, conflicts = [], []
    candidates = dict(journal["owned"])
    for path, entry in journal["pending"].items():
        actual = current[path]
        if actual == entry["before"] or actual == entry["requested"]:
            candidates.setdefault(path, journal["initial"][path])
        else:
            conflicts.append(RecoveryConflict(path, copy.deepcopy(actual), copy.deepcopy(journal["initial"][path])))
    for path, recorded in journal["owned"].items():
        if path in journal["pending"]:
            continue
        actual = current[path]
        if actual != recorded:
            conflicts.append(RecoveryConflict(path, copy.deepcopy(actual), copy.deepcopy(journal["initial"][path])))
    for path, value in sorted(candidates.items()):
        if path in journal["pending"]:
            entry = journal["pending"][path]
            eligible = current[path] == entry["before"] or current[path] == entry["requested"]
        else:
            eligible = current[path] == journal["owned"].get(path)
        value = journal["initial"][path]
        if eligible and current[path] != value:
            restore.append((path, copy.deepcopy(value)))
    conflicts.sort(key=lambda item: item.path)
    conflicts.extend(
        RecoveryConflict(path, None, None) for path in journal["conflicts"]
        if path not in {conflict.path for conflict in conflicts}
    )
    conflicts.sort(key=lambda item: item.path)
    return RecoveryPlan(tuple(restore), tuple(conflicts), True, journal["conflicts"])


@dataclass(frozen=True)
class RecoveryExecution:
    settled: tuple[str, ...]
    conflicts: tuple[RecoveryConflict, ...]
    completed: bool


def execute_recovery(registry, backend, journal_path, decisions, *, outcome=None):
    """Apply explicit per-path recovery choices; journal every decision and field transition."""
    path = Path(journal_path)
    document = read_document(path)
    journal = parse_recovery(document, registry)
    if journal["schema_version"] == 1:
        document.update({"schema_version": 2, "decisions": {}, "restore_pending": {},
                         "restore_before": {}, "settled": []})
    if not isinstance(decisions, dict) or any(
            not isinstance(choice, str) or choice not in {"restore", "keep"}
            for choice in decisions.values()):
        raise ValidationError("Recovery choices must map paths to restore or keep")
    decision_paths = set(journal["owned"]) | set(journal["pending"]) | set(journal["conflicts"])
    current = {}
    tracked_paths = set(journal["owned"]) | set(journal["pending"])
    for field_path in sorted(tracked_paths):
        current[field_path] = registry.validate({field_path: backend.read(field_path)})[field_path]
    for field_path, choice in document["decisions"].items():
        if field_path in decisions and decisions[field_path] != choice:
            raise ValidationError("Recovery choice cannot be changed")
    # Decisions are accepted only for fields with recorded ownership or conflicts.
    if set(decisions) - decision_paths:
        raise ValidationError("Choice for unknown recovery path")
    for field_path in sorted(set(decisions) & decision_paths - tracked_paths):
        if field_path != _AUTO_SAVE_PATH:
            current[field_path] = registry.validate({field_path: backend.read(field_path)})[field_path]
    existing = document["decisions"]
    for field_path, choice in decisions.items():
        if field_path in existing and existing[field_path] != choice:
            raise ValidationError("Recovery choice cannot be changed")
        if field_path == _AUTO_SAVE_PATH and choice != "keep":
            raise ValidationError("Auto-save recovery may only be kept")
        existing[field_path] = choice
    # Reconcile current values and insist on explicit choices for every unresolved conflict.
    base_document = {key: value for key, value in document.items()
                     if key not in {"decisions", "restore_pending", "restore_before", "settled"}}
    base_document["schema_version"] = 1
    planning_values = dict(current)
    planning_values.update({p: v for p, v in journal["owned"].items() if p not in planning_values})
    planning_values.update({p: e["requested"] for p, e in journal["pending"].items() if p not in planning_values})
    planned = plan_recovery(base_document, planning_values, registry)
    unresolved = {item.path for item in planned.conflicts}
    for conflict_path in unresolved:
        if conflict_path not in existing:
            raise ConflictError((conflict_path,))
    for field_path in sorted(decision_paths):
        if field_path not in existing:
            if field_path in unresolved:
                raise ConflictError((field_path,))
            existing[field_path] = "restore"
    for field_path, choice in existing.items():
        if choice == "restore" and field_path != _AUTO_SAVE_PATH and field_path not in document["settled"]:
            document["restore_pending"].setdefault(field_path, journal["initial"][field_path])
            if field_path not in document["restore_before"]:
                observed = current[field_path] if field_path in current else registry.validate(
                    {field_path: backend.read(field_path)})[field_path]
                document["restore_before"][field_path] = copy.deepcopy(observed)
    document["conflicts"] = sorted(set(document["conflicts"]) | unresolved)
    document["schema_version"] = 2
    write_document(path, document, overwrite=True)

    for field_path in sorted(set(existing) - set(document["settled"])):
        choice = existing[field_path]
        if choice == "restore":
            target = document["restore_pending"][field_path]
            actual = registry.validate({field_path: backend.read(field_path)})[field_path]
            if actual != target:
                expected = document["restore_before"][field_path]
                safe = actual == expected
                if not safe:
                    raise ConflictError((field_path,))
                if hasattr(backend, "compare_and_write"):
                    written = backend.compare_and_write(field_path, expected, target)
                    if not written:
                        raise ConflictError((field_path,))
                else:
                    backend.write(field_path, target)
                actual = registry.validate({field_path: backend.read(field_path)})[field_path]
                if actual != target:
                    if actual != expected:
                        raise ConflictError((field_path,))
                    raise ValidationError(f"Recovery readback mismatch for {field_path}")
        document["settled"].append(field_path)
        document["settled"].sort()
        write_document(path, document, overwrite=True)

    all_paths = set(journal["owned"]) | set(journal["pending"]) | set(journal["conflicts"])
    complete = all_paths <= set(document["settled"]) and outcome in {"confirmed", "cancelled"}
    if complete:
        path.unlink()
    conflicts = tuple(RecoveryConflict(p, None, journal["initial"].get(p)) for p in sorted(unresolved))
    return RecoveryExecution(tuple(document["settled"]), conflicts, complete)


def _validate_alpha(value):
    if type(value) not in {int, float} or not 0 <= value <= 1 or not math.isfinite(value):
        raise ValidationError("Opacity must be a finite number between 0 and 1")
    return value


def _validate_rgb(value):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or any(
            type(component) not in {int, float} or not math.isfinite(component) or not 0 <= component <= 1
            for component in value):
        raise ValidationError("Palette color requires finite RGB components between 0 and 1")
    return tuple(value)


@dataclass(frozen=True)
class Profile:
    name: str
    values: dict
    protected: frozenset[str] = field(default_factory=frozenset)


class Draft:
    def __init__(self, registry, values, protected=()):
        self.registry = registry
        self._values = copy.deepcopy(registry.validate(values, complete=True))
        self._baseline = copy.deepcopy(self._values)
        self._palette_rgb = {}
        if not set(protected) <= registry.editable_paths:
            raise ValidationError("Invalid protected field")
        self._protected = set(protected)
        self._undo = []
        self._redo = []
        self._transaction_depth = 0
        self._transaction_before = None

    def __deepcopy__(self, memo):
        duplicate = type(self).__new__(type(self))
        memo[id(self)] = duplicate
        duplicate.registry = self.registry
        duplicate._values = copy.deepcopy(self._values, memo)
        duplicate._baseline = copy.deepcopy(self._baseline, memo)
        duplicate._palette_rgb = copy.deepcopy(self._palette_rgb, memo)
        duplicate._protected = set(self._protected)
        # Snapshots stay internal; undo/redo copy them before restoring live state.
        duplicate._undo = list(self._undo)
        duplicate._redo = list(self._redo)
        duplicate._transaction_depth = self._transaction_depth
        duplicate._transaction_before = copy.deepcopy(self._transaction_before, memo)
        return duplicate

    def _snapshot(self):
        return (copy.deepcopy(self._values), set(self._protected),
                copy.deepcopy(self._palette_rgb), copy.deepcopy(self._baseline))

    def _record(self, before):
        if self._transaction_depth:
            return
        after = self._snapshot()
        if before != after:
            self._undo.append(before)
            self._redo.clear()

    @contextmanager
    def transaction(self):
        """Batch edits into one undo step (e.g. a continuous picker drag)."""
        outer = self._transaction_depth == 0
        before = self._snapshot()
        if outer:
            self._transaction_before = before
        self._transaction_depth += 1
        try:
            yield self
        except BaseException:
            self._transaction_depth -= 1
            self._values, self._protected, self._palette_rgb, self._baseline = copy.deepcopy(before)
            if outer:
                self._transaction_before = None
            raise
        else:
            self._transaction_depth -= 1
            if outer:
                before = self._transaction_before
                self._transaction_before = None
                self._record(before)

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self._snapshot())
        self._values, self._protected, self._palette_rgb, self._baseline = copy.deepcopy(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self._snapshot())
        self._values, self._protected, self._palette_rgb, self._baseline = copy.deepcopy(self._redo.pop())
        return True

    @property
    def values(self):
        return copy.deepcopy(self._values)

    @property
    def protected(self):
        return frozenset(self._protected)

    def value(self, path):
        if path not in self._values:
            raise ValidationError("Unknown or non-editable theme field")
        return copy.deepcopy(self._values[path])

    def set(self, path, value):
        value = self.registry.validate({path: value})[path]
        before = None if self._transaction_depth else self._snapshot()
        self._values[path] = copy.deepcopy(value)
        self._protected.add(path)
        self._record(before)

    def protect(self, path, enabled=True):
        if path not in self.registry.editable_paths or type(enabled) is not bool:
            raise ValidationError("Invalid protected field")
        before = None if self._transaction_depth else self._snapshot()
        if enabled:
            self._protected.add(path)
        else:
            self._protected.discard(path)
        self._record(before)

    def replace_profile(self, profile):
        if not isinstance(profile, Profile):
            raise ValidationError("Expected a profile")
        values = self.registry.validate(profile.values, complete=True)
        if not isinstance(profile.protected, frozenset) or not profile.protected <= self.registry.editable_paths:
            raise ValidationError("Invalid protected fields")
        before = None if self._transaction_depth else self._snapshot()
        self._values = copy.deepcopy(values)
        self._baseline = copy.deepcopy(values)
        self._protected = set(profile.protected)
        self._palette_rgb = {}
        self._record(before)

    def apply_color(self, recipe, rgb):
        before = None if self._transaction_depth else self._snapshot()
        paths = self.registry.recipes.get(recipe)
        if paths is None:
            raise ValidationError(f"Unknown recipe: {recipe}")
        if not isinstance(rgb, (list, tuple)) or len(rgb) != 3:
            raise ValidationError("Color operation requires RGB")
        updates = {}
        for path in paths:
            spec = self.registry.fields[path]
            if spec.subtype not in {"COLOR", "COLOR_GAMMA"} or spec.length not in {3, 4}:
                raise ValidationError(f"Not a color recipe: {recipe}")
            value = spec.validate(list(rgb) + self._values[path][3:])
            if path not in self._protected:
                updates[path] = value
        changed = tuple(path for path, value in updates.items() if value != self._values[path])
        self._values.update(updates)
        self._record(before)
        return ChangeReport(changed, tuple(path for path in paths if path in self._protected))

    def palette_color(self, key, anchor):
        from .palette import palette_group
        group = palette_group(self.registry, key)
        if group is None or anchor not in group["paths"]:
            raise ValidationError("Invalid palette group or anchor")
        state = self._palette_rgb.get(key)
        return tuple(state[1] if state else self._baseline[anchor][:3])

    def set_alpha(self, path, alpha):
        alpha = _validate_alpha(alpha)
        value = self.value(path)
        spec = self.registry.fields[path]
        if spec.kind != "FLOAT" or spec.subtype not in {"COLOR", "COLOR_GAMMA"} or spec.length != 4:
            raise ValidationError("This field does not expose an alpha channel")
        self.set(path, value[:3] + [alpha])

    def apply_palette(self, key, paths, anchor, rgb):
        from .palette import palette_group, transform_color
        group = palette_group(self.registry, key)
        paths = tuple(paths)
        if group is None or paths != group["paths"] or anchor != group["anchor"]:
            raise ValidationError("Invalid palette group, paths or anchor")
        rgb = _validate_rgb(rgb)
        updates = {}
        for path in paths:
            spec = self.registry.fields.get(path)
            if spec is None or spec.subtype not in {"COLOR", "COLOR_GAMMA"} or spec.length not in {3, 4}:
                raise ValidationError(f"Not a palette color field: {path}")
            transformed = (copy.deepcopy(self._baseline[path])
                           if tuple(rgb) == tuple(self._baseline[anchor][:3])
                           else transform_color(self._baseline[path], self._baseline[anchor], rgb))
            if spec.length == 4:
                transformed[3] = self._values[path][3]
            updates[path] = spec.validate(transformed)
        before = None if self._transaction_depth else self._snapshot()
        changed = tuple(path for path in paths
                        if path not in self._protected and updates[path] != self._values[path])
        for path in paths:
            if path not in self._protected:
                self._values[path] = updates[path]
        self._palette_rgb[key] = (paths, rgb, anchor)
        self._record(before)
        return ChangeReport(changed, tuple(path for path in paths if path in self._protected))

    def apply_alpha(self, recipe, alpha):
        """Change only RGBA opacity, atomically; never invent alpha for RGB."""
        before = None if self._transaction_depth else self._snapshot()
        alpha = _validate_alpha(alpha)
        paths = self.registry.recipes.get(recipe)
        if paths is None:
            raise ValidationError(f"Unknown recipe: {recipe}")
        supported, unsupported, updates = [], [], {}
        for path in paths:
            spec = self.registry.fields[path]
            if spec.kind != "FLOAT" or spec.subtype not in {"COLOR", "COLOR_GAMMA"} or spec.length not in {3, 4}:
                raise ValidationError(f"Not a color recipe: {recipe}")
            if spec.length == 3:
                unsupported.append(path)
                continue
            supported.append(path)
            value = spec.validate(self._values[path][:3] + [alpha])
            if path not in self._protected:
                updates[path] = value
        if not supported:
            raise ValidationError("This group contains only RGB fields; opacity is not supported")
        changed = tuple(path for path, value in updates.items() if value != self._values[path])
        self._values.update(updates)
        self._record(before)
        return ChangeReport(changed, tuple(path for path in supported if path in self._protected),
                            unsupported=tuple(unsupported))

    def profile(self, name):
        return Profile(name, self.values, self.protected)


def _reject_constant(value):
    raise ValidationError(f"Non-finite JSON constant: {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_document(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_DOCUMENT_BYTES + 1)
        if len(raw) > MAX_DOCUMENT_BYTES:
            raise ValidationError("Document exceeds size limit")
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValidationError("Invalid JSON document") from exc
    if not isinstance(document, dict):
        raise ValidationError("Document must be an object")
    return document


def _encode_document(document):
    encoded = (json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_DOCUMENT_BYTES:
        raise ValidationError("Document exceeds size limit")
    return encoded


def write_document(path, document, *, overwrite=False):
    """Atomically publish on the same volume; never silently replace a file.

    Exclusive creation uses a hard link to a fully flushed temporary file.
    Unsupported filesystems fail closed instead of falling back to partial IO.
    """
    path = Path(path)
    encoded = _encode_document(document)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _validate_profile(profile, registry):
    if not isinstance(profile.name, str) or not 1 <= len(profile.name.strip()) <= 80:
        raise ValidationError("Profile name must contain 1–80 characters")
    values = registry.validate(profile.values, complete=True)
    if not isinstance(profile.protected, frozenset) or not profile.protected <= registry.editable_paths:
        raise ValidationError("Invalid protected fields")
    return values


def save_profile(path, profile, registry, *, overwrite=False):
    values = _validate_profile(profile, registry)
    write_document(path, {
        "format": "theme-studio-profile", "schema_version": 1,
        "build_hash": registry.build_hash, "name": profile.name,
        "values": values, "protected": sorted(profile.protected),
    }, overwrite=overwrite)


def load_profile(path, registry):
    data = read_document(path)
    if set(data) != {"format", "schema_version", "build_hash", "name", "values", "protected"}:
        raise ValidationError("Unexpected profile fields")
    if data["format"] != "theme-studio-profile" or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValidationError("Unsupported profile format")
    if data["build_hash"] != registry.build_hash:
        raise ValidationError("Profile targets a different Blender build; migration is not implemented")
    if not isinstance(data["protected"], list) or not all(isinstance(p, str) for p in data["protected"]):
        raise ValidationError("Invalid protected fields")
    if len(data["protected"]) != len(set(data["protected"])):
        raise ValidationError("Duplicate protected fields")
    profile = Profile(data["name"], data["values"], frozenset(data["protected"]))
    _validate_profile(profile, registry)
    return profile


def load_catalog(build_hash=None):
    try:
        import bpy
    except ImportError:
        bpy = None

    if build_hash is None and bpy is not None:
        build_hash = getattr(bpy.app, "build_hash", None)
        if build_hash is not None and isinstance(build_hash, (bytes, bytearray)):
            build_hash = build_hash.decode()
    if build_hash is None:
        raise ValidationError("Blender build hash is required for catalog selection")

    catalogs = {
        "9e2066aef7ef": "catalog-5.2.1.json",
        "f75ffda59776": "catalog.json",
    }

    filename = None
    if build_hash in catalogs:
        filename = catalogs[build_hash]
    else:
        major, minor, _ = (0, 0, 0)
        if bpy is not None:
            major, minor, _ = getattr(bpy.app, "version", (0, 0, 0))
        if major == 5 and minor >= 3:
            filename = "catalog.json"
        elif major == 5 and minor == 2:
            filename = "catalog-5.2.1.json"
        elif major == 5:
            filename = "catalog-5.2.1.json"
        elif major >= 5:
            filename = "catalog.json"
        else:
            raise ValidationError("Theme Studio requires Blender 5.x")

    data = read_document(Path(__file__).with_name(filename))
    if data.get("build_hash") != build_hash:
        data = dict(data)
        data["build_hash"] = build_hash
    return Registry([Field(**spec) for spec in data["fields"]], data["recipes"], build_hash=build_hash)


class Session:
    """One owned theme session. Backend implements read/write and auto-save IO.

    GUI lifecycle hooks, concurrency ownership and startup recovery UI belong
    to the future integration layer, not to this UI-independent engine.
    """

    def __init__(self, registry, backend, recovery_path):
        self._lease_key = getattr(backend, "session_key", id(backend))
        if self._lease_key in _SESSIONS:
            raise RuntimeError("Another theme session already owns this backend")
        self.registry = registry
        self.backend = backend
        self.recovery_path = Path(recovery_path)
        self.initial = registry.validate({p: backend.read(p) for p in registry.fields}, complete=True, allow_metadata=True)
        self.original_auto_save = backend.get_auto_save()
        if type(self.original_auto_save) is not bool:
            raise ValidationError("Invalid backend auto-save state")
        self.draft = Draft(registry, {p: v for p, v in self.initial.items() if p in registry.editable_paths})
        self._expected = copy.deepcopy(self.initial)
        self._owned = set()
        self._uncertain = {}
        self._history = []
        self._auto_save_owned = False
        # Undo granularity collapses continuous same-field live ticks; the
        # cap only bounds memory for very long sessions.
        self.HISTORY_LIMIT = 200
        self.faulted = False
        self.active = False
        self._journal("draft", overwrite=False)
        self.active = True
        _SESSIONS[self._lease_key] = self

    def _require_active(self, *, allow_faulted=False):
        if not self.active:
            raise RuntimeError("Theme session is closed")
        if self.faulted and not allow_faulted:
            raise RuntimeError("Rollback was incomplete; cancel/recovery is required before further preview")

    def _journal(self, stage, *, pending=None, owned=None, conflicts=(), overwrite=True):
        document = {
            "format": "theme-studio-recovery", "schema_version": 1,
            "build_hash": self.registry.build_hash, "stage": stage,
            "initial": self.initial, "auto_save": self.original_auto_save,
            "owned": owned if owned is not None else {p: self._expected[p] for p in sorted(self._owned)},
            "pending": pending or {}, "conflicts": list(conflicts),
        }
        write_document(self.recovery_path, document, overwrite=overwrite)
        try:
            if read_document(self.recovery_path) != document:
                raise OSError("Recovery journal failed readback verification")
        except Exception:
            if not overwrite:
                try:
                    if self.recovery_path.read_bytes() == _encode_document(document):
                        self.recovery_path.unlink()
                except OSError:
                    pass
            raise

    def _conflicts(self, paths):
        conflicts = []
        for path in paths:
            actual = self.backend.read(path)
            possible = self._uncertain.get(path)
            if actual != self._expected[path] and (possible is None or actual not in possible):
                conflicts.append(path)
        return tuple(sorted(conflicts))

    def _apply(self, values):
        values = self.registry.validate(values)
        conflicts = self._conflicts(values)
        if conflicts:
            raise ConflictError(conflicts)
        before = {p: self.backend.read(p) for p in values}
        values = {p: v for p, v in values.items() if before[p] != v}
        if not values:
            return {}, {}
        pending = {p: {"before": before[p], "requested": v} for p, v in values.items()}
        self._journal("applying", pending=pending)
        auto_before = self.backend.get_auto_save()
        auto_owned_before = self._auto_save_owned
        attempted = []
        readback = {}
        try:
            self.backend.set_auto_save(False)
            self._auto_save_owned = True
            for path, value in values.items():
                attempted.append(path)  # Include setters that mutate and then fail.
                self.backend.write(path, value)
                readback[path] = self.registry.fields[path].validate(self.backend.read(path))
            prospective = {p: self._expected[p] for p in self._owned}
            for path, value in readback.items():
                if value == self.initial[path]:
                    prospective.pop(path, None)
                else:
                    prospective[path] = value
            self._journal("preview", owned=prospective)
        except Exception as cause:
            rollback_errors = []
            rollback_failed = set()
            for path in reversed(attempted):
                try:
                    self.backend.write(path, before[path])
                    if self.backend.read(path) != before[path]:
                        raise RuntimeError("Readback mismatch during rollback")
                except Exception:
                    rollback_errors.append(path)
                    rollback_failed.add(path)
            try:
                if not rollback_errors:
                    self.backend.set_auto_save(auto_before)
                    self._auto_save_owned = auto_owned_before
                else:
                    self.faulted = True
                    # Track mutations that could not be restored so a later
                    # cancellation can retry them instead of losing ownership.
                    for path in rollback_failed:
                        try:
                            actual = self.backend.read(path)
                        except Exception:
                            self._uncertain[path] = (copy.deepcopy(before[path]), copy.deepcopy(values[path]))
                            self._owned.add(path)
                            continue
                        self._expected[path] = copy.deepcopy(actual)
                        if actual != self.initial[path]:
                            self._owned.add(path)
                        else:
                            self._owned.discard(path)
                        self._uncertain.pop(path, None)
                self._journal("failed" if rollback_errors else "preview" if self._owned else "draft", pending=pending if rollback_errors else None)
            except Exception:
                rollback_errors.append("journal_or_auto_save")
            if rollback_errors:
                self.faulted = True
            raise ApplyError(cause, rollback_errors) from cause
        for path, value in readback.items():
            self._expected[path] = copy.deepcopy(value)
            self._uncertain.pop(path, None)
            if value == self.initial[path]:
                self._owned.discard(path)
            else:
                self._owned.add(path)
            self.draft._values[path] = copy.deepcopy(value)
        return {p: before[p] for p in values}, readback

    def preview(self):
        self._require_active()
        desired = self.draft.values
        paths = self._owned | {p for p, v in desired.items() if v != self.initial[p]}
        before, after = self._apply({p: desired[p] for p in sorted(paths)})
        if after:
            # One live drag keeps ticking the same field; fold equal chain
            # links instead of adding an undo entry per 100 ms tick.
            if self._history and before == self._history[-1][1]:
                last_before = self._history[-1][0]
                self._history[-1] = (last_before, after)
            else:
                self._history.append((before, after))
            del self._history[:-self.HISTORY_LIMIT]
        return ChangeReport(tuple(after))

    def restore_previous(self):
        self._require_active()
        if not self._history:
            return ChangeReport()
        before, _ = self._history[-1]
        _, readback = self._apply(before)
        self._history.pop()
        return ChangeReport(tuple(readback))

    def _finish(self, stage, conflicts):
        conflicts = list(conflicts)
        # Do not overwrite an external change to the auto-save setting.
        current_auto = self.backend.get_auto_save()
        if self._auto_save_owned and current_auto is False:
            self.backend.set_auto_save(self.original_auto_save)
        elif self._auto_save_owned and self.original_auto_save is False:
            conflicts.append("preferences.use_preferences_save")
        pending = {path: {"before": before, "requested": requested}
                   for path, (before, requested) in self._uncertain.items()}
        self._journal(stage, pending=pending, conflicts=conflicts)
        self.active = False
        _SESSIONS.pop(self._lease_key, None)
        return tuple(sorted(conflicts))

    def cancel(self):
        self._require_active(allow_faulted=True)
        conflicts = self._conflicts(self._owned)
        restore_paths = self._owned - set(conflicts)
        before, _ = self._apply({p: self.initial[p] for p in sorted(restore_paths)})
        for path in restore_paths:
            self._uncertain.pop(path, None)
            self._expected[path] = copy.deepcopy(self.initial[path])
            self._owned.discard(path)
        conflicts = self._finish("cancelled_with_conflicts" if conflicts else "cancelled", conflicts)
        return ChangeReport(tuple(before), conflicts=conflicts)

    def confirm(self):
        self._require_active()
        self.preview()
        conflicts = self._conflicts(self._owned)
        conflicts = self._finish("confirmed", conflicts)
        return ChangeReport(conflicts=conflicts)
