# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-02

### Added
- Initial release of leasedkeyq
- FIFO queue with keyed access
- Lease-based exclusive access with ack/release semantics
- O(1) operations using intrusive doubly-linked list
- Blocking `get()` for FIFO consumption
- Blocking `take(key)` for keyed consumption
- Automatic lease timeouts with background reaper task
- Context manager support for lifecycle management
- In-flight policies: update, reject, buffer
- Comprehensive test suite with >95% coverage
- Full type hints with strict mypy compliance

[Unreleased]: https://github.com/yourusername/leasedkeyq/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/leasedkeyq/releases/tag/v0.1.0
