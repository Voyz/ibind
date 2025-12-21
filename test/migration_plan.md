# Unittest to Pytest Migration Plan

This document outlines the roadmap for migrating our existing `unittest`-based tests to `pytest`. The goal of this migration is to modernize our testing suite, improve readability, and take advantage of `pytest`'s powerful features, such as fixtures and improved assertions.

This plan is designed to be executed by multiple AI agents in parallel, with each agent working on a separate file.

## Identifying `unittest` Files

To ensure a complete migration, a systematic search was performed across the `test/` directory to identify all files using the `unittest` framework. This was accomplished by running the following command:

```bash
grep -r "import unittest" test/
```

This command recursively searches for the string `"import unittest"` in all files within the `test/` directory. The output of this command is the definitive list of files that need to be migrated.

## General Guidelines

When migrating tests, please adhere to the following principles:

- **Test Classes:** Convert `unittest.TestCase` subclasses into plain test functions. If a class structure is still beneficial for grouping related tests, you can use a class without inheriting from `unittest.TestCase`.
- **`setUp` and `tearDown`:** Replace `setUp` and `tearDown` methods with `pytest` fixtures. This is the preferred way to manage test setup and teardown in `pytest`.
- **Assertions:** Convert all `self.assert...` methods to plain `assert` statements. For example, `self.assertEqual(a, b)` becomes `assert a == b`. `pytest` provides detailed output for failing assertions.
- **Exception Handling:** Replace `with self.assertRaises(...)` with `with pytest.raises(...)`.
- **Logging:** Use the built-in `caplog` fixture to test log messages. This is the standard `pytest` way to handle logging.
- **Arrange, Act, Assert:** Structure your tests using the Arrange, Act, Assert pattern to improve readability and maintainability.
- **Parametrization:** Use `@pytest.mark.parametrize` to run the same test with different inputs. This is a powerful feature for reducing code duplication.

## Migration Chunks

The following files need to be migrated. Each file can be worked on by a separate AI agent.

### `test/test_utils.py`

**Current Structure:**
- This file contains several helper functions and classes for testing, including `SafeAssertLogs`, `RaiseLogsContext`, `TestCaseWithRaiseLogs`, and a decorator `raise_logs`.
- These utilities are tightly coupled with the `unittest` framework.

**Migration Steps:**
1. **Refactor `SafeAssertLogs`:** This class can be replaced with the built-in `caplog` fixture in `pytest`. The tests that use this class will need to be updated to use `caplog`.
2. **Refactor `RaiseLogsContext`:** This context manager can also be replaced with the `caplog` fixture. The logic for raising an exception on unexpected log messages will need to be implemented within the tests themselves.
3. **Refactor `raise_logs` decorator:** This decorator should be removed. The tests that use it will need to be updated to use `caplog` and the logic for checking for unexpected log messages.
4. **Refactor `TestCaseWithRaiseLogs`:** This class should be removed. The tests that inherit from it will need to be converted to plain test functions.
5. **Remove `unittest` imports:** Once all the `unittest`-dependent code has been refactored, the `import unittest` statement can be removed.

**Potential Challenges:**
- The logic in `RaiseLogsContext` for raising exceptions on unexpected log messages is complex. This will need to be carefully replicated in the tests that use this context manager.

### `test/unit/support/test_py_utils_u.py`

**Current Structure:**
- This file contains several `unittest.TestCase` subclasses with `setUp` methods and `self.assert...` statements.
- It tests the functions in `ibind/support/py_utils.py`.

**Migration Steps:**
1. **Convert `TestEnsureListArgU`:**
   - Convert the class to a set of test functions.
   - Use `assert` for all assertions.
   - Use `@pytest.mark.parametrize` to reduce code duplication for the different test cases.
2. **Convert `TestExecuteInParallelU`:**
   - Convert the class to a set of test functions.
   - Use a `pytest` fixture to replace the `setUp` method.
   - Use `assert` for all assertions.
   - Use `@pytest.mark.parametrize` where appropriate.
3. **Convert `TestWaitUntilU`:**
   - Convert the class to a set of test functions.
   - Use `assert` for all assertions.
   - Use the `caplog` fixture to test the log message for the timeout.
4. **Remove `unittest` imports:** Once all the `unittest`-dependent code has been refactored, the `import unittest` statement can be removed.

**Potential Challenges:**
- There are no significant challenges expected for this file. The migration should be straightforward.
