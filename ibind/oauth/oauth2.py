# Combined imports
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
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
import logging
from ibind.support.errors import ExternalBrokerError # Ensure this is imported

_LOGGER = project_logger(__file__)

# Forward declaration for type hint if IbkrClient is not fully imported
if TYPE_CHECKING:
    from ibind.client.ibkr_client import IbkrClient

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

    def has_sso_bearer_token(self) -> bool:
        """Checks if an SSO bearer token is present and non-empty."""
        return bool(hasattr(self, 'sso_bearer_token') and self.sso_bearer_token)

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
def _get_public_ip():
    """Fetches the public IP address from an external service."""
    try:
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        response.raise_for_status()
        ip_address = response.json()["ip"]
        _LOGGER.debug(f"Successfully fetched public IP address: {ip_address}")
        return ip_address
    except requests.exceptions.RequestException as e:
        _LOGGER.error(f"Could not fetch public IP address: {e}")
        return None
    except json.JSONDecodeError as e:
        _LOGGER.error(f"Could not parse IP address from response: {e}")
        return None
    except KeyError as e:
        _LOGGER.error(f"Could not extract IP from response (KeyError: {e})")
        return None
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred while fetching public IP: {e}")
        return None

class OAuth2Handler:
    """
    Handles the OAuth 2.0 authentication flow with Interactive Brokers.
    Adapted from an earlier proof-of-concept script (e.g., a standalone IBOAuthAuthenticator).
    """
    def __init__(self, client: 'IbkrClient'):
        self.client = client
        if not self.client.oauth_config.private_key_pem:
            raise ValueError("Private key PEM cannot be empty (accessed via client.oauth_config).")
        try:
            self.jwt_private_key = RSA.import_key(
                self.client.oauth_config.private_key_pem.replace('\\\\n', '\\n')
            )
        except Exception as e:
            raise ValueError(f"Failed to import private key: {e}")

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
            'kid': self.client.oauth_config.client_key_id
        }
        if url_for_assertion == self.client.oauth_config.token_url:
            claims = {
                'iss': self.client.oauth_config.client_id,
                'sub': self.client.oauth_config.client_id,
                'aud': self.client.oauth_config.audience,
                'exp': now + 60,
                'iat': now - 10
            }
        elif url_for_assertion == self.client.oauth_config.sso_session_url:
            claims = {
                'ip': self.client.oauth_config.ip_address,
                'credential': self.client.oauth_config.username,
                'iss': self.client.oauth_config.client_id,
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
        rqh = rqh.replace(', ', '\\n    ')
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
        """Gets an OAuth 2.0 access token."""
        url = self.client.oauth_config.token_url
        client_assertion = self._compute_client_assertion(url)
        form_data = {
            'grant_type': 'client_credentials',
            'scope': self.client.oauth_config.scope,
            'client_id': self.client.oauth_config.client_id,
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': client_assertion
        }
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        _LOGGER.debug(f"Requesting OAuth 2.0 Access Token from {url}")
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Access Token Request Headers (to be passed to client._request): {headers}")
            _LOGGER.debug(f"Access Token Request Form Data (to be passed to client._request): {pprint.pformat(form_data)}")

        try:
            result = self.client._request(
                method='POST',
                endpoint=url,
                base_url='',
                extra_headers=headers,
                data=form_data
            )
            if not result or not isinstance(result.data, dict):
                _LOGGER.error(f"Failed to obtain OAuth 2.0 Access Token. Result: {result.data if result and hasattr(result, 'data') else 'Result object missing or data attribute missing'}")
                return None

            token_data = result.data
            access_token = token_data.get('access_token')
            if not access_token:
                _LOGGER.error(f"access_token not found in response: {token_data}")
                return None
            _LOGGER.info("Successfully obtained OAuth 2.0 Access Token.")
            return access_token
        except ExternalBrokerError as e:
            _LOGGER.error(f"HTTP error obtaining OAuth 2.0 Access Token via client._request: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error obtaining OAuth 2.0 Access Token via client._request: {e}", exc_info=True)
            return None

    def get_sso_bearer_token(self, access_token: str) -> Optional[str]:
        """Gets an SSO bearer token using a previously obtained access_token."""
        if not access_token:
            _LOGGER.error("Cannot get SSO bearer token without an access token.")
            return None

        url = self.client.oauth_config.sso_session_url
        signed_request_assertion_jwt = self._compute_client_assertion(url)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/jwt',
            'Accept': 'application/json'
        }

        _LOGGER.debug(f"Requesting SSO Bearer Token from {url}")
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"SSO Bearer Token Request Headers (to be passed to client._request): {headers}")
            _LOGGER.debug(f"SSO Bearer Token Request Body (JWT Assertion, to be passed to client._request): {signed_request_assertion_jwt[:100]}...")

        try:
            result = self.client._request(
                method='POST',
                endpoint=url,
                base_url='',
                extra_headers=headers,
                data=signed_request_assertion_jwt
            )
            if not result or not isinstance(result.data, dict):
                _LOGGER.error(f"Failed to obtain SSO Bearer Token. Result: {result.data if result and hasattr(result, 'data') else 'Result object missing or data attribute missing'}")
                return None

            sso_data = result.data
            sso_bearer_token = sso_data.get('access_token')
            if not sso_bearer_token:
                _LOGGER.error(f"SSO Bearer Token ('access_token') not found in response: {sso_data}")
                return None
            _LOGGER.info("Successfully obtained SSO Bearer Token.")
            return sso_bearer_token
        except ExternalBrokerError as e:
            _LOGGER.error(f"HTTP error obtaining SSO Bearer Token via client._request: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error obtaining SSO Bearer Token via client._request: {e}", exc_info=True)
            return None

    def authenticate(self) -> Optional[str]:
        _LOGGER.debug("Starting OAuth 2.0 authentication flow within OAuth2Handler.")
        access_token = self.get_access_token()
        if not access_token:
            _LOGGER.error("Authentication failed: Could not retrieve access token.")
            return None
        sso_bearer_token = self.get_sso_bearer_token(access_token)
        if not sso_bearer_token:
            _LOGGER.error("Authentication failed: Could not retrieve SSO bearer token.")
            return None
        self.client.oauth_config.access_token = access_token
        self.client.oauth_config.sso_bearer_token = sso_bearer_token
        _LOGGER.info("OAuth 2.0 authentication successful. Tokens stored in client.oauth_config.")
        _LOGGER.debug(f"OAuth 2.0 Authentication successful. SSO Token: {self.client.oauth_config.sso_bearer_token[:20]}... (truncated)")
        return sso_bearer_token

def authenticate_oauth2(client: 'IbkrClient') -> Optional[str]:
    """Main function to authenticate using OAuth 2.0 and return the SSO Bearer Token."""
    config = client.oauth_config
    _LOGGER.info(f"Starting OAuth 2.0 authentication for client_id: {config.client_id}, username: {config.username}")

    config.verify_config()

    if not config.ip_address:
        _LOGGER.info("IP address not configured, attempting to fetch public IP.")
        config.ip_address = _get_public_ip()
        if not config.ip_address:
            _LOGGER.error("Failed to obtain public IP address. Cannot proceed with OAuth 2.0.")
            return None
        _LOGGER.info(f"Using auto-detected public IP: {config.ip_address}")
    else:
        _LOGGER.info(f"Using pre-configured IP address: {config.ip_address}")

    if not config.private_key_pem:
        if var.IBIND_OAUTH2_PRIVATE_KEY_PATH:
             _LOGGER.error(f"private_key_pem is not set, but IBIND_OAUTH2_PRIVATE_KEY_PATH ({var.IBIND_OAUTH2_PRIVATE_KEY_PATH}) was. This suggests a load failure from path in OAuth2Config.__post_init__.")
        else:
            _LOGGER.error("private_key_pem is not set and no private key path was configured via IBIND_OAUTH2_PRIVATE_KEY_PATH. Cannot proceed.")
        return None

    try:
        handler = OAuth2Handler(client=client)
        sso_token = handler.authenticate()
        if sso_token:
            _LOGGER.info("OAuth 2.0 Authentication successful. SSO Token obtained and stored in client.oauth_config.")
            return sso_token
        else:
            _LOGGER.error("OAuth 2.0 Authentication failed: handler.authenticate() returned None. Check OAuth2Handler logs for more details (e.g., issues in get_access_token or get_sso_bearer_token).")
            return None
    except ValueError as e:
        _LOGGER.error(f"OAuth 2.0 authentication failed due to ValueError: {e}", exc_info=True)
        return None
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred during OAuth 2.0 authentication process: {e}", exc_info=True)
        return None

def establish_oauth2_brokerage_session(client: 'IbkrClient') -> None:
    """
    Establishes the brokerage session for an OAuth 2.0 authenticated client.

    This involves validating the SSO session and then initializing the brokerage session.
    """
    _LOGGER.debug(f"{client}: OAuth 2.0: Attempting to establish brokerage session (/sso/validate and initialize).")

    try:
        validation_result = client.validate()
        _LOGGER.debug(f"{client}: /sso/validate result: {validation_result.data if validation_result else 'No result'}")

        sso_is_valid = False
        if validation_result and hasattr(validation_result, 'data') and isinstance(validation_result.data, dict):
            if validation_result.data.get('RESULT') is True:
                sso_is_valid = True
                _LOGGER.debug(f"{client}: /sso/validate deemed successful based on 'RESULT': True.")
            elif validation_result.data.get('authenticated') is True:  # Fallback check
                sso_is_valid = True
                _LOGGER.debug(f"{client}: /sso/validate deemed successful based on 'authenticated': True.")

        if not sso_is_valid:
            _LOGGER.warning(
                f"{client}: /sso/validate did not indicate a clear success. "
                f"Cannot proceed with brokerage session initialization. "
                f"Validation data: {validation_result.data if validation_result else 'No result'}"
            )
            return

        _LOGGER.debug(f"{client}: /sso/validate successful. Now attempting to initialize brokerage session.")
        try:
            _LOGGER.debug(f"{client}: Calling initialize_brokerage_session(compete=True).")
            init_result = client.initialize_brokerage_session(compete=True)
            _LOGGER.debug(f"{client}: initialize_brokerage_session(compete=True) result: {init_result.data if init_result else 'No result'}")

            auth_status_after_init = client.authentication_status()
            _LOGGER.debug(f"{client}: /iserver/auth/status (after compete=True init): {auth_status_after_init.data if auth_status_after_init else 'No result'}")
            if not (auth_status_after_init and auth_status_after_init.data and auth_status_after_init.data.get('authenticated')):
                _LOGGER.warning(f"{client}: Still not authenticated after compete=True init.")

        except ExternalBrokerError as e_init_compete_true:
            _LOGGER.error(f"{client}: initialize_brokerage_session(compete=True) failed: {e_init_compete_true}")
            if e_init_compete_true.status_code == 500 and "failed to generate sso dh token" in str(e_init_compete_true):
                _LOGGER.warning(f"{client}: Retrying initialize_brokerage_session with compete=False due to DH token error.")
                try:
                    init_result_false = client.initialize_brokerage_session(compete=False)
                    _LOGGER.debug(f"{client}: initialize_brokerage_session(compete=False) result: {init_result_false.data if init_result_false else 'No result'}")

                    auth_status_after_init_false = client.authentication_status()
                    _LOGGER.debug(f"{client}: /iserver/auth/status (after compete=False init): {auth_status_after_init_false.data if auth_status_after_init_false else 'No result'}")
                    if not (auth_status_after_init_false and auth_status_after_init_false.data and auth_status_after_init_false.data.get('authenticated')):
                        _LOGGER.warning(f"{client}: Still not authenticated after compete=False init.")
                except Exception as e_init_compete_false:
                    _LOGGER.error(f"{client}: initialize_brokerage_session(compete=False) also failed: {e_init_compete_false}")
            # else: other error from compete=True, not the DH token one. We just log it above.
        except Exception as e_init_generic:
            _LOGGER.error(f"{client}: A generic error occurred during initialize_brokerage_session(compete=True): {e_init_generic}")

    except Exception as e_validate_sequence:
        _LOGGER.error(f"{client}: Error during /sso/validate or subsequent brokerage session initialization sequence: {e_validate_sequence}")
