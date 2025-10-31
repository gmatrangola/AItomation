#!/bin/bash
set -e

# Script to create a new release
# Usage: ./scripts/release.sh 1.0.1

if [ $# -eq 0 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 1.0.1"
    exit 1
fi

VERSION=$1
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

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "❌ Tag $TAG already exists"
    exit 1
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

# Validate code before tagging
echo "🔍 Validating code..."
make validate

echo "✅ All checks passed!"
echo ""
echo "Creating release ${VERSION}..."
echo "  1. Tag: ${TAG}"
echo "  2. This will trigger:"
echo "     - Version updates in config.json and README.md"
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
echo "   Monitor progress at: https://github.com/gmatrangola/aitomations/actions"
echo ""
echo "After the workflow completes:"
echo "  - Docker images will be available at: docker pull gmatrangola/aitomations-amd64:${VERSION}"
echo "  - Installation repo will be updated"
echo "  - GitHub release will be created"