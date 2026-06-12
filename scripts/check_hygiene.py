#!/usr/bin/env python3
"""Build-in-public guardrail (decision 0001): fail if anything that looks
like real financial data or a secret is tracked by git.

Run from the repo root: python scripts/check_hygiene.py
Exit code 0 = clean, 1 = violations found. Suitable as a pre-commit hook.
"""

import re
import subprocess
import sys
from pathlib import Path

# The only CSVs allowed in the repo (decision 0011).
FIXTURE_WHITELIST = re.compile(r"^backend/tests/fixtures/synthetic_[^/]+\.csv$")

FORBIDDEN_PATHS = [
    (re.compile(r"\.(sqlite3?|db)$", re.I), "database file"),
    (re.compile(r"(^|/)\.env($|\.(?!example))", re.I), "env file"),
    (re.compile(r"\.(csv|ofx|qfx|qbo)$", re.I), "bank-statement format"),
]

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{16,}"), "hardcoded credential"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "API key literal"),
]

TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".toml", ".yml", ".yaml", ".ps1", ".css", ".html", ".env", ".cfg", ".ini", ".txt", ".example"}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def main() -> int:
    violations: list[str] = []

    for path in tracked_files():
        for pattern, label in FORBIDDEN_PATHS:
            if pattern.search(path):
                if FIXTURE_WHITELIST.match(path):
                    continue
                violations.append(f"{path}: {label} must not be tracked")

        file = Path(path)
        if file.suffix.lower() in TEXT_SUFFIXES and file.is_file():
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(text):
                    violations.append(f"{path}: possible {label}")

    if violations:
        print("HYGIENE CHECK FAILED — public repo, private data:", file=sys.stderr)
        for violation in violations:
            print(f"  ✗ {violation}", file=sys.stderr)
        return 1
    print("hygiene check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
