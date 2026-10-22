# Root conftest.py — disables a broken web3 pytest plugin installed system-wide.
# This does NOT affect the project's dependencies (which are listed in requirements-dev.txt).
collect_ignore_glob: list[str] = []

def pytest_configure(config):
    # Suppress the broken web3/pytest_ethereum plugin if present
    try:
        config.pluginmanager.set_blocked("pytest_ethereum")
    except Exception:
        pass
