#!/usr/bin/env python3
"""
Bump or set the app version across all required files:
- web/src-tauri/tauri.conf.json
- web/src-tauri/Cargo.toml
- web/src-tauri/Cargo.lock
- web/package.json

Usage:
  python3 scripts/bump_version.py <version | patch | minor | major>

Examples:
  python3 scripts/bump_version.py 0.1.5
  python3 scripts/bump_version.py patch
  python3 scripts/bump_version.py minor
  python3 scripts/bump_version.py major
"""

import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TAURI_CONF = REPO_ROOT / "web" / "src-tauri" / "tauri.conf.json"
CARGO_TOML = REPO_ROOT / "web" / "src-tauri" / "Cargo.toml"
CARGO_LOCK = REPO_ROOT / "web" / "src-tauri" / "Cargo.lock"
PACKAGE_JSON = REPO_ROOT / "web" / "package.json"

def get_current_version() -> str:
    content = TAURI_CONF.read_text(encoding="utf-8")
    m = re.search(r'"version"\s*:\s*"([^"]+)"', content)
    if not m:
        raise ValueError(f"Could not find version in {TAURI_CONF}")
    return m.group(1)

def compute_new_version(current: str, arg: str) -> str:
    arg = arg.strip().lstrip("v")
    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Current version '{current}' is not valid semver (X.Y.Z)")

    major, minor, patch = map(int, parts)

    if arg == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif arg == "minor":
        return f"{major}.{minor + 1}.0"
    elif arg == "major":
        return f"{major + 1}.0.0"
    else:
        new_parts = arg.split(".")
        if len(new_parts) != 3 or not all(p.isdigit() for p in new_parts):
            raise ValueError(f"Invalid version target '{arg}'. Expected 'patch', 'minor', 'major', or 'X.Y.Z'")
        return arg

def update_tauri_conf(new_ver: str):
    content = TAURI_CONF.read_text(encoding="utf-8")
    new_content = re.sub(r'("version"\s*:\s*")[^"]+(")', f'\\g<1>{new_ver}\\g<2>', content, count=1)
    TAURI_CONF.write_text(new_content, encoding="utf-8")

def update_cargo_toml(new_ver: str):
    content = CARGO_TOML.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    in_package = False
    new_lines = []
    updated = False
    for line in lines:
        if line.strip() == "[package]":
            in_package = True
            new_lines.append(line)
            continue
        if in_package and line.strip().startswith("["):
            in_package = False
        if in_package and not updated and line.strip().startswith("version"):
            line = re.sub(r'(version\s*=\s*")[^"]+(")', f'\\g<1>{new_ver}\\g<2>', line)
            updated = True
        new_lines.append(line)
    CARGO_TOML.write_text("".join(new_lines), encoding="utf-8")

def update_cargo_lock(new_ver: str):
    content = CARGO_LOCK.read_text(encoding="utf-8")
    pattern = r'(\[\[package\]\]\s*\nname\s*=\s*"tbs-lpdp-app"\s*\nversion\s*=\s*")[^"]+(")'
    if not re.search(pattern, content):
        print(f"Warning: Could not find tbs-lpdp-app entry in {CARGO_LOCK}")
        return
    new_content = re.sub(pattern, f'\\g<1>{new_ver}\\g<2>', content)
    CARGO_LOCK.write_text(new_content, encoding="utf-8")

def update_package_json(new_ver: str):
    content = PACKAGE_JSON.read_text(encoding="utf-8")
    new_content = re.sub(r'("version"\s*:\s*")[^"]+(")', f'\\g<1>{new_ver}\\g<2>', content, count=1)
    PACKAGE_JSON.write_text(new_content, encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        current = get_current_version()
        print(f"Current version: {current}")
        print("Usage: python3 scripts/bump_version.py <version | patch | minor | major>")
        print("Examples:\n  python3 scripts/bump_version.py patch\n  python3 scripts/bump_version.py 0.1.5")
        sys.exit(1)

    target_arg = sys.argv[1]
    current_ver = get_current_version()
    new_ver = compute_new_version(current_ver, target_arg)

    print(f"Bumping version: {current_ver} -> {new_ver}")

    update_tauri_conf(new_ver)
    print(f"  ✓ Updated {TAURI_CONF.relative_to(REPO_ROOT)}")

    update_cargo_toml(new_ver)
    print(f"  ✓ Updated {CARGO_TOML.relative_to(REPO_ROOT)}")

    update_cargo_lock(new_ver)
    print(f"  ✓ Updated {CARGO_LOCK.relative_to(REPO_ROOT)}")

    update_package_json(new_ver)
    print(f"  ✓ Updated {PACKAGE_JSON.relative_to(REPO_ROOT)}")

    print(f"\nDone! Updated version to {new_ver}.")

if __name__ == "__main__":
    main()
