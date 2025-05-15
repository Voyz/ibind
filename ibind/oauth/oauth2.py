# Combined imports
from dataclasses import dataclass, field
from typing import Optional
from ibind import var
from ibind.oauth import OAuthConfig # For OAuth2Config parent
import base64
import json
import math
import pprint
import requests
import time
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from ibind.support.logs import project_logger

# OAuth2Config class definition
@dataclass
class OAuth2Config(OAuthConfig):
    """
    Dataclass encapsulating OAuth 2.0 configuration parameters.
    """

    # --- Core OAuth 2.0 Parameters ---
    client_id: str = var.IBIND_OAUTH2_CLIENT_ID
    client_key_id: str = var.IBIND_OAUTH2_CLIENT_KEY_ID

    # --- Direct Credential Storage ---
    private_key_pem: Optional[str] = var.IBIND_OAUTH2_PRIVATE_KEY_PEM
    username: Optional[str] = var.IBIND_OAUTH2_USERNAME

    # Optional: Pre-configured IP address. If None, will be auto-fetched.
    ip_address: Optional[str] = var.IBIND_OAUTH2_IP_ADDRESS

    # --- OAuth 2.0 Endpoints and Settings (with defaults) ---
    token_url: str = field(default=var.IBIND_OAUTH2_TOKEN_URL or 'https://api.ibkr.com/oauth2/api/v1/token')
    sso_session_url: str = field(default=var.IBIND_OAUTH2_SSO_SESSION_URL or 'https://api.ibkr.com/gw/api/v1/sso-sessions')
    audience: str = field(default=var.IBIND_OAUTH2_AUDIENCE or '/token')
    scope: str = field(default=var.IBIND_OAUTH2_SCOPE or 'sso-sessions.write')

    # --- IBKR API Base URL (after successful OAuth) ---
    oauth_rest_url: str = var.IBIND_OAUTH2_REST_URL or var.IBIND_REST_URL or 'https://api.ibkr.com/v1/api/'
    oauth_ws_url: str = var.IBIND_OAUTH2_WS_URL or var.IBIND_WS_URL or 'wss://api.ibkr.com/v1/api/ws'

    # --- Token Storage ---
    access_token: Optional[str] = field(default=None, init=False)
    sso_bearer_token: Optional[str] = field(default=None, init=False)

    def version(self):
        return 2.0

    def verify_config(self) -> None:
        required_params = [
            'client_id',
            'client_key_id',
            'private_key_pem',
            'username',
            'token_url',
            'sso_session_url',
            'audience',
            'scope'
        ]
        missing_params = [param for param in required_params if not getattr(self, param)]
        if missing_params:
            raise ValueError(f'OAuth2Config is missing required parameters: {", ".join(missing_params)}')
        super().verify_config()

# Original oauth2.py logic starts here
_LOGGER = project_logger(__file__)

def _get_public_ip():
    """Fetches the public IP address from an external service."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        ip_address = response.json()["ip"]
        _LOGGER.info(f"Successfully fetched public IP address: {ip_address}")
        return ip_address
    except requests.exceptions.RequestException as e:
        _LOGGER.error(f"Could not fetch public IP address: {e}")
        return None
    except json.JSONDecodeError as e:
        _LOGGER.error(f"Could not parse IP address from response: {e}")
        return None

class OAuth2Handler:
    """
    Handles the OAuth 2.0 authentication flow with Interactive Brokers.
    Adapted from the original IBOAuthAuthenticator.
    """
    def __init__(self, config: OAuth2Config, private_key_pem: str, username: str, ip_address: str):
        self.config = config
        self.username = username
        self.ip_address = ip_address
        if not private_key_pem:
            raise ValueError("Private key PEM cannot be empty.")
        try:
            self.jwt_private_key = RSA.import_key(private_key_pem.replace('\\\\n', '\\n'))
        except Exception as e:
            raise ValueError(f"Failed to import private key: {e}")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "python/3.11"})

    def _base64_encode(self, val: bytes) -> str:
        return base64.b64encode(val).decode().replace('+', '-').replace('/', '_').rstrip('=')

    def _make_jws(self, header: dict, claims: dict) -> str:
        json_header = json.dumps(header, separators=(',', ':')).encode()
        encoded_header = self._base64_encode(json_header)
        json_claims = json.dumps(claims, separators=(',', ':')).encode()
        encoded_claims = self._base64_encode(json_claims)
        payload = f"{encoded_header}.{encoded_claims}"
        md = SHA256.new(payload.encode())
        signer = PKCS1_v1_5.new(self.jwt_private_key)
        signature = signer.sign(md)
        encoded_signature = self._base64_encode(signature)
        return payload + "." + encoded_signature

    def _compute_client_assertion(self, url_for_assertion: str) -> str:
        now = math.floor(time.time())
        header = {
            'alg': 'RS256',
            'typ': 'JWT',
            'kid': self.config.client_key_id
        }
        if url_for_assertion == self.config.token_url:
            claims = {
                'iss': self.config.client_id,
                'sub': self.config.client_id,
                'aud': self.config.audience,
                'exp': now + 60,
                'iat': now - 10
            }
        elif url_for_assertion == self.config.sso_session_url:
            claims = {
                'ip': self.ip_address,
                'credential': self.username,
                'iss': self.config.client_id,
                'exp': now + 86400,
                'iat': now
            }
        else:
            raise ValueError(f"Unknown URL for client assertion: {url_for_assertion}")
        assertion = self._make_jws(header, claims)
        return assertion

    def _pretty_request_response(self, resp: requests.Response) -> str:
        req = resp.request
        rqh = '\\n'.join(f"{k}: {v}" for k, v in req.headers.items())
        rqh = rqh.replace(', ', ',\\n    ')
        rqb = req.body if req.body else ""
        if isinstance(rqb, bytes):
            rqb = rqb.decode('utf-8', errors='replace')
        try:
            rsb = f"\\n{pprint.pformat(resp.json())}\\n" if resp.text else ""
        except json.JSONDecodeError:
            rsb = resp.text
        resp_headers_to_print = ["Content-Type", "Content-Length", "Date", "Set-Cookie", "User-Agent", "Cookie", "Cache-Control", "Host"]
        rsh = '\\n'.join([f"{k}: {v}" for k, v in resp.headers.items() if k in resp_headers_to_print])
        return_str = '\\n'.join([
            '-----------REQUEST-----------',
            f"{req.method} {req.url}",
            "",
            rqh,
            str(rqb),
            "",
            '-----------RESPONSE-----------',
            f"{resp.status_code} {resp.reason}",
            rsh,
            f"{rsb}\\n",
            "",
        ])
        return return_str

    def get_access_token(self) -> Optional[str]:
        url = self.config.token_url
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        form_data = {
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': self._compute_client_assertion(url),
            'grant_type': 'client_credentials',
            'scope': self.config.scope
        }
        try:
            _LOGGER.info(f"Requesting OAuth 2.0 Access Token from {url}")
            response = self.session.post(url=url, headers=headers, data=form_data, timeout=10)
            _LOGGER.debug(self._pretty_request_response(response))
            response.raise_for_status()
            token = response.json().get("access_token")
            if token:
                _LOGGER.info("Successfully obtained OAuth 2.0 Access Token.")
            else:
                _LOGGER.error("Failed to obtain OAuth 2.0 Access Token from response.")
            return token
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error getting access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                _LOGGER.error(f"Response body: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Error decoding JSON response for access token: {e}")
            if 'response' in locals() and response:
                 _LOGGER.error(f"Response body: {response.text}")
            return None

    def get_sso_bearer_token(self, access_token: str) -> Optional[str]:
        if not access_token:
            _LOGGER.error("Cannot get SSO bearer token without an access token.")
            return None
        url = self.config.sso_session_url
        headers = {
            "Authorization": "Bearer " + access_token,
            "Content-Type": "application/jwt"
        }
        signed_request = self._compute_client_assertion(url)
        try:
            _LOGGER.info(f"Requesting SSO Bearer Token from {url}")
            response = self.session.post(url=url, headers=headers, data=signed_request, timeout=10)
            _LOGGER.debug(self._pretty_request_response(response))
            response.raise_for_status()
            sso_token = response.json().get("access_token")
            if sso_token:
                _LOGGER.info("Successfully obtained SSO Bearer Token.")
            else:
                _LOGGER.error("Failed to obtain SSO Bearer Token from response.")
            return sso_token
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Error getting SSO bearer token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                _LOGGER.error(f"Response body: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Error decoding JSON response for SSO bearer token: {e}")
            if 'response' in locals() and response:
                _LOGGER.error(f"Response body: {response.text}")
            return None

    def authenticate(self) -> Optional[str]:
        _LOGGER.info("Starting OAuth 2.0 authentication flow within OAuth2Handler.")
        access_token = self.get_access_token()
        if not access_token:
            _LOGGER.error("Authentication failed: Could not retrieve access token.")
            return None
        sso_bearer_token = self.get_sso_bearer_token(access_token)
        if not sso_bearer_token:
            _LOGGER.error("Authentication failed: Could not retrieve SSO bearer token.")
            return None
        self.config.access_token = access_token
        self.config.sso_bearer_token = sso_bearer_token
        _LOGGER.info("OAuth 2.0 authentication successful. Tokens stored in config.")
        return sso_bearer_token

def authenticate_oauth2(config: OAuth2Config) -> Optional[str]:
    _LOGGER.info(f"Starting OAuth 2.0 authentication with client ID: {config.client_id}")
    if not config.private_key_pem:
        _LOGGER.error("OAuth 2.0 Authentication: Missing private_key_pem in config.")
        raise ValueError("private_key_pem must be provided in OAuth2Config.")
    if not config.username:
        _LOGGER.error("OAuth 2.0 Authentication: Missing username in config.")
        raise ValueError("username must be provided in OAuth2Config.")
    ip_address_to_use = config.ip_address
    if not ip_address_to_use:
        _LOGGER.info("IP address not found in config, attempting to fetch public IP.")
        ip_address_to_use = _get_public_ip()
        if not ip_address_to_use:
            _LOGGER.error("Failed to obtain public IP address. Cannot proceed with OAuth 2.0 authentication.")
            return None
        config.ip_address = ip_address_to_use
    else:
        _LOGGER.info(f"Using pre-configured IP address from config: {ip_address_to_use}")
    try:
        handler = OAuth2Handler(
            config=config,
            private_key_pem=config.private_key_pem,
            username=config.username,
            ip_address=ip_address_to_use
        )
        sso_bearer_token = handler.authenticate()
        if sso_bearer_token:
            _LOGGER.info("OAuth 2.0 authentication successful. SSO Bearer Token obtained.")
        else:
            _LOGGER.error("OAuth 2.0 authentication failed.")
        return sso_bearer_token
    except ValueError as ve:
        _LOGGER.error(f"Configuration error during OAuth 2.0 authentication: {ve}")
        return None
    except Exception as e:
        _LOGGER.error(f"Unexpected error during OAuth 2.0 authentication: {e}", exc_info=True)
        return None
