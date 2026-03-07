#!/bin/bash

# Insert Test Data Script
# Loads sample OCR data into MongoDB for enrichment pipeline testing

set -e

MONGO_USER="${MONGO_USER:-enrichment_user}"
MONGO_PASSWORD="${MONGO_PASSWORD:-changeMe123}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-gvpocr}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================"
echo "Test Data Insertion"
echo "================================"
echo ""
echo "MongoDB Configuration:"
echo "  Host: $MONGO_HOST"
echo "  Port: $MONGO_PORT"
echo "  Database: $MONGO_DB"
echo "  User: $MONGO_USER"
echo ""

# Check if MongoDB is accessible
echo "[1/3] Checking MongoDB connectivity..."
if ! mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to MongoDB"
    exit 1
fi
echo "✓ MongoDB connection successful"
echo ""

# Load sample letters JSON
echo "[2/3] Reading sample letters data..."
if [ ! -f "$SCRIPT_DIR/sample-letters.json" ]; then
    echo "ERROR: sample-letters.json not found"
    exit 1
fi

# Extract sample letters and insert
echo "[3/3] Inserting OCR test data into MongoDB..."

# Create OCR job
OCR_JOB_ID="ocr_test_$(date +%s)"
COLLECTION_ID="goenka_letters"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Read JSON and process each letter
jq '.sample_letters[]' "$SCRIPT_DIR/sample-letters.json" | while read -r letter; do
    LETTER_ID=$(echo "$letter" | jq -r '.id')
    TEXT=$(echo "$letter" | jq -r '.ocr_text')
    CONFIDENCE=$(echo "$letter" | jq -r '.ocr_metadata.confidence')
    LANGUAGE=$(echo "$letter" | jq -r '.ocr_metadata.detected_language')

    # Insert OCR result document
    mongosh \
        --username "$MONGO_USER" \
        --password "$MONGO_PASSWORD" \
        --host "$MONGO_HOST:$MONGO_PORT" \
        --authenticationDatabase admin \
        --quiet \
        --eval "
            db = db.getSiblingDB('$MONGO_DB');
            db.ocr_results.insertOne({
                document_id: '$LETTER_ID',
                ocr_job_id: '$OCR_JOB_ID',
                collection_id: '$COLLECTION_ID',
                text: $letter.ocr_text,
                full_text: $letter.ocr_text,
                confidence: $CONFIDENCE,
                detected_language: '$LANGUAGE',
                blocks: [],
                words: [],
                provider: 'test_data',
                pages: 1,
                created_at: new Date('$TIMESTAMP')
            });
        "

    echo "  ✓ Inserted $LETTER_ID (confidence: $CONFIDENCE)"
done

# Create OCR job document to mark as complete
echo ""
echo "Creating OCR job document..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');
        db.ocr_jobs.insertOne({
            job_id: '$OCR_JOB_ID',
            collection_id: '$COLLECTION_ID',
            status: 'completed',
            documents: [
                { document_id: 'test_letter_001', status: 'completed' },
                { document_id: 'test_letter_002', status: 'completed' },
                { document_id: 'test_letter_003', status: 'completed' },
                { document_id: 'test_letter_004', status: 'completed' },
                { document_id: 'test_letter_005', status: 'completed' }
            ],
            total_documents: 5,
            completed_count: 5,
            error_count: 0,
            metadata: {
                source: 'test_data',
                batch_name: 'E2E_Test_Batch'
            },
            created_at: new Date('$TIMESTAMP'),
            completed_at: new Date('$TIMESTAMP')
        });
    "

echo "✓ OCR job created with ID: $OCR_JOB_ID"

echo ""
echo "================================"
echo "✓ Test Data Inserted Successfully"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Verify OCR job status:"
echo "   mongosh --username $MONGO_USER --password '***' --host $MONGO_HOST:$MONGO_PORT"
echo "   > use gvpocr"
echo "   > db.ocr_jobs.findOne({job_id: '$OCR_JOB_ID'})"
echo ""
echo "2. Monitor enrichment processing:"
echo "   ./monitor-enrichment.sh"
echo ""
echo "3. Check enriched results:"
echo "   mongosh --username $MONGO_USER --password '***' --host $MONGO_HOST:$MONGO_PORT"
echo "   > use gvpocr"
echo "   > db.enriched_documents.count()"
echo ""
