# Unittest to Pytest Migration Plan

This document outlines the roadmap for migrating our existing `unittest`-based tests to `pytest`. The goal is to modernize our testing suite, improve readability, and take advantage of `pytest`'s powerful features.

## General Guidelines

When migrating tests, please adhere to the following principles:

- **New Test Files:** To compare test coverage before and after the migration, create a new test file for the migrated tests. For example, `test/integration/base/test_rest_client_i.py` should be migrated to `test/integration/base/test_rest_client_i_new.py`.
- **Post-migration check:** run the old and new test files *separately* with `--cov=<target_module> --cov-report=term-missing` and confirm the covered/missing lines are identical (or document any differences).
- **Test Classes:** Convert `unittest.TestCase` subclasses into plain test functions. If a class structure is still beneficial for grouping related tests, you can use a class without inheriting from `unittest.TestCase`.
- **`setUp` and `tearDown`:** Replace `setUp` and `tearDown` methods with `pytest` fixtures.
- **Assertions:** Convert all `self.assert...` methods to plain `assert` statements. For example, `self.assertEqual(a, b)` becomes `assert a == b`.
- **Exception Handling:** Replace `with self.assertRaises(...)` with `with pytest.raises(...)`.
- **Logging:** Use the new `capture_logs` utility from `test_utils_new.py`. It can be used as a context manager (`with capture_logs(...) as cm:`) or as a decorator (`@capture_logs(...)`). This replaces all previous `unittest`-based logging helpers. The returned watcher object has methods like `exact_log`, `partial_log`, and `log_excludes` for assertions.
- **Arrange, Act, Assert:** Structure your tests using the ##Arrange, ##Act, ##Assert pattern.
- **Parametrization:** Use `@pytest.mark.parametrize` to run the same test with different inputs.

## Additional Rules (learned from first few migrations)

The following rules help avoid common migration pitfalls and reduce boilerplate. See:

- `test/integration/base/test_rest_client_i_new.py`
- `test/integration/client/test_ibkr_client_i_new.py`

### Fixtures and constants

- **Prefer module constants for stable configuration**
  - Put stable values such as `_URL`, `_TIMEOUT`, `_DEFAULT_PATH`, `_MAX_RETRIES` at module scope.
  - Keep fixtures focused on objects with lifecycle/state (clients, mocks, results).

- **Avoid “mega fixtures” that return tuples**
  - If a `setUp` method created many objects, migrate it into multiple fixtures.

### Patching (replacing class-level @patch)

- **Use an autouse `requests_mock` fixture for common patching**
  - When the original unittest test patched a whole `TestCase` class (e.g. `@patch('...requests')`), replicate it with a single `@pytest.fixture(autouse=True)`.

  Example pattern:

  ```python
  @pytest.fixture(autouse=True)
  def requests_mock(mocker, response):
      requests_mock = mocker.patch('ibind.base.rest_client.requests')
      requests_mock.request.return_value = response
      return requests_mock
  ```

  Tests can still override behavior locally:

  - `requests_mock.request.side_effect = ReadTimeout()`
  - `requests_mock.request.return_value = MagicMock(...)`

### Preserve unittest semantics

- **Float comparisons**
  - `self.assertAlmostEqual(...)` should migrate to `pytest.approx(...)`.

- **Logging expectations**
  - Do not assert *more* than the unittest test asserted.
  - If unittest checked a substring (e.g. `assertIn`), migrate to `partial_match=True` or explicit substring checks.

- **Exceptions vs return values**
  - Verify whether the production code *raises* or *returns* exceptions.
  - A common pitfall is migrating a test to “return exception in results” when the implementation actually raises (or ignores) specific errors.

- **Key types / coercions**
  - Be careful with dict keys and parameter conversions.
  - If production code casts IDs (e.g. `int(conid)`), results may be keyed by `int` even if the input looked like a string.

- **Naming parity**
  - Keep test names close to the original unittest names to make 1:1 mapping and review easier.

## Migration Chunks

The following files need to be migrated. Each file can be worked on independently.

---

### 1. [✔] `test/integration/base/test_rest_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/base/test_rest_client_i_new.py`.
    2.  In the new file, convert all `TestCase` subclasses into simple test functions.
    3.  Replace the `setUp` method's logic with granular fixtures and module constants (avoid tuple-returning fixtures).
    4.  Convert all `self.assert...` calls and `with self.assertRaises` to `assert` and `with pytest.raises(...)`.
    5.  Replace `with self.assertLogs(...)` with the `capture_logs` context manager from `test_utils_new.py`.
    6.  Refactor the class-level patch into an autouse fixture (e.g. `requests_mock`) so tests don't repeat patch boilerplate.

---

### 2. [] `test/integration/base/test_websocket_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/base/test_websocket_client_i_new.py`.
    2.  In the new file, convert the `TestWsClient` class into a series of test functions.
    3.  Move the `setUp` logic into one or more `pytest` fixtures.
    4.  Eliminate the complex `run_in_test_context` helper. Use the `mocker` fixture for patching and decorate tests with `@capture_logs(...)` from `test_utils_new.py` for logging.
    5.  Convert all `self.assert...` calls to plain `assert` statements.

---

### 3. [✔] `test/integration/client/test_ibkr_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/client/test_ibkr_client_i_new.py`.
    2.  In the new file, convert the class into a series of test functions.
    3.  Move the `setUp` logic into granular fixtures and module constants (avoid tuple-returning fixtures).
    4.  Replace all `self.assert...` calls with plain `assert` statements and `pytest.raises`.
    5.  Replace the `SafeAssertLogs` and `RaiseLogsContext` with the `capture_logs` utility from `test_utils_new.py`.
    6.  Handle the class-level patch using an autouse fixture (e.g. `requests_mock`) so tests don't repeat patch boilerplate.

---

### 4. [ ] `test/integration/client/test_ibkr_utils_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/client/test_ibkr_utils_i_new.py`.
    2.  In the new file, convert all four classes into separate sets of test functions.
    3.  Move `setUp` logic into fixtures where applicable.
    4.  Convert all `self.assert...` calls to plain `assert` and `pytest.raises`.
    5.  Replace `with self.assertLogs(...)` with the `capture_logs` context manager from `test_utils_new.py`.

---

### 5. [ ] `test/integration/client/test_ibkr_ws_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/client/test_ibkr_ws_client_i_new.py`.
    2.  In the new file, convert both `TestCase` subclasses into sets of test functions.
    3.  Move the extensive `setUp` logic into `pytest` fixtures.
    4.  Eliminate the `run_in_test_context` helper. Use the `mocker` fixture for patching and `@capture_logs(...)` from `test_utils_new.py` for logging.
    5.  Convert all `self.assert...` calls to plain `assert` statements.

---

### 6. [ ] `test/unit/support/test_py_utils_u.py`

- **Migration Steps:**
    1.  Create a new file: `test/unit/support/test_py_utils_u_new.py`.
    2.  In the new file, convert all three classes into separate sets of test functions.
    3.  Move the `setUp` method into a fixture.
    4.  Convert all `self.assert...` methods and `with self.assertRaises` to plain `assert` statements and `with pytest.raises(...)`.
    5.  Replace the `@patch` decorator with the `mocker` fixture.