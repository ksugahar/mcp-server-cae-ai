# Testing Guide

## Quick Start

```bash
# Run all tests
pip install -e ".[test]"
pytest

# Run specific test files
pytest tests/test_radia_rules.py -v
pytest tests/test_selftest.py -v
pytest tests/test_cubit_rules.py -v
```

## Test Structure

### Unit Tests: `test_radia_rules.py` (23 tests)

Each lint rule has a dedicated test class with:
- **Positive test**: Bad code that should trigger the rule
- **Negative test**: Good code that should NOT trigger the rule
- **Edge cases**: Comments, docstrings, non-matching contexts

```python
class TestObjBckgNoLambda:
    def test_detects_list_arg(self):       # Bad code -> finding
        ...
    def test_allows_lambda(self):           # Good code -> no finding
        ...
    def test_allows_function_ref(self):     # Edge case
        ...
```

### Fixture Tests: `test_selftest.py` (8 tests)

Tests that lint rules work correctly on actual `.py` files:

| Test | Description |
|------|-------------|
| `test_fixtures_dir_exists` | `tests/fixtures/` directory exists |
| `test_bad_radia_has_findings` | Bad Radia code triggers rules |
| `test_bad_ngsolve_has_findings` | Bad NGSolve code triggers rules |
| `test_bad_peec_has_findings` | Bad PEEC/BEM code triggers rules |
| `test_clean_radia_has_no_findings` | Clean code has zero false positives |
| `test_all_severity_levels_covered` | CRITICAL and HIGH both covered |
| `test_radia_selftest_uses_fixtures` | Selftest falls back to fixtures |
| `test_cubit_selftest_skips_without_examples` | Cubit selftest graceful skip |

### Meta Tests (in rule test files)

```python
class TestAllRulesList:
    def test_all_rules_count(self):       # Correct number of rules
    def test_all_rules_callable(self):    # All rules are functions
    def test_clean_code_no_findings(self): # No false positives
```

## Test Fixtures

Located in `tests/fixtures/`:

| File | Purpose | Expected Findings |
|------|---------|-------------------|
| `bad_radia_script.py` | Triggers Radia-specific rules | 5 (CRITICAL, HIGH, LOW) |
| `bad_ngsolve_script.py` | Triggers NGSolve-specific rules | 8+ (HIGH, MODERATE) |
| `bad_peec_script.py` | Triggers PEEC/BEM rules | 2 (CRITICAL, MODERATE) |
| `clean_radia_script.py` | Zero findings (no false positives) | 0 |

### Adding a Fixture

When adding a new lint rule:

1. Add a triggering code line to the appropriate `bad_*.py` file
2. Verify with: `python -c "from mcp_server_cae_ai.radia.server import _lint_file; print(_lint_file('tests/fixtures/bad_radia_script.py'))"`
3. Be careful not to accidentally include rule keywords in comments (e.g., mentioning `UtiDelAll` in a comment will suppress the `missing-utidelall` rule)

## Self-Test (`--selftest`)

```bash
# From a project with examples/
cd /path/to/radia-project
mcp-server-radia --selftest

# From anywhere (uses built-in fixtures)
cd /tmp
python -m mcp_server_cae_ai.radia.server --selftest
```

The self-test verifies:
1. All rules can detect violations (bad fixtures have findings)
2. No false positives (clean fixture has zero findings)
3. Both CRITICAL and HIGH severity levels are covered

## CI Integration

```yaml
# GitHub Actions example
- name: Install
  run: pip install -e ".[test]"

- name: Unit tests
  run: pytest tests/ -v --tb=short

- name: Self-test
  run: python -m mcp_server_cae_ai.radia.server --selftest
```

The self-test works in CI without any external `examples/` directory because it falls back to the built-in fixture files.

## Coverage

Current test coverage:

| Component | Tests | Coverage |
|-----------|-------|----------|
| Radia lint rules (23) | 23 classes, 57 test methods | All rules tested |
| Cubit lint rules (16) | 16 classes, 40 test methods | All rules tested |
| Selftest mechanism | 8 tests | Both servers, fixtures, edge cases |
| **Total** | **111 tests** | All pass |
