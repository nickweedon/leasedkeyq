---
allowed-tools: Bash(make:*), Bash(python:*), Bash(ls:*)
description: Run linting, type checking, tests, and build the package distribution. Use this to validate code before committing or releasing.
---

# Build Process

Run the complete build process for leasedkeyq: linting, type checking, tests, and package building.

## Overview

This command executes the full validation and build pipeline to ensure code quality and package integrity before releases.

## Steps

1. **Validation Checks**
   - Run `make all` to execute lint, typecheck, and test targets
   - If validation fails, stop and report errors to the user
   - Validation must pass before proceeding to build

2. **Build Package**
   - Run `python -m build` to create distribution artifacts
   - This generates both wheel (.whl) and source (.tar.gz) distributions in `dist/`

3. **Verify Build**
   - Check that `dist/` directory exists and contains artifacts
   - List the built files with `ls -lh dist/` to show sizes

4. **Report Results**
   - Use clear section headers and status indicators
   - Include next steps for the user

## Output Format

Structure the output with these sections:

### Build Status
- ✅ Lint passed
- ✅ Type checking passed
- ✅ Tests passed (include coverage percentage)
- ✅ Package built successfully

### Built Artifacts
List the files in `dist/` with their sizes

### Next Steps
- Review coverage report: `htmlcov/index.html`
- Test installation: `pip install dist/*.whl`
- Create release: `/release [VERSION]`

## Error Handling

- If `make all` fails, report which step failed (lint/typecheck/test) and show relevant errors
- If `python -m build` fails, show the build error
- Do not proceed to next steps if any step fails

Execute these steps and provide clear status reporting.
