---
allowed-tools: Bash(./release.sh:*)
argument-hint: [version]
description: Create a new release with optional version number. Auto-increments patch version if not specified. Use /release for patch bump or /release 1.2.3 for specific version.
---

# Create Release

Create a new release of leasedkeyq with proper versioning and tagging.

## Overview

This command wraps the `release.sh` script to create a new version, update changelogs, create git tags, and prepare for publishing.

## Usage

- **Auto-increment patch version**: `/release`
  - Example: 0.1.0 → 0.1.1
- **Specific version**: `/release 1.2.3`
  - Example: `/release 0.2.0` for minor version bump

## Steps

1. **Execute Release Script**
   - If `$ARGUMENTS` is provided, run `./release.sh $ARGUMENTS`
   - If no arguments, run `./release.sh` (auto-increment patch)

2. **Monitor Output**
   - The script will show current version and new version
   - It will update `pyproject.toml` and create git tags
   - Watch for any errors during the process

3. **Report Results**
   - Show the version that was created
   - Confirm git tag creation
   - Provide next steps for publishing

## Output Format

Structure the output with these sections:

### Release Status
- ✅ Version updated (old → new)
- ✅ Git tag created
- ✅ Changelog updated (if applicable)

### Next Steps
- Push tags: `git push --tags`
- Publish to PyPI: `python -m twine upload dist/*`
- Create GitHub release from tag

## Guidelines

- Ensure working directory is clean before releasing
- Follow semantic versioning conventions:
  - MAJOR: Breaking changes
  - MINOR: New features (backward compatible)
  - PATCH: Bug fixes (backward compatible)
- The release script should handle version updates automatically

## Error Handling

- If working directory is dirty, report uncommitted changes
- If version is invalid, explain semantic versioning format
- If git operations fail, show the git error

Execute the release script and provide clear status reporting.
