#!/usr/bin/env python3
"""
Test the folder listing endpoint without full Flask app
"""
import os
import json
import sys

def test_folder_listing():
    """Simulate the folder listing logic"""
    print("Testing folder listing endpoint logic")
    print("=" * 70)

    # Test different paths
    test_paths = [
        '/tmp',
        '/home',
        '/root',
        '/',
        '/nonexistent',
    ]

    for test_path in test_paths:
        print(f"\nTesting path: {test_path}")
        print("-" * 70)

        # Validate path is provided
        if not test_path:
            print("  ✗ Path parameter required")
            continue

        # Validate path exists
        if not os.path.exists(test_path):
            print(f"  ✗ Path does not exist: {test_path}")
            continue

        # Validate path is a directory
        if not os.path.isdir(test_path):
            print(f"  ✗ Path is not a directory: {test_path}")
            continue

        # Check read permissions
        if not os.access(test_path, os.R_OK):
            print(f"  ✗ Permission denied: {test_path}")
            continue

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
            print(f"  ✗ Error listing directories: {str(e)}")
            continue

        # Print response
        response = {
            'success': True,
            'path': test_path,
            'folders': folders,
            'total': len(folders)
        }

        print(f"  ✓ Success - found {len(folders)} folders")
        if folders:
            print(f"  Sample: {folders[0]['name']}")

    print("\n" + "=" * 70)
    print("✓ Endpoint logic test complete!")

if __name__ == '__main__':
    test_folder_listing()
