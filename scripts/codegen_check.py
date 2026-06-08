#!/usr/bin/env python3
"""CI-side codegen drift check.

Re-runs ``scripts/codegen.py`` into a temp directory (via the
``ANIMUS_CODEGEN_OUT_DIR`` override) and diffs the result against the committed
generated pydantic modules under
``animus_plugin_sdk/types/generated/``. Exits non-zero if any byte differs so
PRs that touch the vendored Rust schemas without regenerating get caught.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
COMMITTED_DIR = REPO_ROOT / "animus_plugin_sdk" / "types" / "generated"
CODEGEN_SCRIPT = REPO_ROOT / "scripts" / "codegen.py"


def load_dir(path: Path) -> dict[str, str]:
    return {f.name: f.read_text() for f in sorted(path.glob("*.py"))}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="animus-codegen-check-") as staging:
        result = subprocess.run(
            [sys.executable, str(CODEGEN_SCRIPT)],
            env={"ANIMUS_CODEGEN_OUT_DIR": staging, "PATH": _path()},
            check=False,
        )
        if result.returncode != 0:
            print("codegen failed", file=sys.stderr)
            return result.returncode or 1

        committed = load_dir(COMMITTED_DIR)
        fresh = load_dir(Path(staging))

    drift = False
    for name in sorted(set(committed) | set(fresh)):
        a = committed.get(name)
        b = fresh.get(name)
        if a is None:
            print(f"drift: {name} is generated but not committed", file=sys.stderr)
            drift = True
        elif b is None:
            print(f"drift: {name} is committed but no longer generated", file=sys.stderr)
            drift = True
        elif a != b:
            print(f"drift: {name} differs from regenerated output", file=sys.stderr)
            drift = True

    if drift:
        print("\nRun `python scripts/codegen.py` and commit the result.", file=sys.stderr)
        return 1
    print("codegen output matches committed files")
    return 0


def _path() -> str:
    import os

    return os.environ.get("PATH", "")


if __name__ == "__main__":
    raise SystemExit(main())
