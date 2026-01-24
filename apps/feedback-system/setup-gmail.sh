#!/bin/bash

echo "=== Gmail SMTP Setup for Feedback System ==="
echo ""
echo "This script will configure Gmail SMTP for sending feedback reports."
echo ""

# Prompt for Gmail credentials
read -p "Enter your Gmail address: " GMAIL_USER
read -sp "Enter your Gmail App Password (16 characters): " GMAIL_APP_PASSWORD
echo ""
echo ""

# Validate inputs
if [ -z "$GMAIL_USER" ] || [ -z "$GMAIL_APP_PASSWORD" ]; then
    echo "❌ Error: Email and password are required"
    exit 1
fi

# Backup .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backed up .env file"

# Update .env file
sed -i "s/^GMAIL_USER=.*/GMAIL_USER=$GMAIL_USER/" .env
sed -i "s/^GMAIL_APP_PASSWORD=.*/GMAIL_APP_PASSWORD=$GMAIL_APP_PASSWORD/" .env

# Also update SMTP config
sed -i "s/^SMTP_USER=.*/SMTP_USER=$GMAIL_USER/" .env
sed -i "s/^SMTP_PASS=.*/SMTP_PASS=$GMAIL_APP_PASSWORD/" .env
sed -i "s/^SMTP_FROM=.*/SMTP_FROM=$GMAIL_USER/" .env

echo "✓ Updated .env file with Gmail credentials"
echo ""

# Restart backend to load new config
echo "Restarting backend service..."
docker-compose restart backend
sleep 5

echo ""
echo "✅ Gmail SMTP configured successfully!"
echo ""
echo "Test the email service with:"
echo "  docker-compose exec backend node test-email.js your@email.com food_court"
echo ""
