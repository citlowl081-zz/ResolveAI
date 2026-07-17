#!/usr/bin/env python3
"""Secret scanner — report files that may contain API keys, tokens, or secrets.

Usage:  python scripts/check-secrets.py

Scans git-tracked and staged files for patterns matching common secret formats.
Does NOT print full secrets — only file path and rule name.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Patterns that match potential secrets
RULES: list[tuple[str, str]] = [
    ("JWT Token", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    ("API Key (sk-)", r"sk-[A-Za-z0-9]{20,}"),
    ("Private Key (BEGIN)", r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ("AWS Key", r"AKIA[0-9A-Z]{16}"),
    ("GitHub Token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    (".env file", r"(?<!\.example)\.env$"),
]

# Files/directories to skip
SKIP_PATTERNS: list[str] = [
    ".venv/", "node_modules/", ".next/", "__pycache__/", ".git/",
    ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    "package-lock.json", ".tsbuildinfo", ".pyc",
    ".env.example",  # allowed
    ".md",  # markdown files — source references in docs
]

# Known test placeholder values (skip these)
SKIP_VALUES: list[str] = [
    "dev-secret-change-in-production",
    "resolveai-dev",
    "resolveai-test",
    "testpass123",
    "demo123456",
    "admin123456",
    "password123",
    "change-me-in-production",
    "sk-ant-xxxxxxxxxxxxxxxx",
    "sk-xxxxxxxxxxxxxxxx",
    "change-me-to-a-random",
    "sk-abc123def456ghi789jkl012mno345pqr678stu",
]


def get_git_files() -> list[str]:
    """Return all files known to git (tracked + staged)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        return result.stdout.strip().split("\n") if result.stdout else []
    except Exception:
        return []


def should_skip(path: str) -> bool:
    for pat in SKIP_PATTERNS:
        if pat in path:
            return True
    return False


def check_file(filepath: str) -> list[tuple[str, str]]:
    """Scan one file and report only rule names and paths, never content."""
    findings: list[tuple[str, str]] = []
    full_path = PROJECT_ROOT / filepath

    # Check filename
    for rule_name, pattern in RULES:
        if rule_name == ".env file" and re.search(pattern, filepath):
            if not filepath.endswith(".env.example"):
                findings.append((rule_name, filepath))

    if should_skip(filepath):
        return findings

    try:
        content = full_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    for rule_name, pattern in RULES:
        if rule_name == ".env file":
            continue  # already checked above
        for match in re.finditer(pattern, content):
            found = match.group()
            # Skip known test placeholders
            if any(pv in found or found in pv for pv in SKIP_VALUES):
                continue
            findings.append((rule_name, filepath))

    return findings


def main() -> int:
    print("Secret Scanner — ResolveAI")
    print(f"  Project: {PROJECT_ROOT}")
    print()

    files = get_git_files()
    if not files:
        print("  WARNING: Could not get git file list.")
        print("  Run from the project root with git available.")
        return 1

    all_findings: list[tuple[str, str]] = []
    for f in files:
        if f:
            all_findings.extend(check_file(f))

    if all_findings:
        print(f"  ⚠  {len(all_findings)} potential issue(s) found:\n")
        for rule, detail in all_findings:
            print(f"  [{rule}] {detail}")
        print()
        print("  Review the files above. Do NOT commit real secrets.")
        return 1
    else:
        print("  ✓ No secrets detected in tracked files.")
        print("  ✓ .env is NOT tracked (expected).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
