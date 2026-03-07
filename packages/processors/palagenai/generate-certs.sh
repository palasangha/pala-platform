#!/bin/bash

# Production SSL/TLS Certificate Generation Script
# Generates self-signed certificates for development/staging
# For production, replace with CA-signed certificates

set -e

CERTS_DIR="./certs"
CERT_FILE="$CERTS_DIR/server.crt"
KEY_FILE="$CERTS_DIR/server.key"
DAYS=730  # 2 years

echo "=== SSL/TLS Certificate Generation ==="
echo ""

# Create certs directory
mkdir -p "$CERTS_DIR"
echo "✓ Created $CERTS_DIR directory"

# Check if certificates already exist
if [ -f "$CERT_FILE" ] && [ -f "$KEY_FILE" ]; then
    echo "⚠️  Certificates already exist. Skipping generation."
    echo "   To regenerate: rm -f $CERT_FILE $KEY_FILE && $0"
    exit 0
fi

# Generate self-signed certificate (development/staging)
echo "Generating self-signed certificate..."
openssl req -x509 -newkey rsa:4096 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -days "$DAYS" \
  -nodes \
  -subj "/C=IN/ST=Maharashtra/L=Igatpuri/O=Vipassana Research Institute/CN=enrichment.gvpocr.local" \
  -addext "subjectAltName=DNS:enrichment.gvpocr.local,DNS:localhost,IP:127.0.0.1,IP:172.12.0.132"

# Set proper permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "✓ Generated certificate: $CERT_FILE"
echo "✓ Generated private key: $KEY_FILE"
echo ""

# Display certificate details
echo "Certificate Details:"
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After|Public-Key"
echo ""

# Generate certificate fingerprint
echo "Certificate Fingerprint (SHA256):"
openssl x509 -in "$CERT_FILE" -noout -fingerprint -sha256 | sed 's/SHA256 Fingerprint=/  /'
echo ""

# For production, show instructions
cat <<'PRODUCTION'

PRODUCTION DEPLOYMENT INSTRUCTIONS:
===================================

For DEVELOPMENT/STAGING (current setup):
- Self-signed certificates are adequate
- Browsers will show security warnings (expected)
- APIs will use these certificates

For PRODUCTION:
1. Obtain CA-signed certificate from:
   - DigiCert, GlobalSign, Let's Encrypt, etc.

2. Replace certificate files:
   - server.crt: Replace with CA-signed certificate
   - server.key: Replace with private key

3. Optionally create certificate chain:
   - intermediate.crt: Intermediate CA certificate
   - root.crt: Root CA certificate

4. Update docker-compose.enrichment.yml:
   - Add intermediate and root certificates to volumes
   - Update SSL configuration if needed

5. Restart services:
   docker-compose -f docker-compose.enrichment.yml restart review-api cost-api

PRODUCTION
