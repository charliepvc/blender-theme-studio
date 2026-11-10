"""Safe filesystem helpers for native theme XML output."""

import os
import re
import tempfile
from pathlib import Path


def validate_theme_name(name: str, normalized: str) -> str:
    """Return validated native-normalized filename stem."""
    if not isinstance(normalized, str) or not normalized or normalized in {".", ".."}:
        raise ValueError(f"Invalid theme name: {name!r}")
    if any(character in normalized for character in ("/", "\\", "\0")):
        raise ValueError(f"Invalid theme name: {name!r}")
    if re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"Invalid theme name: {name!r}")
    isreserved = getattr(os.path, "isreserved", lambda value: False)
    device_name = normalized.split(".", 1)[0].upper()
    if (
        normalized.endswith((".", " "))
        or isreserved(normalized)
        or device_name in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    ):
        raise ValueError(f"Invalid theme name: {name!r}")
    return normalized


def _canonical(path: Path) -> Path:
    absolute = Path(os.path.abspath(os.fspath(path)))
    _reject_reparse_components(absolute)
    return absolute.resolve(strict=False)


def _reject_reparse_components(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if current.is_symlink() or getattr(info, "st_file_attributes", 0) & getattr(
            __import__("stat"), "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        ):
            raise ValueError(f"Reparse point not allowed: {current}")


def theme_output_paths(library_root: Path, preset_root: Path, stem: str) -> tuple[Path, ...]:
    """Plan canonical, deduplicated XML destinations without creating folders."""
    validate_theme_name(stem, stem)
    library = _canonical(Path(library_root))
    presets = _canonical(Path(preset_root))
    destinations = (
        _canonical(library / "themes" / f"{stem}.xml"),
        _canonical(presets / f"{stem}.xml"),
    )
    for path in destinations:
        _reject_reparse_components(path)
    return tuple(dict.fromkeys(destinations))


def _read_expected(path: Path, expected: bytes | None) -> None:
    try:
        actual = path.read_bytes()
    except FileNotFoundError:
        actual = None
    if actual != expected:
        raise FileExistsError(f"Destination changed since confirmation: {path}")


def _stage(path: Path, xml: bytes) -> Path:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(xml)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        staged.unlink(missing_ok=True)
        raise
    return staged


def _retain_recovery(target: Path, prior: bytes) -> Path:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.recovery.", suffix=".bak", dir=target.parent)
    recovery = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(prior)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        recovery.unlink(missing_ok=True)
        raise
    return recovery


def write_theme_files(
    xml: bytes, paths: tuple[Path, ...], *, expected: dict[Path, bytes | None]
) -> None:
    """Write all destinations, restoring only unchanged operation-owned outputs."""
    raw_paths = tuple(Path(path) for path in paths)
    for path in raw_paths:
        _reject_reparse_components(Path(os.path.abspath(os.fspath(path))))
    targets = tuple(dict.fromkeys(_canonical(path) for path in raw_paths))
    if not targets:
        raise ValueError("At least one theme output path is required")
    for path in expected:
        _reject_reparse_components(Path(os.path.abspath(os.fspath(path))))
    expected_by_path = {_canonical(Path(path)): value for path, value in expected.items()}
    if set(targets) != set(expected_by_path):
        raise ValueError("Expected-byte map must match theme output paths")

    staged: dict[Path, Path] = {}
    snapshots: dict[Path, bytes | None] = {}
    recovery: dict[Path, Path] = {}
    committed: list[Path] = []
    failed_targets: set[Path] = set()
    try:
        for target in targets:
            _reject_reparse_components(target)
            _read_expected(target, expected_by_path[target])
            snapshots[target] = expected_by_path[target]
        for target in targets:
            if not target.parent.is_dir():
                raise FileNotFoundError(f"Output directory does not exist: {target.parent}")
            staged[target] = _stage(target, xml)
            if snapshots[target] is not None:
                recovery[target] = _retain_recovery(target, snapshots[target])
        for target in targets:
            if snapshots[target] is None:
                os.link(staged[target], target)
                committed.append(target)
                staged[target].unlink()
                staged.pop(target)
            else:
                _read_expected(target, snapshots[target])
                os.replace(staged[target], target)
                committed.append(target)
                staged.pop(target)
    except Exception as error:
        rollback_errors = []
        for target in reversed(committed):
            try:
                current = target.read_bytes()
                if current != xml:
                    raise FileExistsError(f"Concurrent replacement preserved: {target}")
                prior = snapshots[target]
                if prior is None:
                    target.unlink()
                else:
                    restore = _stage(target, prior)
                    try:
                        if target.read_bytes() != xml:
                            raise FileExistsError(f"Concurrent replacement preserved: {target}")
                        os.replace(restore, target)
                    finally:
                        restore.unlink(missing_ok=True)
                    if target in recovery:
                        if target.read_bytes() == prior:
                            recovery[target].unlink(missing_ok=True)
                            recovery.pop(target, None)
                        else:
                            raise OSError(f"Restored bytes differ from approved snapshot: {target}")
            except Exception as rollback_error:
                evidence = recovery.get(target)
                rollback_errors.append(
                    f"{target}: {rollback_error}; prior bytes at {evidence}" if evidence else f"{target}: {rollback_error}"
                )
                if evidence:
                    failed_targets.add(target)
        detail = f"Failed to write theme files: {error}; affected: {', '.join(map(str, targets))}"
        if rollback_errors:
            detail += f"; rollback incomplete: {'; '.join(rollback_errors)}"
            retained = [str(recovery[target]) for target in failed_targets]
            if retained:
                detail += f"; evidence retained at: {'; '.join(retained)}"
        raise OSError(detail) from error
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
        for target, backup in tuple(recovery.items()):
            if target not in failed_targets:
                backup.unlink(missing_ok=True)
