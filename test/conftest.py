import pytest

from ibind import ibind_logs_initialize


@pytest.fixture(scope='module', autouse=True)
def configure_logs():
    ibind_logs_initialize(log_to_console=True, log_to_file=False)
