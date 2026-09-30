import pytest
from app.services.rate_limiter import limiter

@pytest.fixture(autouse=True)
def reset_rate_limiter_for_every_test():
    limiter.reset()
    yield
    limiter.reset()
