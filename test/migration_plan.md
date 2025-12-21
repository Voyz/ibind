# Unittest to Pytest Migration Plan

This document outlines the roadmap for migrating our existing `unittest`-based tests to `pytest`. The goal of this migration is to modernize our testing suite, improve readability, and take advantage of `pytest`'s powerful features, such as fixtures and improved assertions.

## General Guidelines

When migrating tests, please adhere to the following principles:

- **Test Classes:** Convert `unittest.TestCase` subclasses into plain test functions. If a class structure is still beneficial for grouping related tests, you can use a class without inheriting from `unittest.TestCase`.
- **`setUp` and `tearDown`:** Replace `setUp` and `tearDown` methods with `pytest` fixtures. This is the preferred way to manage test setup and teardown in `pytest`.
- **Assertions:** Convert all `self.assert...` methods to plain `assert` statements. For example, `self.assertEqual(a, b)` becomes `assert a == b`. `pytest` provides detailed output for failing assertions.
- **Exception Handling:** Replace `with self.assertRaises(...)` with `with pytest.raises(...)`.
- **Logging:** The `test_utils.py` file will be updated manually to provide a `capture_logs` fixture. This fixture will replace the `SafeAssertLogs`, `RaiseLogsContext`, `TestCaseWithRaiseLogs`, and `raise_logs` decorator. Use the `capture_logs` fixture to test log messages. The built-in `caplog` fixture can also be used for simple cases.
- **Arrange, Act, Assert:** Structure your tests using the Arrange, Act, Assert pattern to improve readability and maintainability.
- **Parametrization:** Use `@pytest.mark.parametrize` to run the same test with different inputs. This is a powerful feature for reducing code duplication.

## Migration Chunks

The following files need to be migrated. Each file can be worked on independently.

**Note:** `test/test_utils.py` will be updated manually to provide a `capture_logs` fixture. This fixture will be used in the migrated tests.

---

### 1. [ ] `test/integration/base/test_rest_client_i.py`

- **Current Structure:** Contains three `unittest.TestCase` subclasses: `TestRestClientI`, `TestRestClientInThread`, and `TestRestClientAsync`. It uses a class-level `@patch` decorator, `setUp` methods, and various `self.assert...` methods, including `self.assertLogs` and `self.assertRaises`.
- **Migration Steps:**
    1.  Convert the `TestRestClientI` class into a series of test functions.
    2.  Replace the `setUp` method's logic with a `pytest` fixture that provides a configured `RestClient` instance.
    3.  Convert all `self.assertEqual` and `self.assertRaises` calls to plain `assert` statements and `with pytest.raises(...)`.
    4.  Replace `with self.assertLogs(...)` with the `caplog` fixture for log capture and assertion.
    5.  Refactor the class-level `@patch('ibind.base.rest_client.requests')` to use the `mocker` fixture from `pytest-mock` within each test function that needs it.
    6.  Convert the `TestRestClientInThread` and `TestRestClientAsync` classes to simple test functions; their internal logic does not require a class structure.
- **Potential Challenges:** The class-level patching needs to be carefully applied to each test function that relies on it, likely using the `mocker.patch` method.

---

### 2. [ ] `test/integration/base/test_websocket_client_i.py`

- **Current Structure:** Contains a single `TestWsClient(TestCase)` class with a complex `setUp` method. It heavily relies on a custom `run_in_test_context` helper method that sets up multiple patches and log handlers (`self.assertLogs`, `RaiseLogsContext`).
- **Migration Steps:**
    1.  Convert the `TestWsClient` class into a series of test functions.
    2.  The logic within the `setUp` method should be moved into one or more `pytest` fixtures.
    3.  The `run_in_test_context` helper method must be refactored. Its functionality (patching, log capturing) should be moved into a dedicated fixture.
    4.  Replace `self.assertLogs` and the custom `RaiseLogsContext` with the new `capture_logs` fixture.
    5.  Convert all `self.assertTrue` and `self.assertFalse` calls to plain `assert` statements.
- **Potential Challenges:** The `run_in_test_context` method is complex. Migrating its logic into a `pytest` fixture that correctly manages setup and teardown of patches will be the most challenging part of this file's migration.

---

### 3. [ ] `test/integration/client/test_ibkr_client_i.py`

- **Current Structure:** Consists of a single `TestIbkrClientI(TestCase)` class that uses a class-level `@patch`, a `setUp` method, and a wide variety of `self.assert...` methods.
- **Migration Steps:**
    1.  Convert the `TestIbkrClientI` class into a series of test functions.
    2.  Move the `setUp` logic into a `pytest` fixture.
    3.  Replace all `self.assert...` calls (e.g., `assertEqual`, `assertIn`, `assertRaises`, `assertAlmostEqual`, `assertTrue`) with plain `assert` statements and `pytest.raises`.
    4.  Replace `with self.assertLogs(...)` and `RaiseLogsContext` with the `capture_logs` fixture or `caplog`.
    5.  Handle the class-level patch using the `mocker` fixture in each relevant test function.
- **Potential Challenges:** The `test_marketdata_history_by_symbols` test has a complex mock side effect (`_marketdata_request`). This logic should be extracted into a helper function or a fixture to maintain readability.

---

### 4. [ ] `test/integration/client/test_ibkr_utils_i.py`

- **Current Structure:** Contains four `TestCase` subclasses: `TestIbkrUtilsI`, `TestFindAnswer`, `TestHandleQuestionsI`, and `TestParseOrderRequestI`. These classes use `setUp` methods and various assertions.
- **Migration Steps:**
    1.  Convert all four classes into separate sets of test functions. The class names can be used as prefixes for the function names to maintain grouping (e.g., `test_ibkr_utils_filter_stocks`).
    2.  Move `setUp` logic into fixtures where applicable.
    3.  Convert all `self.assert...` calls to plain `assert` and `pytest.raises`.
    4.  Replace `with self.assertLogs(...)` with the `caplog` fixture.
- **Potential Challenges:** This file appears to be a straightforward migration with no significant challenges.

---

### 5. [ ] `test/integration/client/test_ibkr_ws_client_i.py`

- **Current Structure:** Contains two `TestCase` subclasses: `TestPreprocessRawMessage` and `TestIbkrWsClient`. The `TestIbkrWsClient` class is complex, with a detailed `setUp` method and a `run_in_test_context` helper method similar to the one in `test_websocket_client_i.py`.
- **Migration Steps:**
    1.  Convert both `TestCase` subclasses into sets of test functions.
    2.  Move the extensive `setUp` logic from `TestIbkrWsClient` into `pytest` fixtures.
    3.  Refactor the `run_in_test_context` helper method into a dedicated fixture that handles patching and log capturing.
    4.  Replace `SafeAssertLogs` and `RaiseLogsContext` with the new `capture_logs` fixture.
    5.  Convert all `self.assert...` calls to plain `assert` statements.
- **Potential Challenges:** Similar to `test_websocket_client_i.py`, the primary challenge is refactoring the `run_in_test_context` method into a robust and readable `pytest` fixture.

---

### 6. [ ] `test/unit/support/test_py_utils_u.py`

- **Current Structure:** Contains three `TestCase` subclasses: `TestEnsureListArgU`, `TestExecuteInParallelU`, and `TestWaitUntilU`. It uses `setUp`, a variety of `self.assert...` methods, and `with self.assertRaises`.
- **Migration Steps:**
    1.  Convert all three classes into separate sets of test functions.
    2.  Move the `setUp` method from `TestExecuteInParallelU` into a fixture.
    3.  Convert all `self.assert...` methods and `with self.assertRaises` to plain `assert` statements and `with pytest.raises(...)`.
    4.  The `@patch` decorator in `test_wait_until_timeout_message` can be replaced with the `mocker` fixture.
- **Potential Challenges:** This file should be a straightforward migration.
