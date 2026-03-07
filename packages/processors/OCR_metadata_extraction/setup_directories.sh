#!/bin/bash
# Script to verify and document all required directories

echo "Checking directory structure..."
echo ""

# Arrays of required directories
DATA_DIRS=("data/Bhushanji" "data/newsletters" "data/dhamma_for_all")
SHARED_DIRS=("shared/temp-images" "shared/uploads" "shared/Bhushanji" "shared/newsletters")
OTHER_DIRS=("backend/uploads" "models" "ssh_keys" "certs")

all_exist=true

echo "✓ Data Directories:"
for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir (missing)"
        all_exist=false
    fi
done

echo ""
echo "✓ Shared Directories:"
for dir in "${SHARED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir (missing)"
        all_exist=false
    fi
done

echo ""
echo "✓ Other Directories:"
for dir in "${OTHER_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir (missing)"
        all_exist=false
    fi
done

echo ""
if $all_exist; then
    echo "✅ All required directories exist!"
else
    echo "⚠️  Some directories are missing"
fi
