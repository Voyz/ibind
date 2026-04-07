from pathlib import Path

import pytest

from ibind.client.ibkr_client import IbkrClient
from ibind.oauth.oauth2 import OAuth2Config


def make_oauth2_config(**overrides) -> OAuth2Config:
    config = {
        'client_id': 'client-id',
        'client_key_id': 'key-id',
        'private_key_pem': 'dummy-private-key',
        'username': 'user-name',
    }
    config.update(overrides)
    return OAuth2Config(**config)


def test_oauth2_config_loads_private_key_from_path(tmp_path: Path) -> None:
    key_path = tmp_path / 'private.pem'
    key_path.write_text('file-private-key', encoding='utf-8')

    config = make_oauth2_config(private_key_pem=None, private_key_path=str(key_path))

    assert config.private_key_pem == 'file-private-key'


def test_oauth2_get_headers_skips_token_and_sso_requests() -> None:
    oauth_config = make_oauth2_config()
    oauth_config.sso_bearer_token = 'sso-token'  # noqa: S105
    client = IbkrClient(use_oauth=False, auto_register_shutdown=False)
    client._use_oauth = True
    client.oauth_config = oauth_config

    assert client._get_headers('POST', oauth_config.token_url) == {}
    assert client._get_headers('POST', oauth_config.sso_session_url) == {}


def test_oauth2_get_headers_adds_bearer_token_for_api_requests() -> None:
    oauth_config = make_oauth2_config()
    oauth_config.sso_bearer_token = 'sso-token'  # noqa: S105
    client = IbkrClient(use_oauth=False, auto_register_shutdown=False)
    client._use_oauth = True
    client.oauth_config = oauth_config

    headers = client._get_headers('GET', 'https://api.ibkr.com/v1/api/portfolio/accounts')

    assert headers == {'Authorization': 'Bearer sso-token'}


def test_oauth2_get_headers_without_sso_token_returns_empty_headers(caplog: pytest.LogCaptureFixture) -> None:
    oauth_config = make_oauth2_config()
    client = IbkrClient(use_oauth=False, auto_register_shutdown=False)
    client._use_oauth = True
    client.oauth_config = oauth_config

    with caplog.at_level('ERROR', logger='ibind.oauth.oauth2'):
        headers = client._get_headers('GET', 'https://api.ibkr.com/v1/api/portfolio/accounts')

    assert headers == {}
    assert 'SSO bearer token is missing' in caplog.text
