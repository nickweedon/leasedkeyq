#!/bin/bash
set -e

# Release automation script for leasedkeyq
# Usage: ./release.sh [VERSION]
# If VERSION is not provided, auto-increments patch version from latest git tag

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install from: https://cli.github.com/"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated."
    echo "Run: gh auth login"
    exit 1
fi

# Get the latest git tag or default to v0.0.0
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
echo "Latest tag: $LATEST_TAG"

# Auto-increment patch version if VERSION not provided
if [ -z "$1" ]; then
    # Strip 'v' prefix and split into components
    VERSION_NUM=${LATEST_TAG#v}
    IFS='.' read -r MAJOR MINOR PATCH <<< "$VERSION_NUM"

    # Increment patch version
    PATCH=$((PATCH + 1))
    VERSION="$MAJOR.$MINOR.$PATCH"
    echo "Auto-incrementing to: v$VERSION"
else
    VERSION="$1"
    # Strip 'v' prefix if provided
    VERSION=${VERSION#v}
fi

# Validate version format (semantic versioning)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Expected: X.Y.Z (e.g., 1.0.0)"
    exit 1
fi

TAG="v$VERSION"

echo ""
echo "Preparing release $TAG..."
echo ""

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: Tag $TAG already exists"
    exit 1
fi

# Ensure working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: Working directory is not clean. Commit or stash changes first."
    git status --short
    exit 1
fi

# Update version in pyproject.toml
echo "Updating version in pyproject.toml..."
sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
rm pyproject.toml.bak

# Update version in __init__.py
echo "Updating version in src/leasedkeyq/__init__.py..."
sed -i.bak "s/^__version__ = .*/__version__ = \"$VERSION\"/" src/leasedkeyq/__init__.py
rm src/leasedkeyq/__init__.py.bak

# Run all checks
echo "Running validation checks..."
make all

if [ $? -ne 0 ]; then
    echo "Error: Validation checks failed. Fix errors and try again."
    git checkout pyproject.toml src/leasedkeyq/__init__.py
    exit 1
fi

echo ""
echo "✓ All checks passed"
echo ""

# Commit version bump
echo "Committing version bump..."
git add pyproject.toml src/leasedkeyq/__init__.py
git commit -m "Bump version to $VERSION"

# Create git tag
echo "Creating git tag $TAG..."
git tag -a "$TAG" -m "Release $TAG"

# Push to GitHub
echo "Pushing to GitHub..."
git push origin main
git push origin "$TAG"

# Create GitHub release
echo "Creating GitHub release..."
gh release create "$TAG" \
    --title "Release $TAG" \
    --generate-notes

echo ""
echo "✓ Release $TAG created successfully!"
echo ""
echo "The GitHub Actions workflow will automatically publish to PyPI."
echo ""
