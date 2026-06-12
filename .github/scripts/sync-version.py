#!/usr/bin/env python3
"""
Sync pyproject.toml version from a tag or input.
Usage: python sync-version.py <version>
"""
import re
import sys

version = sys.argv[1].lstrip("v")  # strip leading "v" if present

with open("pyproject.toml") as f:
    content = f.read()

content = re.sub(
    r'(?<=^version = ")[^"]+',
    version,
    content,
    flags=re.MULTILINE,
)

with open("pyproject.toml", "w") as f:
    f.write(content)

print(f"Version updated to {version}")
