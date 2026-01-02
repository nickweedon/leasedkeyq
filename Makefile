.PHONY: help install lint typecheck test all clean release

help:
	@echo "leasedkeyq development commands:"
	@echo ""
	@echo "  make install     - Install package with dev dependencies"
	@echo "  make lint        - Run ruff linter"
	@echo "  make typecheck   - Run mypy type checker"
	@echo "  make test        - Run pytest with coverage"
	@echo "  make all         - Run lint, typecheck, and test (recommended)"
	@echo "  make clean       - Remove build artifacts"
	@echo "  make release     - Create a new release (use VERSION=x.y.z to override)"
	@echo ""

install:
	pip install -e ".[dev]"

lint:
	@echo "Running ruff linter..."
	ruff check src/ tests/

typecheck:
	@echo "Running mypy type checker..."
	mypy src/

test:
	@echo "Running pytest with coverage..."
	pytest tests/ -v --cov=leasedkeyq --cov-report=term-missing --cov-report=html

all: lint typecheck test
	@echo ""
	@echo "✓ All checks passed!"

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ Cleaned"

release:
	@echo "Creating release..."
	@bash release.sh $(VERSION)
