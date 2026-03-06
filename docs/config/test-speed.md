# Test Speed Optimizations

Notes on how we increased pytest suite speed.

---

## Dependencies

From [requirements.txt](../../requirements.txt):

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `pytest-xdist` | Parallel execution (`-n auto`) |

```shell
pip install -r requirements.txt
```

---

## Performance (68 tests)

| Configuration | Time | Notes |
|---------------|------|-------|
| Before (per-test engine) | ~5.0 s | Each test created/disposed its own engine |
| After (session-scoped engine) | ~4.7 s | **~6% faster** |
| With `-n auto` (parallel) | ~5.4 s | Slower on small suite; overhead outweighs gains |

*Times are approximate; run `pytest --durations=10` to measure on your machine.*

---

## Summary

| Optimization | Effect |
|--------------|--------|
| Session-scoped engine | Reuse SQLAlchemy engine across tests instead of creating/disposing per test |
| pytest-xdist | Optional parallel execution across CPU cores |
| Quiet mode (`-q`) | Less output, slightly faster I/O |

---

## 1. Session-Scoped Engine

**Problem:** Each test using `db_session` was creating a new `AsyncEngine`, connecting, running the test, then disposing the engine. With ~50+ DB-backed tests, that meant 50+ engine create/dispose cycles.

**Solution:** Introduce a session-scoped `test_engine` fixture in [conftest.py](../../conftest.py):

```python
@pytest.fixture(scope="session")
def test_engine():
    """Session-scoped engine — reused across tests to avoid per-test engine creation."""
    engine = create_async_engine(
        _get_test_db_url(),
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
async def db_session(test_engine):
    """..."""
    async with test_engine.connect() as connection:
        # ... transaction + session ...
```

**Result:** Engine is created once per test session (or per worker when using `-n auto`). Each test still gets its own connection and transaction for isolation.

---

## 2. pytest-xdist (Parallel Execution)

**Install:** `pytest-xdist` is in [requirements.txt](../../requirements.txt).

**Usage:**
```shell
pytest -n auto    # Workers = CPU count
pytest -n 4       # Fixed number of workers
```

**Caveat:** On small suites (~70 tests), parallel can be slightly slower due to worker spawn overhead and DB connection contention. Use when the suite grows or for CI with many cores.

---

## 3. Commands

All commands run from the project root.

```shell
# Quiet mode (less output, slightly faster)
pytest -q

# Show 10 slowest tests (helps find bottlenecks)
pytest --durations=10

# Parallel execution across CPU cores (pytest-xdist)
# May be faster on large suites; can be slower on small suites due to worker overhead
pytest -n auto

# Combine: quiet + parallel
pytest -q -n auto
```

---

## References

- [docs/commands.md](../commands.md) — Pytest commands and "Faster runs" section
- [conftest.py](../../conftest.py) — `test_engine`, `db_session` fixtures
