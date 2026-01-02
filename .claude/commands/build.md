---
allowed-tools: Bash(make:*), Bash(python:*), Bash(ls:*), Bash(radon:*), Bash(pip:install radon)
description: Run linting, type checking, tests, build the package distribution, and validate test coverage is proportional to code complexity.
---

# Build Process

Run the complete build process for leasedkeyq: linting, type checking, tests, complexity analysis, test proportionality validation, and package building.

## Overview

This command executes the full validation and build pipeline to ensure code quality, adequate test coverage relative to complexity, and package integrity before releases.

## Steps

1. **Ensure Radon is Installed**
   - Check if radon is available, if not install it: `pip install radon`
   - Radon is used for cyclomatic complexity analysis

2. **Validation Checks**
   - Run `make all` to execute lint, typecheck, and test targets
   - If validation fails, stop and report errors to the user
   - Validation must pass before proceeding to complexity analysis

3. **Cyclomatic Complexity Analysis**
   - Run `radon cc src/leasedkeyq -a -s` to analyze cyclomatic complexity
     - `-a` shows average complexity
     - `-s` sorts by complexity (highest first)
   - Report the results with clear headers

4. **Test Proportionality Check**
   - Calculate total complexity of source code
   - Verify that the score matches the number of tests for the given area.
   - **Guideline**: For any area of code with a score that is >= 6 (B or less), the number of tests for the area of code must be greater than or equal to 80% of the score for the same area of code. For example, a score of 10 should require at least 8 unit tests focusing on that area of code.
   - **Reasoning**: Complex code requires more comprehensive testing scenarios
   - Report all areas that have insufficient testing based on the guideline. 
     Display in a table with columns: Score, Tests, Ratio, Additional Needed.
   - Report all areas of code that are below or equal to a 'B' grade.
   - Report on tests that were added as well as any areas that still have too few tests.

5. **Build Package**
   - Run `python -m build` to create distribution artifacts
   - This generates both wheel (.whl) and source (.tar.gz) distributions in `dist/`

6. **Verify Build**
   - Check that `dist/` directory exists and contains artifacts
   - List the built files with `ls -lh dist/` to show sizes

7. **Report Results**
   - Use clear section headers and status indicators
   - Include complexity metrics and test proportionality assessment
   - Include next steps for the user

## Output Format

Structure the output with these sections:

### Build Status
- ✅ Lint passed
- ✅ Type checking passed
- ✅ Tests passed (include coverage percentage)
- ✅ Complexity analysis completed
- ✅/⚠️ Test proportionality check (show ratio and assessment)
- ✅ Package built successfully

### Complexity Metrics
- **Source Code Complexity**: Show average and total complexity
- **Test Code Complexity**: Show average and total complexity
- **Test-to-Source Ratio**: X% (with assessment: ✅ Adequate / ⚠️ Needs improvement / ❌ Insufficient)

### Built Artifacts
List the files in `dist/` with their sizes

### Next Steps
- Review coverage report: `htmlcov/index.html`
- Review complexity: Check functions with high complexity (A-F grade)
- Test installation: `pip install dist/*.whl`
- Create release: `/release [VERSION]`

### Recommendations (if applicable)
- If test proportionality is low, suggest specific areas that need more tests
- If any source functions have high complexity (C or worse), recommend refactoring or additional test coverage

## Error Handling

- If radon is not installed, install it automatically with `pip install radon`
- If `make all` fails, report which step failed (lint/typecheck/test) and show relevant errors
- If complexity analysis fails, show the error but continue with build (non-blocking)
- If `python -m build` fails, show the build error
- Do not proceed to package build if validation fails

## Implementation Notes

To extract complexity metrics from radon output:
- Use `radon cc -j src/leasedkeyq` for JSON output to programmatically parse complexity
- Sum up all complexity values to get total complexity
- Count the number of functions/methods to calculate averages
- Compare source vs test complexity ratios

Execute these steps and provide clear status reporting.
