#!/bin/bash
# Sync files from source repository to installation repository
set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <source_dir> <install_dir> <version>"
    echo "Example: $0 /workspace /tmp/install 1.0.0"
    exit 1
fi

SOURCE_DIR=$1
INSTALL_DIR=$2
VERSION=${3:-}

echo "📦 Syncing files to installation repository..."
echo "   Source: $SOURCE_DIR"
echo "   Install: $INSTALL_DIR"
echo "   Version: ${VERSION:-current}"

# Create target directory
mkdir -p "$INSTALL_DIR/aitomations-creator"
TARGET="$INSTALL_DIR/aitomations-creator"

# Copy main files
echo "📄 Copying configuration and documentation..."
cp "$SOURCE_DIR/aitomations/config.json" "$TARGET/config.json"
cp "$SOURCE_DIR/docs/install/README.md" "$TARGET/README.md"
cp "$SOURCE_DIR/docs/install/DOCS.md" "$TARGET/DOCS.md"

# Copy icons
echo "🎨 Copying icons..."
if [ -f "$SOURCE_DIR/docs/install/icon.png" ]; then
    cp "$SOURCE_DIR/docs/install/icon.png" "$TARGET/icon.png"
    echo "   ✓ icon.png"
else
    echo "   ⚠️  icon.png not found (required)"
    exit 1
fi

if [ -f "$SOURCE_DIR/docs/install/logo.png" ]; then
    cp "$SOURCE_DIR/docs/install/logo.png" "$TARGET/logo.png"
    echo "   ✓ logo.png"
else
    echo "   ⚠️  logo.png not found, using icon.png as logo"
    cp "$SOURCE_DIR/docs/install/icon.png" "$TARGET/logo.png"
fi

# Generate changelog if version is provided
if [ -n "$VERSION" ]; then
    echo "📝 Generating CHANGELOG..."
    
    # Extract changelog entry for this version
    awk -v version="$VERSION" \
        '/^## \['"$version"'\]/ { found=1; print; next } 
         /^## \[/ { if (found) exit }
         found { print }' \
        "$SOURCE_DIR/aitomations/Changelog.md" > "$TARGET/new_entry.md"
    
    # Create or update CHANGELOG.md
    if [ ! -f "$TARGET/CHANGELOG.md" ]; then
        echo "# Changelog" > "$TARGET/CHANGELOG.md"
        echo "" >> "$TARGET/CHANGELOG.md"
    fi
    
    if [ -s "$TARGET/new_entry.md" ]; then
        # Prepend new entry to existing changelog
        {
            echo "# Changelog"
            echo ""
            cat "$TARGET/new_entry.md"
            echo ""
            tail -n +2 "$TARGET/CHANGELOG.md"
        } > "$TARGET/CHANGELOG.new.md"
        mv "$TARGET/CHANGELOG.new.md" "$TARGET/CHANGELOG.md"
        echo "   ✓ Added version $VERSION to CHANGELOG"
    else
        echo "   ⚠️  No changelog entry found for version $VERSION"
    fi
    
    rm -f "$TARGET/new_entry.md"
fi

# Verify critical files exist
echo "✅ Verifying files..."
REQUIRED_FILES=(
    "config.json"
    "README.md"
    "DOCS.md"
    "icon.png"
    "logo.png"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$TARGET/$file" ]; then
        echo "   ✓ $file"
    else
        echo "   ✗ $file (missing)"
        exit 1
    fi
done

echo "✅ Sync complete!"