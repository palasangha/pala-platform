#!/usr/bin/env python3
"""
Diagnostic script to check all deployments in MongoDB
Lists deployments regardless of user, showing user ownership and status
"""

import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app
from app.models import mongo
from bson import ObjectId

def diagnose_deployments():
    """Diagnose deployment storage and visibility issues"""

    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("DEPLOYMENT DIAGNOSTIC REPORT")
        print("="*80 + "\n")

        # 1. Count total deployments
        total_count = mongo.db.worker_deployments.count_documents({})
        print(f"📊 TOTAL DEPLOYMENTS IN DATABASE: {total_count}\n")

        if total_count == 0:
            print("❌ NO DEPLOYMENTS FOUND - The supervisor window will be empty!")
            print("\nSolution: Create a new deployment through the supervisor UI.\n")
            return

        # 2. Count by user
        print("📋 DEPLOYMENTS BY USER:\n")
        user_groups = list(mongo.db.worker_deployments.aggregate([
            {'$group': {'_id': '$user_id', 'count': {'$sum': 1}, 'statuses': {'$push': '$status'}}}
        ]))

        for group in user_groups:
            user_id = group['_id']
            count = group['count']
            statuses = group['statuses']

            # Try to find user details
            user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
            user_email = user.get('email', 'UNKNOWN') if user else 'USER NOT FOUND'

            status_summary = {}
            for status in statuses:
                status_summary[status] = status_summary.get(status, 0) + 1

            print(f"  User ID: {user_id}")
            print(f"  Email: {user_email}")
            print(f"  Total Deployments: {count}")
            print(f"  Status Breakdown: {status_summary}")
            print()

        # 3. List all deployments with details
        print("="*80)
        print("📝 ALL DEPLOYMENTS DETAILS:\n")

        deployments = mongo.db.worker_deployments.find().sort('created_at', -1)

        for i, dep in enumerate(deployments, 1):
            user = mongo.db.users.find_one({'_id': dep.get('user_id')})
            user_email = user.get('email', 'UNKNOWN') if user else 'NOT FOUND'

            print(f"\n[{i}] {dep.get('worker_name', 'NO NAME')}")
            print(f"    ID: {dep['_id']}")
            print(f"    Owner: {user_email} ({dep.get('user_id')})")
            print(f"    Host: {dep.get('host')}:{dep.get('port', 22)}")
            print(f"    Status: {dep.get('status', 'UNKNOWN')}")
            print(f"    Health: {dep.get('health_status', 'unknown')}")
            print(f"    Workers: {dep.get('worker_count', 0)}")
            print(f"    Containers: {len(dep.get('containers', []))}")
            print(f"    Created: {dep.get('created_at', 'N/A')}")
            print(f"    Error: {dep.get('error_message', 'None')}")

        # 4. Check current user
        print("\n" + "="*80)
        print("👤 CURRENT USER CHECK:\n")

        # Try to get current logged in user from session or token
        users = list(mongo.db.users.find().limit(5))

        if users:
            print("⚠️  Available users in system:\n")
            for user in users:
                user_id = user['_id']
                email = user.get('email', 'NO EMAIL')

                # Count their deployments
                dep_count = mongo.db.worker_deployments.count_documents({'user_id': user_id})

                print(f"  • {email}")
                print(f"    ID: {user_id}")
                print(f"    Deployments: {dep_count}")
                print()
        else:
            print("❌ No users found in database!\n")

        # 5. Check for deployments with null user_id
        print("="*80)
        print("🔍 DATA INTEGRITY CHECKS:\n")

        null_user = mongo.db.worker_deployments.count_documents({'user_id': None})
        if null_user > 0:
            print(f"⚠️  Found {null_user} deployments with NULL user_id")
            print("   These will NEVER appear in supervisor window (they belong to no one)\n")
        else:
            print("✅ All deployments have valid user_id\n")

        # Check for deployments stuck in 'deploying' state
        deploying_count = mongo.db.worker_deployments.count_documents({'status': 'deploying'})
        if deploying_count > 0:
            print(f"⏳ Found {deploying_count} deployments stuck in 'deploying' state")
            print("   These should eventually transition to 'running' or 'error'\n")

        # 6. Recommendations
        print("="*80)
        print("💡 RECOMMENDATIONS:\n")

        if total_count == 0:
            print("1. Create a new deployment through the supervisor UI")
            print("2. Check the backend logs for any creation errors")
        else:
            # Check if current user has deployments
            current_user = users[0] if users else None
            if current_user:
                current_dep_count = mongo.db.worker_deployments.count_documents(
                    {'user_id': current_user['_id']}
                )
                if current_dep_count == 0:
                    print(f"1. Current user ({current_user.get('email')}) has NO deployments")
                    print(f"   Log in as a different user, or create a new deployment")
                else:
                    print(f"1. Current user HAS {current_dep_count} deployments")
                    print("   Check browser DevTools Network tab for API response")

            if deploying_count > 0:
                print(f"\n2. {deploying_count} deployments are still deploying")
                print("   Wait a moment and refresh, or check backend logs for deployment errors")

            print(f"\n3. Total {total_count} deployments exist")
            print("   If they don't show, it's a user_id mismatch issue")

        print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    diagnose_deployments()
