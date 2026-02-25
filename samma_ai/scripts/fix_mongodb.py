#!/usr/bin/env python3
"""
MongoDB Fix Script for Samma AI
Provides options to fix MongoDB authentication issues
"""

import subprocess
import sys
import os

def check_mongodb_status():
    """Check if MongoDB is running and with what flags"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'mongod' in line and '--auth' in line:
                print("✓ MongoDB is running WITH authentication")
                return True, True
            elif 'mongod' in line:
                print("✓ MongoDB is running WITHOUT authentication")
                return True, False
        print("✗ MongoDB is not running")
        return False, False
    except Exception as e:
        print(f"Error checking MongoDB: {e}")
        return False, False

def update_env_no_auth():
    """Update .env to use MongoDB without auth"""
    env_path = '/mnt/sda1/mango1_home/pala-platform/samma_ai/backend/.env'
    mongo_uri = 'mongodb://localhost:27017/samma_ai'

    # Read current .env
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Update MONGO_URI
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('MONGO_URI='):
            lines[i] = f'MONGO_URI={mongo_uri}\n'
            updated = True
            break

    if not updated:
        lines.append(f'\nMONGO_URI={mongo_uri}\n')

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)

    print(f"✓ Updated .env with: MONGO_URI={mongo_uri}")

def main():
    print("🔧 Samma AI - MongoDB Fix Script\n")

    running, has_auth = check_mongodb_status()

    if not running:
        print("\n❌ MongoDB is not running!")
        print("Please start MongoDB first:")
        print("  sudo systemctl start mongod")
        print("  OR")
        print("  sudo mongod --dbpath /var/lib/mongodb --bind_ip_all")
        sys.exit(1)

    if has_auth:
        print("\n⚠️  MongoDB is running with --auth flag")
        print("This requires credentials, but none are configured in .env")
        print("\nOptions:")
        print("  1. Restart MongoDB without --auth (recommended for development)")
        print("  2. Create MongoDB user and update .env with credentials")
        print("\nFor option 1, run:")
        print("  sudo systemctl stop mongod")
        print("  sudo mongod --dbpath /var/lib/mongodb --bind_ip_all --noauth")
        print("\nFor option 2, you need mongosh or mongo CLI to create users")
    else:
        print("\n✓ MongoDB is running without authentication")
        print("Updating .env to use correct connection string...")
        update_env_no_auth()
        print("\n✅ Configuration updated!")
        print("\nNext step: Restart backend")
        print("  cd /mnt/sda1/mango1_home/pala-platform/samma_ai/backend")
        print("  pkill -f 'flask run' && nohup python run.py &")

if __name__ == '__main__':
    main()
