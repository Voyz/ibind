import base64
import secrets
import string
import time
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING
from urllib import parse

from Crypto.Cipher import PKCS1_v1_5 as PKCS1_v1_5_Cipher
from Crypto.Hash import SHA256, HMAC, SHA1
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_Signature

from ibind import var

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient


@dataclass
class OAuthConfig():
    """ Dataclass encapsulating OAuth configuration parameters. """

    live_session_token_endpoint: str = var.IBIND_LIVE_SESSION_TOKEN_ENDPOINT
    """ Endpoint for OAuth Live Session Token. """

    access_token: str = var.IBIND_ACCESS_TOKEN
    """ OAuth access token generated in the self-service portal. """

    access_token_secret: str = var.IBIND_ACCESS_TOKEN_SECRET
    """ OAuth access token secret generated in the self-service portal. """

    consumer_key: str = var.IBIND_CONSUMER_KEY
    """ The consumer key configured during the onboarding process. This uniquely identifies the project in the IBKR ecosystem. """

    dh_prime: str = var.IBIND_DH_PRIME
    """ The hex representation of the Diffie-Hellman prime. """

    encryption_key_fp: str = var.IBIND_ENCRYPTION_KEY_FP
    """ The path to the private OAuth encryption key. """

    signature_key_fp: str = var.IBIND_SIGNATURE_KEY_FP
    """ The path to the private OAuth signature key. """

    dh_generator: str = var.IBIND_DH_GENERATOR
    """ The Diffie-Hellman generator value. """

    realm: str = var.IBIND_REALM
    """ OAuth connection type. This is generally set to "limited_poa", however should be set to "test_realm" when using the TESTCONS consumer key. """

    init_oauth: bool = var.IBIND_INIT_OAUTH
    """ Whether OAuth should be automatically initialised. """

    maintain_oauth: bool = var.IBIND_MAINTAIN_OAUTH
    """ Whether OAuth should be automatically maintained. """

    shutdown_oauth: bool = var.IBIND_SHUTDOWN_OAUTH
    """ Whether OAuth should be automatically stopped on termination. """


def req_live_session_token(client: 'IbkrClient', oauth_config: OAuthConfig) -> tuple[str, int, str]:
    """ Get live session token and access token from IBKR Web API used to make API endpoint calls """

    endpoint = oauth_config.live_session_token_endpoint

    prepend, extra_headers, dh_random = prepare_oauth(oauth_config)

    headers = generate_oauth_headers(
        oauth_config=oauth_config,
        request_method="POST",
        request_url=f'{client.base_url}{endpoint}',
        extra_headers=extra_headers,
        signature_method="RSA-SHA256",
        prepend=prepend
    )

    result = client.post(endpoint, extra_headers=headers)

    lst_expires = result.data["live_session_token_expiration"]
    dh_response = result.data["diffie_hellman_response"]
    lst_signature = result.data["live_session_token_signature"]
    live_session_token = calculate_live_session_token(
        dh_prime=oauth_config.dh_prime,
        dh_random_value=dh_random,
        dh_response=dh_response,
        prepend=prepend
    )

    return live_session_token, lst_expires, lst_signature


def prepare_oauth(oauth_config: OAuthConfig) -> tuple[str, dict, str]:
    dh_random = generate_dh_random_bytes()
    dh_challenge = generate_dh_challenge(
        dh_prime=oauth_config.dh_prime,
        dh_random=dh_random,
        dh_generator=int(oauth_config.dh_generator),
    )
    prepend = calculate_live_session_token_prepend(
        access_token_secret=oauth_config.access_token_secret,
        private_encryption_key=read_private_key(private_key_fp=oauth_config.encryption_key_fp)
    )

    extra_headers = {"diffie_hellman_challenge": dh_challenge}

    return prepend, extra_headers, dh_random


def generate_oauth_headers(
        oauth_config: OAuthConfig,
        request_method: str,
        request_url: str,
        live_session_token: Optional[str] = None,
        extra_headers: Optional[dict[str, str]] = None,
        request_params: dict = None,
        signature_method: str = "HMAC-SHA256",
        prepend: Optional[str] = None,
):
    headers = {
        "oauth_consumer_key": oauth_config.consumer_key,
        "oauth_nonce": generate_oauth_nonce(),
        "oauth_signature_method": signature_method,
        "oauth_timestamp": generate_request_timestamp(),
        "oauth_token": oauth_config.access_token
    }

    if oauth_config.access_token:
        headers.update({"oauth_token": oauth_config.access_token})
    if extra_headers:
        headers.update(extra_headers)

    base_string = generate_base_string(
        request_method=request_method,
        request_url=request_url,
        request_headers=headers,
        request_params=request_params,
        prepend=prepend
    )

    if signature_method == "HMAC-SHA256":
        signature = generate_hmac_sha_256_signature(
            base_string=base_string,
            live_session_token=live_session_token)
    else:
        private_signature_key = read_private_key(oauth_config.signature_key_fp)
        signature = generate_rsa_sha_256_signature(
            base_string=base_string,
            private_signature_key=private_signature_key)

    headers.update({"oauth_signature": signature})
    headers_string = generate_authorization_header_string(
        request_data=headers,
        realm=oauth_config.realm
    )

    header_oauth = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip,deflate",
        "Authorization": headers_string,
        "Connection": "keep-alive",
        "Host": "api.ibkr.com",
        "User-Agent": "ibind"
    }

    return header_oauth


def generate_request_timestamp() -> str:
    """
    Generates the current timestamp in seconds. This is used when generating the request, access and live session tokens.
    """
    return str(int(time.time()))


def read_private_key(private_key_fp: str) -> RSA.RsaKey:
    """
    Reads the private key from the file path provided. The key is used to sign the request and decrypt the access token secret.
    """
    FILE_MODE = "r"
    with open(private_key_fp, FILE_MODE) as f:
        private_key = RSA.importKey(f.read())
    return private_key


def generate_oauth_nonce() -> str:
    """
    Generates a random nonce value. A unique nonce value is generated for each request.
    """
    NONCE_LENGTH = 16
    NONCE_CHARACTERS = string.ascii_letters + string.digits
    return "".join(secrets.choice(NONCE_CHARACTERS) for _ in range(NONCE_LENGTH))


def generate_base_string(
        request_method: str,
        request_url: str,
        request_headers: dict,
        request_params: dict = None,
        request_form_data: dict = None,
        request_body: dict = None,
        extra_headers: dict = None,
        prepend: str = None,
) -> str:
    """
    A lexicographically sorted list of key/value pairs including the authorization header pairs, query parameters and if the request
    contains a body of type x-www-form-urlencoded, the body parameters. The list values are separated using the character '&', then the list is percent
    encoded.
    """
    LIST_SEPARATOR = "&"
    KEY_VALUE_SEPARATOR = "="
    encoded_request_url = parse.quote_plus(request_url)
    # Create a dictionary of any header, params, form data or body data that is not None
    base_string_params = {**request_headers}
    base_string_params.update(request_params or {})
    base_string_params.update(request_form_data or {})
    base_string_params.update(request_body or {})
    base_string_params.update(extra_headers or {})
    oauth_params_string = LIST_SEPARATOR.join(
        [f"{k}{KEY_VALUE_SEPARATOR}{v}" for k, v in sorted(base_string_params.items())]
    )
    encoded_oauth_params_string = parse.quote_plus(oauth_params_string)
    base_string = LIST_SEPARATOR.join(
        [request_method, encoded_request_url, encoded_oauth_params_string]
    )
    if prepend is not None:
        base_string = f"{prepend}{base_string}"
    return base_string


def generate_dh_random_bytes() -> str:
    """
    Generates a random 256 bit number and returns it as a hex value.
    This is used when generating the DH challenge.
    """
    NUM_RANDOM_BITS = 256
    random_bytes = secrets.randbits(NUM_RANDOM_BITS)
    random_bytes_hex = hex(random_bytes)[2:]
    return random_bytes_hex


def generate_dh_challenge(dh_prime: str, dh_random: str, dh_generator: int = 2) -> str:
    """
    Generate the DH challenge using the prime, random and generator values.
    The result needs to be recorded as a hex value and sent to LST endpoint.
    """
    INT_BASE = 16
    dh_challenge = pow(int(dh_generator), int(dh_random, INT_BASE), int(dh_prime, INT_BASE))
    hex_challenge = hex(dh_challenge)[2:]
    return hex_challenge


def calculate_live_session_token_prepend(access_token_secret: str, private_encryption_key: RSA.RsaKey) -> str:
    """
    Decrypts the access token secret using the private encryption key.
    The result is then converted to a hex value, and returned as the prepend
    used when requesting the live session token.
    """
    access_token_secret_bytes = base64.b64decode(access_token_secret)
    cipher = PKCS1_v1_5_Cipher.new(private_encryption_key)
    decrypted_access_token_secret = cipher.decrypt(access_token_secret_bytes, None)
    decrypted_access_token_secret_hex = decrypted_access_token_secret.hex()
    return decrypted_access_token_secret_hex


def generate_rsa_sha_256_signature(base_string: str, private_signature_key: RSA.RsaKey) -> str:
    """
    Generates the signature for the base string using the private signature key.
    The signature is generated using the
    RSA-SHA256 algorithm and is encoded using base64.
    The signature is then decoded to utf-8 and the newline character
    is removed. Finally, the signature is URL encoded.

    This method is used when getting the request, access and live session tokens.
    """
    STRING_ENCODING = "utf-8"
    encoded_base_string = base_string.encode(STRING_ENCODING)
    signer = PKCS1_v1_5_Signature.new(private_signature_key)
    hash = SHA256.new(encoded_base_string)
    signature = signer.sign(hash)
    encoded_signature = base64.encodebytes(signature)
    return parse.quote_plus(encoded_signature.decode(STRING_ENCODING).replace("\n", ""))


def generate_hmac_sha_256_signature(base_string: str, live_session_token: str) -> str:
    """
    When accessing any other endpoint, which means any protected resource, the key used is the live session token as a byte array and the signature
    method is HMAC-SHA256.
    """
    STRING_ENCODING = "utf-8"
    encoded_base_string = base_string.encode(STRING_ENCODING)
    hmac = HMAC.new(bytes(base64.b64decode(live_session_token)), digestmod=SHA256)
    hmac.update(encoded_base_string)
    return parse.quote_plus(base64.b64encode(hmac.digest()).decode(STRING_ENCODING))


def get_access_token_secret_bytes(access_token_secret: str) -> list[int]:
    """
    Converts the access token secret to a byte array. This is used when generating the live session token.
    """
    access_token_secret_bytes = bytearray.fromhex(access_token_secret)
    return [int(byte) for byte in access_token_secret_bytes]


def to_byte_array(x: int) -> list[int]:
    """
    Converts an integer to a byte array. This is used when generating the live session token.
    """
    hex_string = hex(x)[2:]
    if len(hex_string) % 2 > 0:
        hex_string = "0" + hex_string
    byte_array = []
    if len(bin(x)[2:]) % 8 == 0:
        byte_array.append(0)
    for i in range(0, len(hex_string), 2):
        byte_array.append(int(hex_string[i: i + 2], 16))
    return byte_array


def calculate_live_session_token(dh_prime: str, dh_random_value: str, dh_response: str, prepend: str) -> str:
    """
    Calculates the live session token using the DH prime, random value, response and prepend.
    The live session token is used to sign requests for protected resources.
    """
    INT_BASE = 16
    STRING_ENCODING = "utf-8"
    access_token_secret_bytes = get_access_token_secret_bytes(prepend)
    a = int(dh_random_value, INT_BASE)
    B = int(dh_response, INT_BASE)
    K = pow(B, a, int(dh_prime, INT_BASE))
    hmac = HMAC.new(bytes(to_byte_array(K)), digestmod=SHA1)
    hmac.update(bytes(access_token_secret_bytes))
    return base64.b64encode(hmac.digest()).decode(STRING_ENCODING)


def validate_live_session_token(live_session_token: str, live_session_token_signature: str, consumer_key: str) -> bool:
    """
    Validate the calculated live session token against the live session token signature.
    """
    STRING_ENCODING = "utf-8"
    hmac = HMAC.new(bytes(base64.b64decode(live_session_token)), digestmod=SHA1)
    hmac.update(bytes(consumer_key, STRING_ENCODING))
    return hmac.hexdigest() == live_session_token_signature


def generate_authorization_header_string(request_data: dict, realm: str) -> str:
    """
    Generates the authorization header string using the request data. The request data is a dictionary containing the
    key value pairs for the authorization header. The request data is sorted by key and then joined together using the
    character ',' and the string 'OAuth realm=' is prepended to the string. For most cases, the realm is set as limited_poa.
    """
    HEADER_KEY_VALUE_SEPARATOR = "="
    HEADER_KEY_VALUE_PAIR_SEPARATOR = ", "
    authorization_header_keys = HEADER_KEY_VALUE_PAIR_SEPARATOR.join(
        [
            f'{key}{HEADER_KEY_VALUE_SEPARATOR}"{value}"'
            for key, value in sorted(request_data.items())
        ]
    )
    authorization_header_string = f'OAuth realm="{realm}", {authorization_header_keys}'
    return authorization_header_string
