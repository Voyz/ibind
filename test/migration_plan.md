# Unittest to Pytest Migration Plan

This document outlines the roadmap for migrating our existing `unittest`-based tests to `pytest`. The goal of this migration is to modernize our testing suite, improve readability, and take advantage of `pytest`'s powerful features, such as fixtures and improved assertions.

## Identifying `unittest` Files

To ensure a complete migration, a systematic search was performed across the `test/` directory to identify all files using the `unittest` framework. This was accomplished by running the following command:

```bash
grep -r -E "import unittest|from unittest" test/
```

This command recursively searches for `unittest` imports in all files within the `test/` directory. The output of this command is the definitive list of files that need to be migrated.

## General Guidelines

When migrating tests, please adhere to the following principles:

- **Test Classes:** Convert `unittest.TestCase` subclasses into plain test functions. If a class structure is still beneficial for grouping related tests, you can use a class without inheriting from `unittest.TestCase`.
- **`setUp` and `tearDown`:** Replace `setUp` and `tearDown` methods with `pytest` fixtures. This is the preferred way to manage test setup and teardown in `pytest`.
- **Assertions:** Convert all `self.assert...` methods to plain `assert` statements. For example, `self.assertEqual(a, b)` becomes `assert a == b`. `pytest` provides detailed output for failing assertions.
- **Exception Handling:** Replace `with self.assertRaises(...)` with `with pytest.raises(...)`.
- **Logging:** The `test_utils.py` file will be updated manually to provide a `capture_logs` fixture. This fixture will replace the `SafeAssertLogs`, `RaiseLogsContext`, `TestCaseWithRaiseLogs`, and `raise_logs` decorator. Use the `capture_logs` fixture to test log messages.
- **Arrange, Act, Assert:** Structure your tests using the Arrange, Act, Assert pattern to improve readability and maintainability.
- **Parametrization:** Use `@pytest.mark.parametrize` to run the same test with different inputs. This is a powerful feature for reducing code duplication.

## Migration Chunks

The following files need to be migrated. Each file can be worked on independently.

1. [ ] `test/e2e/xtest_ibkr_client_e.py`
2. [ ] `test/integration/base/test_rest_client_i.py`
3. [ ] `test/integration/base/test_websocket_client_i.py`
4. [ ] `test/integration/base/websocketapp_mock.py`
5. [ ] `test/integration/client/test_ibkr_client_i.py`
6. [ ] `test/integration/client/test_ibkr_utils_i.py`
7. [ ] `test/integration/client/test_ibkr_ws_client_i.py`
8. [ ] `test/unit/support/test_py_utils_u.py`

**Note:** `test/test_utils.py` will be updated manually by a human to provide a `capture_logs` fixture. This fixture will be used in the migrated tests.
