# Unittest to Pytest Migration Plan

This document outlines the roadmap for migrating our existing `unittest`-based tests to `pytest`. The goal is to modernize our testing suite, improve readability, and take advantage of `pytest`'s powerful features.

## General Guidelines

When migrating tests, please adhere to the following principles:

- **New Test Files:** To compare test coverage before and after the migration, create a new test file for the migrated tests. For example, `test/integration/base/test_rest_client_i.py` should be migrated to `test/integration/base/test_rest_client_i_new.py`.
- **Test Classes:** Convert `unittest.TestCase` subclasses into plain test functions. If a class structure is still beneficial for grouping related tests, you can use a class without inheriting from `unittest.TestCase`.
- **`setUp` and `tearDown`:** Replace `setUp` and `tearDown` methods with `pytest` fixtures.
- **Assertions:** Convert all `self.assert...` methods to plain `assert` statements. For example, `self.assertEqual(a, b)` becomes `assert a == b`.
- **Exception Handling:** Replace `with self.assertRaises(...)` with `with pytest.raises(...)`.
- **Logging:** Use the new `capture_logs` utility from `test_utils_new.py`. It can be used as a context manager (`with capture_logs(...) as cm:`) or as a decorator (`@capture_logs(...)`). This replaces all previous `unittest`-based logging helpers. The returned watcher object has methods like `exact_log`, `partial_log`, and `log_excludes` for assertions.
- **Arrange, Act, Assert:** Structure your tests using the Arrange, Act, Assert pattern.
- **Parametrization:** Use `@pytest.mark.parametrize` to run the same test with different inputs.

## Migration Chunks

The following files need to be migrated. Each file can be worked on independently.

---

### 1. [ ] `test/integration/base/test_rest_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/base/test_rest_client_i_new.py`.
    2.  In the new file, convert all `TestCase` subclasses into simple test functions.
    3.  Replace the `setUp` method's logic with a `pytest` fixture.
    4.  Convert all `self.assert...` calls and `with self.assertRaises` to `assert` and `with pytest.raises(...)`.
    5.  Replace `with self.assertLogs(...)` with the `capture_logs` context manager from `test_utils_new.py`.
    6.  Refactor the class-level patch to use the `mocker` fixture within each test function.

---

### 2. [ ] `test/integration/base/test_websocket_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/base/test_websocket_client_i_new.py`.
    2.  In the new file, convert the `TestWsClient` class into a series of test functions.
    3.  Move the `setUp` logic into one or more `pytest` fixtures.
    4.  Eliminate the complex `run_in_test_context` helper. Use the `mocker` fixture for patching and decorate tests with `@capture_logs(...)` from `test_utils_new.py` for logging.
    5.  Convert all `self.assert...` calls to plain `assert` statements.

---

### 3. [ ] `test/integration/client/test_ibkr_client_i.py`

- **Migration Steps:**
    1.  Create a new file: `test/integration/client/test_ibkr_client_i_new.py`.
    2.  In the new file, convert the class into a series of test functions.
    3.  Move the `setUp` logic into a `pytest` fixture.
    4.  Replace all `self.assert...` calls with plain `assert` statements and `pytest.raises`.
    5.  Replace the `SafeAssertLogs` and `RaiseLogsContext` with the `capture_logs` utility from `test_utils_new.py`.
    6.  Handle the class-level patch using the `mocker` fixture.

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
