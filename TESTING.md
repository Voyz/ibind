# Testing Guide

This document defines how tests are chosen, written, and evaluated.

---

## Testing philosophy

- Use commentary with `## Arrange` `## Act` and `## Assert` sections for test structure.
- Tests exist to lock behaviour, not to chase coverage.
- Avoid tests that duplicate what the language/runtime already guarantees.
- Use fixtures for setup/teardown of test state.
- Mock internal dependencies for unit tests. Mock external dependencies for integration tests.
- Prefer integration tests for verifying component boundaries and data flow.
- Capture and assert on logs for error and warning conditions.

## Guidelines

- When `time.time` is used, use `mock_module_time` from `test.test_utils` rather than waiting for the time to pass.


## Test Type Structure

Tests are organized into three main categories:

```
test/
├── unit/         # Fast, isolated tests for core logic 
├── integration/  # Multi-component tests 
└── manual/       # Manual and performance tests 
```


## Test types and boundaries

Use the lightest test type that still provides confidence.

### Unit tests
Use when:
- logic is isolated and deterministic
- behaviour can be validated without wiring other components

Guidelines:
- No network, filesystem, threads, or time dependence.
- Mock only at clear boundaries; do not mock internals of the unit under test.
- Data should be small, synthetic, and explicit.
- Prefer clarity over clever parametrisation.

### Integration tests
Use when:
- correctness depends on interaction between components
- data flow or ordering matters

Guidelines:
- Mock only outside the test boundary (eg. broker, network).
- Use realistic but minimal fixtures.
- Allow threads/timers only if they are part of the behaviour being tested.
- Failures should clearly indicate which interaction broke.

### Manual / performance tests
Use when:
- validating full-system flows
- measuring throughput, latency, or concurrency
- interacting with real or near-real external systems

Guidelines:
- Never run automatically in CI.
- Keep secrets out of test code.
- Prefer recorded or replayable inputs where possible.
- Treat results as diagnostic, not pass/fail gates.


## Choosing what to test

Test:
- decision logic
- state transitions
- boundary conditions
- error and warning paths
- behaviour that has broken before

Do not test:
- trivial getters/setters
- pure delegation
- obvious library behaviour
- formatting or logging text unless it signals correctness


## Running tests

- Prefer running the smallest relevant subset while iterating.
- Run broader suites when touching core or high-risk code.
