"""Build a local legacy development addon ZIP, not a published Extension."""

import argparse
import os
import tempfile
import zipfile
from pathlib import Path


REQUIRED_FILES = ("__init__.py", "blender_backend.py", "catalog.json", "catalog-5.2.1.json", "contrast.py", "core.py", "labels.py", "palette.py", "preferences.py", "ui.py")


def build_archive(source, output):
    source, output = Path(source), Path(output)
    if not output.parent.is_dir():
        raise ValueError("Output parent directory must already exist")
    for name in REQUIRED_FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing or unsafe package source: {name}")
    fd, temporary = tempfile.mkstemp(prefix=".theme-studio-", suffix=".zip.tmp", dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in REQUIRED_FILES:
                info = zipfile.ZipInfo(f"theme_studio/{name}", date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (source / name).read_bytes())
        with open(temporary, "r+b") as stream:
            os.fsync(stream.fileno())
        os.link(temporary, output)  # Exclusive publication, no overwrite fallback.
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build_archive(Path(__file__).resolve().parents[1] / "theme_studio", args.output)
    print(f"Development addon ZIP: {args.output}")
    print("Legacy local test package; not a final Blender Extension release")


if __name__ == "__main__":
    main()
