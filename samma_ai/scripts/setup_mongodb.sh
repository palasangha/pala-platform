#!/bin/bash

# MongoDB Setup Script for Samma AI
# Creates database user and updates .env configuration

echo "🔧 Setting up MongoDB for Samma AI..."

# MongoDB credentials
DB_NAME="samma_ai"
DB_USER="samma_ai_user"
DB_PASS="samma_ai_password_2026"

# Create MongoDB user
echo "Creating MongoDB user..."
docker exec -it $(docker ps -q -f name=mongo) mongosh admin --eval "
  db.createUser({
    user: '$DB_USER',
    pwd: '$DB_PASS',
    roles: [
      { role: 'readWrite', db: '$DB_NAME' }
    ]
  })
"

# If docker approach fails, try direct mongosh
if [ $? -ne 0 ]; then
  echo "Docker approach failed, trying direct mongosh..."
  mongosh admin --eval "
    db.createUser({
      user: '$DB_USER',
      pwd: '$DB_PASS',
      roles: [
        { role: 'readWrite', db: '$DB_NAME' }
      ]
    })
  "
fi

# Update .env file
MONGO_URI="mongodb://${DB_USER}:${DB_PASS}@localhost:27017/${DB_NAME}?authSource=admin"

echo "Updating .env file..."
if grep -q "^MONGO_URI=" ../backend/.env; then
  sed -i "s|^MONGO_URI=.*|MONGO_URI=$MONGO_URI|" ../backend/.env
else
  echo "MONGO_URI=$MONGO_URI" >> ../backend/.env
fi

echo "✅ MongoDB setup complete!"
echo ""
echo "Credentials created:"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Password: $DB_PASS"
echo ""
echo "MONGO_URI updated in backend/.env"
echo ""
echo "⚠️  Next steps:"
echo "  1. Restart the backend: cd backend && ./restart.sh"
echo "  2. Test agent chat to verify conversations are saved"
