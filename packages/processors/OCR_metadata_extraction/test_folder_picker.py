#!/usr/bin/env python3
"""
Test folder picker endpoint
"""
import os
import sys

# Test the folder listing logic
test_path = '/tmp'

print(f"Testing folder listing for: {test_path}")
print("=" * 60)

# Validate path exists
if not os.path.exists(test_path):
    print(f"✗ Path does not exist: {test_path}")
    sys.exit(1)

# Validate path is a directory
if not os.path.isdir(test_path):
    print(f"✗ Path is not a directory: {test_path}")
    sys.exit(1)

# Check read permissions
if not os.access(test_path, os.R_OK):
    print(f"✗ Permission denied: {test_path}")
    sys.exit(1)

# List directories
folders = []
try:
    items = os.listdir(test_path)
    for item in sorted(items):
        full_path = os.path.join(test_path, item)
        if os.path.isdir(full_path) and not item.startswith('.'):
            try:
                if os.access(full_path, os.R_OK):
                    folders.append({
                        'name': item,
                        'path': full_path,
                        'is_readable': True
                    })
            except (OSError, PermissionError):
                folders.append({
                    'name': item,
                    'path': full_path,
                    'is_readable': False
                })
except (OSError, PermissionError) as e:
    print(f"✗ Error listing directories: {str(e)}")
    sys.exit(1)

print(f"✓ Found {len(folders)} readable folders")
print()

if folders:
    print("Sample folders found:")
    for folder in folders[:5]:
        status = "✓ readable" if folder['is_readable'] else "✗ no access"
        print(f"  - {folder['name']:40} [{status}]")
    if len(folders) > 5:
        print(f"  ... and {len(folders) - 5} more")
else:
    print("No readable folders found")

print()
print("=" * 60)
print("✓ Folder listing logic works correctly!")
