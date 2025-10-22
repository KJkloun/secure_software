# tests/conftest.py
import sys
from pathlib import Path

import pytest

try:
    from app.main import attachment_storage, rate_limiter, storage
except ModuleNotFoundError:  # pragma: no cover - fallback for CI env
    ROOT = Path(__file__).resolve().parents[1]  # корень репозитория
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from app.main import attachment_storage, rate_limiter, storage


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    storage.clear()
    rate_limiter.reset()
    attachment_storage.configure(tmp_path / "uploads")
    yield
    storage.clear()
    rate_limiter.reset()
