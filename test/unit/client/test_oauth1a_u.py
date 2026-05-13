from urllib.parse import unquote_plus

import pytest

pytest.importorskip('Crypto')

from ibind.client.ibkr_client import IbkrClient
from ibind.oauth.oauth1a import OAuth1aConfig, generate_oauth_headers
from ibind.base.rest_client import Result


def test_generate_oauth_headers_omits_static_host_and_includes_request_params(monkeypatch):
    ## Arrange
    captured = {}
    config = OAuth1aConfig(consumer_key='consumer', access_token='access', realm='realm')  # noqa: S106

    monkeypatch.setattr('ibind.oauth.oauth1a.generate_oauth_nonce', lambda: 'nonce')
    monkeypatch.setattr('ibind.oauth.oauth1a.generate_request_timestamp', lambda: '123')

    def fake_signature(base_string, live_session_token):
        captured['base_string'] = base_string
        captured['live_session_token'] = live_session_token
        return 'signature'

    monkeypatch.setattr('ibind.oauth.oauth1a.generate_hmac_sha_256_signature', fake_signature)

    ## Act
    headers = generate_oauth_headers(
        oauth_config=config,
        request_method='GET',
        request_url='https://1.api.ibkr.com/v1/api/iserver/accounts',
        live_session_token='live-token',  # noqa: S106
        request_params={'accountId': 'DU123'},
    )

    ## Assert
    assert 'Host' not in headers
    assert captured['live_session_token'] == 'live-token'  # noqa: S105
    assert 'accountId=DU123' in unquote_plus(captured['base_string'])


def test_oauth_get_request_passes_query_params_to_signature(mocker):
    ## Arrange
    client = IbkrClient(url='https://1.api.ibkr.com/v1/api/', use_oauth=False, use_session=False, auto_register_shutdown=False)
    client._use_oauth = True
    client.oauth_config = OAuth1aConfig(consumer_key='consumer', access_token='access', realm='realm')  # noqa: S106
    client.live_session_token = 'live-token'  # noqa: S105
    client._process_response = mocker.MagicMock(return_value=Result(data={'ok': True}))

    generate_headers = mocker.patch('ibind.oauth.oauth1a.generate_oauth_headers', return_value={'Authorization': 'OAuth test'})
    request = mocker.patch('ibind.base.rest_client.requests.request')
    request.return_value = mocker.MagicMock()

    ## Act
    client.get('iserver/accounts', params={'accountId': 'DU123'})

    ## Assert
    generate_headers.assert_called_once()
    assert generate_headers.call_args.kwargs['request_params'] == {'accountId': 'DU123'}
