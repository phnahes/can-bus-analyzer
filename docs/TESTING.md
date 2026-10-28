# Tests

The suite is **hardware-free**: it runs on macOS and Linux CI with no adapter
plugged in. Qt uses the `offscreen` platform plugin, python-can is only reached
through `virtual` buses or injected fakes, and every shell command (`ip`,
`pkexec`) goes through an injected runner.

## Running

```bash
pip install -r requirements-dev.txt   # adds pytest + pytest-cov

pytest                    # fast suite (default, skips slow guards)
pytest -m slow            # scaling guards
pytest --cov=src          # coverage report
```

On a headless machine set `QT_QPA_PLATFORM=offscreen` (the fixtures do this
too). Nothing writes to your real config: the logger points at a temporary
directory and dialogs are built from dictionaries.

## Layout

| File | Covers |
|------|--------|
| `tests/conftest.py` | `qapp` (offscreen), `FakeParent`, table/handler factories |
| `test_models.py` | `CANMessage` dict roundtrip, ASCII/bits, filters |
| `test_log_roundtrip.py` | JSON/CSV/trace save + load |
| `test_receive_table_manager.py` | Monitor row index, sorted insert, Tracer batching and ring buffer |
| `test_ui_update_handler.py` | Tick budget, batching, pause, bounded queue/drop counter |
| `test_can_interface_setup.py` | `ip -j -d link` parsing, command building, `pkexec` path, EBUSY retry |
| `test_can_bus_manager.py` | Backend selection, per-backend kwargs, connect errors, send/receive |
| `test_connection_manager.py` | Interface-down dialog wiring, kernel vs configured bitrate |
| `test_interface_setup_dialog.py` | Dialog states (copy command, bring up, failures) |
| `test_settings_dialog.py` | New settings round-trip (performance limits, bring-up flag) |
| `test_perf_regression.py` | **slow**: per-frame cost must not grow with the row count |

## Load benchmark

`tools/general/bench_ui_feed.py` pushes synthetic frames through the real
pipeline (queue → UI handler → table) and prints tick latency, row count and
dropped frames. Useful to reproduce field reports without hardware:

```bash
python tools/general/bench_ui_feed.py --rate 3000 --seconds 15 --mode monitor
python tools/general/bench_ui_feed.py --rate 2000 --seconds 15 --mode tracer --max-rows 5000
```

Exit code is `2` when the p95 tick exceeds twice the timer interval, so it can
gate a nightly job (see `.github/workflows/ci-test.yml`).

## Writing tests

- Prefer the factories: `make_table(tracer=True)` gives you
  `(table, manager, handler, parent)` with a real `QTableWidget`.
- Never call `subprocess` in a test — pass a runner to
  `can_interface_setup` functions instead.
- For timing, assert **ratios** (see `test_perf_regression.py`), not absolute
  milliseconds; CI machines vary too much.
