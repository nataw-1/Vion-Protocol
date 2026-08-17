# Contributing to VION Protocol

Thank you for your interest in contributing. VION Protocol is open-source infrastructure for AI agent governance. Contributions that improve reliability, security, or developer experience are welcome.

---

## Development Setup

```bash
# Clone the repo
git clone https://github.com/nataw-1/Vion-Protocol
cd Vion-Protocol

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install test dependencies
pip install pytest pytest-cov ruff

# Copy and configure environment
cp .env.example .env
# Edit .env — set VION_AUTH_TOKEN to any string for local testing

# Verify setup
pytest tests/ -q
```

---

## Running Tests

```bash
# Run all 50 tests
pytest tests/

# Run with coverage
pytest tests/ --cov=nvion --cov-report=term-missing

# Run a specific test file
pytest tests/test_halt_engine.py -v

# Run a specific test
pytest tests/test_halt_engine.py::TestCondition6::test_condition_6_always_halts_immediately -v
```

All 50 tests must pass before submitting a pull request.

---

## Code Standards

VION Protocol uses `ruff` for linting.

```bash
# Check for issues
ruff check nvion/

# Auto-fix safe issues
ruff check nvion/ --fix
```

**Style rules:**
- Line length: 100 characters
- Type hints on all public methods
- Docstrings on all public classes and methods
- No unused imports (`F401`)
- Sorted imports (`I001`)

---

## Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable releases only |
| `dev` | Active development, PRs target here |
| `feature/name` | New features |
| `fix/name` | Bug fixes |
| `docs/name` | Documentation only |

All pull requests should target `dev`, not `main`.

---

## Pull Request Process

1. Fork the repository
2. Create a branch from `dev`: `git checkout -b feature/your-feature dev`
3. Make your changes
4. Add or update tests for your changes
5. Ensure all 50 existing tests still pass
6. Run `ruff check nvion/` — zero errors required
7. Update documentation if you changed public APIs
8. Open a PR against `dev` with a clear description

**PR description should include:**
- What changed and why
- Which tests cover the change
- Any constitutional implications (changes to governance behavior)

---

## What to Contribute

**High priority:**
- Bug fixes with reproduction test cases
- Security improvements to the governance pipeline
- New adapter implementations (Autogen, Haystack, etc.)
- Additional N Auditor detection patterns
- Performance improvements to log chain verification

**Medium priority:**
- Additional example projects
- Documentation improvements
- Additional risk cap patterns

**Please discuss first (open an issue):**
- Changes to the HALT Engine condition thresholds
- Changes to the constitutional document format
- New HALT conditions
- Breaking API changes

---

## Constitutional Constraints on Contributions

Contributions must not:
- Remove or weaken any of the 6 HALT conditions
- Bypass the N Auditor output gate
- Allow peer-to-peer agent communication
- Remove suspension persistence
- Weaken the hash-chain integrity system
- Allow agents to modify VION.md or IDENTITY.md

The constitutional model is the core of VION Protocol. Its integrity is non-negotiable.

---

## Reporting Security Issues

Do not open a public GitHub issue for security vulnerabilities. Email directly: **security@nvionprotocol.dev**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix if you have one

---

## Roadmap Contributions

See `ROADMAP.md` for planned versions. If you want to work on a roadmap item, open an issue first to coordinate — especially for items in v1.1.0 and beyond, which require architectural discussions.

---

*VION Protocol — constitutional law for AI agents.*
