#!/bin/bash

# GVPOCR Mobile Access Setup Script
# This script helps configure the environment for mobile access

set -e

echo "=========================================="
echo "GVPOCR Mobile Access Setup"
echo "=========================================="
echo ""

# Get server IP addresses
echo "Detecting server IP addresses..."
SERVER_IPS=$(hostname -I)
echo "Available IPs: $SERVER_IPS"
echo ""

# Parse IPs into array
IPS_ARRAY=($SERVER_IPS)

echo "Select the IP address accessible from your mobile device:"
echo "(Usually starts with 192.168.x.x or 10.x.x.x for local network)"
echo ""

i=1
for ip in "${IPS_ARRAY[@]}"; do
    echo "$i) $ip"
    ((i++))
done
echo ""

read -p "Enter number (1-${#IPS_ARRAY[@]}): " IP_CHOICE

if [ "$IP_CHOICE" -lt 1 ] || [ "$IP_CHOICE" -gt "${#IPS_ARRAY[@]}" ]; then
    echo "Invalid choice"
    exit 1
fi

SELECTED_IP="${IPS_ARRAY[$((IP_CHOICE-1))]}"
echo ""
echo "Selected IP: $SELECTED_IP"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    exit 1
fi

# Backup original .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
echo "Backed up .env to .env.backup.$(date +%Y%m%d_%H%M%S)"

# Get Google credentials
echo ""
echo "=========================================="
echo "Google OAuth Credentials"
echo "=========================================="
echo ""
echo "You need to create OAuth credentials in Google Cloud Console:"
echo "1. Visit: https://console.cloud.google.com/"
echo "2. Create a project or select existing"
echo "3. Enable Google+ API"
echo "4. Create OAuth 2.0 credentials (Web application)"
echo "5. Add authorized redirect URIs:"
echo "   - http://localhost:5000/api/auth/google/callback"
echo "   - http://$SELECTED_IP:5000/api/auth/google/callback"
echo ""

read -p "Do you have Google OAuth credentials ready? (y/n): " HAS_CREDS

if [ "$HAS_CREDS" != "y" ]; then
    echo ""
    echo "Please create Google OAuth credentials first."
    echo "See GOOGLE_LOGIN_MOBILE_FIX.md for detailed instructions."
    exit 0
fi

echo ""
read -p "Enter Google Client ID: " CLIENT_ID
read -p "Enter Google Client Secret: " CLIENT_SECRET

if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ]; then
    echo "Error: Client ID and Secret are required"
    exit 1
fi

# Update .env file
echo ""
echo "Updating .env file..."

# Update or add Google OAuth settings
sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$CLIENT_ID|" .env
sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$CLIENT_SECRET|" .env
sed -i "s|^GOOGLE_REDIRECT_URI=.*|GOOGLE_REDIRECT_URI=http://$SELECTED_IP:5000/api/auth/google/callback|" .env

# Update CORS origins
CORS_ORIGINS="http://localhost:5173,http://localhost:3000,http://$SELECTED_IP:3000,http://$SELECTED_IP:5173"
sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$CORS_ORIGINS|" .env

echo "✓ Updated GOOGLE_CLIENT_ID"
echo "✓ Updated GOOGLE_CLIENT_SECRET"
echo "✓ Updated GOOGLE_REDIRECT_URI to: http://$SELECTED_IP:5000/api/auth/google/callback"
echo "✓ Updated CORS_ORIGINS to: $CORS_ORIGINS"

# Display configuration summary
echo ""
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo ""
echo "Server IP for mobile access: $SELECTED_IP"
echo ""
echo "Frontend URLs:"
echo "  - Desktop: http://localhost:3000"
echo "  - Mobile:  http://$SELECTED_IP:3000"
echo ""
echo "Backend API URLs:"
echo "  - Desktop: http://localhost:5000/api"
echo "  - Mobile:  http://$SELECTED_IP:5000/api"
echo ""
echo "Google OAuth Redirect URI:"
echo "  http://$SELECTED_IP:5000/api/auth/google/callback"
echo ""

# Remind about Google Cloud Console
echo "=========================================="
echo "⚠️  IMPORTANT: Update Google Cloud Console"
echo "=========================================="
echo ""
echo "Add this redirect URI to your Google OAuth credentials:"
echo "  http://$SELECTED_IP:5000/api/auth/google/callback"
echo ""
echo "Add this origin to authorized JavaScript origins:"
echo "  http://$SELECTED_IP:3000"
echo "  http://$SELECTED_IP:5173"
echo ""

# Ask to restart services
echo ""
read -p "Restart backend and frontend services now? (y/n): " RESTART

if [ "$RESTART" = "y" ]; then
    echo ""
    echo "Restarting services..."
    cd ..
    docker-compose restart backend frontend
    echo ""
    echo "✓ Services restarted"
fi

# Display testing instructions
echo ""
echo "=========================================="
echo "Testing Instructions"
echo "=========================================="
echo ""
echo "From Desktop:"
echo "  1. Open: http://localhost:3000"
echo "  2. Click 'Sign in with Google'"
echo "  3. Should work as expected"
echo ""
echo "From Mobile:"
echo "  1. Ensure mobile is on the same network"
echo "  2. Open: http://$SELECTED_IP:3000"
echo "  3. Click 'Sign in with Google'"
echo "  4. Should redirect to Google login"
echo "  5. After login, should redirect back with tokens"
echo ""
echo "If login fails, check:"
echo "  - Google Cloud Console redirect URIs are correct"
echo "  - Mobile can access http://$SELECTED_IP:3000"
echo "  - Check backend logs: docker-compose logs -f backend"
echo ""
echo "For detailed troubleshooting, see:"
echo "  GOOGLE_LOGIN_MOBILE_FIX.md"
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
