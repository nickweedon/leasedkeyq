# Contributing Guide

Guidelines for contributing to leasedkeyq.

## Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/leasedkeyq.git
cd leasedkeyq

# Install with dev dependencies
pip install -e ".[dev]"

# Or use devcontainer (recommended)
# Open in VS Code and select "Reopen in Container"
```

## Development Workflow

### 1. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes
- Write code following style guidelines (see below)
- Add tests for new functionality
- Update documentation if API changes

### 3. Run Validation
```bash
# Run all checks
make all

# Or individually
make lint       # Ruff linting
make typecheck  # Mypy type checking
make test       # Pytest with coverage
```

### 4. Commit Changes
```bash
git add .
git commit -m "Add feature: description"
```

### 5. Push and Create PR
```bash
git push origin feature/your-feature-name
# Create PR on GitHub
```

## Code Style

### Type Hints
- **Required** on all public functions and methods
- Use Python 3.10+ syntax: `str | None` instead of `Optional[str]`
- Strict mypy mode must pass

```python
# Good
async def get(self, timeout: float | None = None) -> tuple[K, V, Lease[K]]:
    ...

# Bad - missing return type
async def get(self, timeout: float | None = None):
    ...
```

### Docstrings
- All public APIs must have docstrings
- Use Google style format

```python
def method(self, key: K, value: V) -> None:
    """
    Short description.

    Longer description if needed.

    Args:
        key: Description of key parameter
        value: Description of value parameter

    Raises:
        SomeError: When this error occurs

    Example:
        >>> await queue.method("key", 100)
    """
```

### Formatting
- Line length: 100 characters
- Use ruff for formatting and linting
- Import order: stdlib, third-party, local (ruff handles this)

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

### Async Conventions
- Always use `async def` for methods that acquire locks
- Avoid blocking calls in async functions
- Use `asyncio.wait_for()` for timeouts

## Testing Requirements

### Coverage
- New features must have tests
- Aim for >95% line coverage
- Critical paths need 100% coverage

### Test Organization
```python
@pytest.mark.asyncio
async def test_descriptive_name() -> None:
    """Test description."""
    # Arrange
    queue = LeasedKeyQueue[str, int]()

    # Act
    await queue.put("key", 100)

    # Assert
    assert await queue.qsize() == 1

    # Cleanup
    await queue.close()
```

### What to Test
1. **Happy path** - Normal operation
2. **Edge cases** - Empty queue, single item, etc.
3. **Error conditions** - Invalid inputs, timeouts
4. **Concurrency** - Multiple consumers/producers
5. **State transitions** - Available → in-flight → acked

## Pull Request Guidelines

### PR Title
Use conventional commit format:
- `feat: Add new feature`
- `fix: Fix bug in timeout handling`
- `docs: Update API documentation`
- `test: Add concurrency tests`
- `refactor: Simplify lease management`

### PR Description
Include:
- **What**: Brief description of changes
- **Why**: Motivation for changes
- **How**: Implementation approach
- **Testing**: How changes were tested

### Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] `make all` passes
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] No breaking changes (or clearly documented)

## Breaking Changes

If your change breaks backward compatibility:
1. Document in PR description
2. Update CHANGELOG.md with `[BREAKING]` tag
3. Increment major version (will be done during release)

## Documentation Updates

Update when changing:
- Public API: Update [docs/README.md](README.md)
- Architecture: Update [CLAUDE.md](../CLAUDE.md)
- Examples: Update/add files in [examples/](../examples/)
- Testing: Update [docs/TESTING.md](TESTING.md)

## Release Process

Releases are handled by maintainers:

```bash
# Auto-increment patch version
./release.sh

# Specify version
./release.sh 1.2.0
```

This will:
1. Update version in `pyproject.toml` and `__init__.py`
2. Run `make all` for validation
3. Create git tag and GitHub release
4. Trigger automatic PyPI publishing

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Features**: Open a GitHub Issue with use case description

## Code Review

All PRs require review. Reviewers check for:
- Code correctness and quality
- Test coverage
- Documentation completeness
- Style compliance
- Performance implications

## Common Pitfalls

### 1. Forgetting to Acquire Lock
```python
# Bad
async def method(self) -> None:
    self._available[key] = node  # Race condition!

# Good
async def method(self) -> None:
    async with self._lock:
        self._available[key] = node
```

### 2. Breaking Invariants
```python
# Bad - key in both available and in-flight
del self._in_flight[token]
# Forgot to delete from _leases_by_key!

# Good
del self._in_flight[token]
del self._leases_by_key[key]
```

### 3. Not Notifying Waiters
```python
# Bad
async def put(self, key: K, value: V) -> None:
    async with self._lock:
        node = Node(key, value)
        self._list.append(node)
        # Forgot to notify!

# Good
async def put(self, key: K, value: V) -> None:
    async with self._lock:
        node = Node(key, value)
        self._list.append(node)
        self._cond_changed.notify_all()
```

### 4. Missing Type Hints
```python
# Bad
async def get(self, timeout=None):  # Missing types!
    ...

# Good
async def get(self, timeout: float | None = None) -> tuple[K, V, Lease[K]]:
    ...
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
