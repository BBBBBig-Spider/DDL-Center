"""Pre-commit guard: refuse to commit per-user local state.

These files are git-ignored by content, but a teammate could still
`git add -f` them. Pushing one teammate's avatar / display name / theme /
sync cache to GitHub would overwrite everyone else's settings on pull —
that is the bug this hook prevents.

Install once per clone (Windows / macOS / Linux):
    git config core.hooksPath .githooks
"""
from __future__ import annotations

import re
import subprocess
import sys

# Patterns that must NEVER appear in a commit.
FORBIDDEN = [
    re.compile(r"^data/\.theme_palette$"),
    re.compile(r"^data/last_.*\.json$"),
    re.compile(r"^data/.*\.db$"),
    re.compile(r".*\.sqlite3$"),
    re.compile(r"^\.env$"),
]


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line.strip()]


def main() -> int:
    violations = []
    for path in staged_files():
        for pat in FORBIDDEN:
            if pat.match(path):
                violations.append((path, pat.pattern))
                break

    if not violations:
        return 0

    print()
    print("Refusing to commit per-user local state:")
    for path, pattern in violations:
        print(f"  {path}  (matches: {pattern})")
    print()
    print("These files are user-specific (theme, avatar, sync caches, DB).")
    print("Pushing them would overwrite teammates' settings on pull.")
    print()
    print("If genuinely intentional, edit .githooks/pre_commit_check.py and")
    print("remove the offending pattern — but think twice.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
