#!/bin/bash
set -e

FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        *)
            VERSION=$1
            shift
            ;;
    esac
done

if [ -z "$VERSION" ]; then
    echo "Usage: $0 [-f|--force] <version>"
    echo "Example: $0 1.0.1"
    echo "Example: $0 --force 1.0.1  # Re-release existing tag"
    exit 1
fi

TAG="v${VERSION}"

echo "🚀 Preparing release ${VERSION}"

# Check if on main branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "❌ Must be on main branch to release (currently on: $BRANCH)"
    exit 1
fi

# Check if working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Working directory is not clean. Commit or stash changes first."
    git status --short
    exit 1
fi

# Refresh remote tags
echo "🔄 Syncing tags with remote..."
git fetch --prune --prune-tags

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    if [ "$FORCE" = false ]; then
        echo "❌ Tag $TAG already exists"
        echo "   Use --force to delete and recreate it"
        exit 1
    else
        echo "⚠️  Tag $TAG exists, deleting..."
        git tag -d "$TAG"
        git push origin --delete "$TAG" 2>/dev/null || echo "   (Remote tag already deleted)"
    fi
fi

# Check if changelog has entry for this version
if ! grep -q "## \[${VERSION}\]" aitomations/Changelog.md; then
    echo "❌ No changelog entry found for version ${VERSION}"
    echo ""
    echo "Please add an entry to aitomations/Changelog.md following this format:"
    echo ""
    echo "## [${VERSION}] - $(date +%Y-%m-%d)"
    echo ""
    echo "### Added"
    echo "- New feature description"
    echo ""
    echo "### Fixed"
    echo "- Bug fix description"
    echo ""
    exit 1
fi

echo "📝 Updating version numbers..."

# Update config.json
cd aitomations
jq --arg version "$VERSION" '.version = $version' config.json > config.json.tmp
mv config.json.tmp config.json
cd ..

# Update README.md badge
sed -i "s/version-[0-9]\+\.[0-9]\+\.[0-9]\+-blue/version-${VERSION}-blue/g" README.md

# Commit version changes
git add aitomations/config.json README.md

# Only commit if there are changes
if ! git diff --staged --quiet; then
    git commit -m "chore: bump version to ${VERSION}"
    git push origin main
    echo "✓ Version numbers updated and committed"
else
    echo "✓ Version numbers already up to date (no changes needed)"
fi

echo "🔍 Validating code..."
make validate

echo "✅ All checks passed!"
echo ""
echo "Creating release ${VERSION}..."
echo "  1. Tag: ${TAG}"
if [ "$FORCE" = true ]; then
    echo "  2. ⚠️  FORCE mode: This will recreate the tag and re-trigger workflows"
else
    echo "  2. This will trigger:"
fi
echo "     - Docker image builds for all architectures"
echo "     - Update to installation repository"
echo "     - GitHub release creation"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Create and push tag
git tag -a "$TAG" -m "Release version ${VERSION}"
git push origin "$TAG"

echo "✅ Tag ${TAG} created and pushed"
echo ""
echo "🎉 Release process started!"
echo "   Monitor progress at: https://github.com/gmatrangola/AItomation/actions"
echo ""
echo "After the workflow completes:"
echo "  - Docker images will be available at: docker pull gmatrangola/aitomations-amd64:${VERSION}"
echo "  - Installation repo will be updated"
echo "  - GitHub release will be created"