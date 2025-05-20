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
import logging

_LOGGER = project_logger(__file__)

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
    def __init__(self, config: OAuth2Config, private_key_pem: str, username: str, ip_address: str):
        self.config = config
        self.username = username
        self.ip_address = ip_address
        if not private_key_pem:
            raise ValueError("Private key PEM cannot be empty.")
        try:
            self.jwt_private_key = RSA.import_key(private_key_pem.replace('\\n', '\n'))
        except Exception as e:
            raise ValueError(f"Failed to import private key: {e}")
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/x-www-form-urlencoded'})

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
        url = self.config.token_url
        client_assertion = self._compute_client_assertion(url)
        form_data = {
            'grant_type': 'client_credentials',
            'scope': self.config.scope,
            'client_id': self.config.client_id,
            'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
            'client_assertion': client_assertion
        }
        headers = {
            'Accept': 'application/json'
        }

        _LOGGER.debug(f"Requesting OAuth 2.0 Access Token from {url}")
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"Access Token Request Headers: {headers}")
            _LOGGER.debug(f"Access Token Request Form Data: {pprint.pformat(form_data)}")

        try:
            resp = self.session.post(url, headers=headers, data=form_data, timeout=10)
            _LOGGER.debug(f"Access Token Response Status: {resp.status_code}")
            if _LOGGER.isEnabledFor(logging.DEBUG):
                 _LOGGER.debug(f"Access Token Response Headers: {resp.headers}")
                 _LOGGER.debug(f"Access Token Response Content: {self._pretty_request_response(resp)}")
            resp.raise_for_status()
            token_data = resp.json()
            access_token = token_data.get('access_token')
            if not access_token:
                _LOGGER.error(f"access_token not found in response: {token_data}")
                return None
            _LOGGER.info("Successfully obtained OAuth 2.0 Access Token.")
            return access_token
        except requests.exceptions.HTTPError as e:
            _LOGGER.error(f"HTTP error obtaining OAuth 2.0 Access Token: {e}\nResponse content: {e.response.text if e.response else 'N/A'}")
            return None
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Request exception obtaining OAuth 2.0 Access Token: {e}")
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON decode error obtaining OAuth 2.0 Access Token: {e}\nResponse content: {resp.text if 'resp' in locals() and hasattr(resp, 'text') else 'N/A'}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error obtaining OAuth 2.0 Access Token: {e}\nResponse content: {resp.text if 'resp' in locals() and hasattr(resp, 'text') else 'N/A'}")
            return None

    def get_sso_bearer_token(self, access_token: str) -> Optional[str]:
        """Gets an SSO bearer token using a previously obtained access_token."""
        if not access_token:
            _LOGGER.error("Cannot get SSO bearer token without an access token.")
            return None

        url = self.config.sso_session_url
        signed_request_assertion_jwt = self._compute_client_assertion(url)

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/jwt',
            'Accept': 'application/json'
        }

        _LOGGER.debug(f"Requesting SSO Bearer Token from {url}")
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(f"SSO Bearer Token Request Headers: {headers}")
            _LOGGER.debug(f"SSO Bearer Token Request Body (JWT Assertion): {signed_request_assertion_jwt[:100]}...")

        try:
            resp = self.session.post(url, headers=headers, data=signed_request_assertion_jwt, timeout=10)
            _LOGGER.debug(f"SSO Bearer Token Response Status: {resp.status_code}")
            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug(f"SSO Bearer Token Response Headers: {resp.headers}")
                _LOGGER.debug(f"SSO Bearer Token Response Content: {self._pretty_request_response(resp)}")
            resp.raise_for_status()
            sso_data = resp.json()
            sso_bearer_token = sso_data.get('access_token')
            if not sso_bearer_token:
                _LOGGER.error(f"SSO Bearer Token ('access_token') not found in response: {sso_data}")
                return None
            _LOGGER.info("Successfully obtained SSO Bearer Token.")
            return sso_bearer_token
        except requests.exceptions.HTTPError as e:
            _LOGGER.error(f"HTTP error obtaining SSO Bearer Token: {e}\nResponse content: {e.response.text if e.response else 'N/A'}")
            return None
        except requests.exceptions.RequestException as e:
            _LOGGER.error(f"Request exception obtaining SSO Bearer Token: {e}")
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error(f"JSON decode error obtaining SSO Bearer Token: {e}\nResponse content: {resp.text if 'resp' in locals() and hasattr(resp, 'text') else 'N/A'}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error obtaining SSO Bearer Token: {e}\nResponse content: {resp.text if 'resp' in locals() and hasattr(resp, 'text') else 'N/A'}")
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
        self.config.access_token = access_token
        self.config.sso_bearer_token = sso_bearer_token
        _LOGGER.info("OAuth 2.0 authentication successful. Tokens stored in config.")
        _LOGGER.debug(f"OAuth 2.0 Authentication successful. SSO Token: {self.config.sso_bearer_token[:20]}... (truncated)")
        return sso_bearer_token

def authenticate_oauth2(config: OAuth2Config) -> Optional[str]:
    """Main function to authenticate using OAuth 2.0 and return the SSO Bearer Token."""
    _LOGGER.info(f"Starting OAuth 2.0 authentication for client_id: {config.client_id}, username: {config.username}")

    config.verify_config() # Ensure basic config is present

    if not config.ip_address:
        _LOGGER.info("IP address not configured, attempting to fetch public IP.")
        config.ip_address = _get_public_ip()
        if not config.ip_address:
            _LOGGER.error("Failed to obtain public IP address. Cannot proceed with OAuth 2.0.")
            return None
        _LOGGER.info(f"Using auto-detected public IP: {config.ip_address}")
    else:
        _LOGGER.info(f"Using pre-configured IP address: {config.ip_address}")

    # Ensure private_key_pem is loaded if path was provided (OAuth2Config now handles this in __post_init__)
    # However, an explicit check here adds robustness if __post_init__ logic changes or fails silently.
    if not config.private_key_pem:
        # Check if path was available and __post_init__ should have loaded it
        if var.IBIND_OAUTH2_PRIVATE_KEY_PATH: # Check original env var for path
             _LOGGER.error(f"private_key_pem is not set, but IBIND_OAUTH2_PRIVATE_KEY_PATH ({var.IBIND_OAUTH2_PRIVATE_KEY_PATH}) was. This suggests a load failure from path in OAuth2Config.__post_init__.")
        else:
            _LOGGER.error("private_key_pem is not set and no private key path was configured via IBIND_OAUTH2_PRIVATE_KEY_PATH. Cannot proceed.")
        return None

    try:
        handler = OAuth2Handler(
            config=config,
            private_key_pem=config.private_key_pem,
            username=config.username,
            ip_address=config.ip_address
        )
        sso_token = handler.authenticate()
        if sso_token:
            config.sso_bearer_token = sso_token # Store on the config object for client use
            _LOGGER.info("OAuth 2.0 Authentication successful. SSO Token obtained and stored.")
            return sso_token
        else:
            # More detailed logging if authenticate() returns None
            _LOGGER.error("OAuth 2.0 Authentication failed: handler.authenticate() returned None. Check OAuth2Handler logs for more details (e.g., issues in get_access_token or get_sso_bearer_token).")
            return None
    except ValueError as e:
        _LOGGER.error(f"OAuth 2.0 authentication failed due to ValueError: {e}", exc_info=True) # Added exc_info
        return None
    except Exception as e:
        _LOGGER.error(f"An unexpected error occurred during OAuth 2.0 authentication process: {e}", exc_info=True) # Added exc_info
        return None
