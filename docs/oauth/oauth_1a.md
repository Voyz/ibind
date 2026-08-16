# OAuth 1.0a

If you prefer to communicate with the Client Portal Web API without the need to start the CP Gateway (eg. through [IBeam][ibeam]), you can use [OAuth 1.0a][ibkr-oauth1a].

This page covers the basic OAuth 1.0a support in IBind.

* [Enabling OAuth 1.0a](#enabling_oauth1a)
* [Acquiring the DH Prime](#acquiring_dh_prime)
* [Using OAuth 1.0a in IBind](#using_oauth1a_in_ibind)

## <a name="enabling_oauth1a"></a> Enabling OAuth 1.0a

### Prerequisites
1. An IBKR "Pro" account. There should be no explicit approval needed for basic OAuth access, see notes below.
2. [openssl][openssl] installed.

### OAuth 1.0a Setup
1. On your machine run the following commands, ensuring each generates a file:
    ```
    openssl genrsa -out private_signature.pem 2048
    openssl rsa -in private_signature.pem -outform PEM -pubout -out public_signature.pem
    openssl genrsa -out private_encryption.pem 2048
    openssl rsa -in private_encryption.pem -outform PEM -pubout -out public_encryption.pem
    openssl dhparam -out dhparam.pem 2048
    ```
1. Visit the [IBKR OAuth setup page][ibkr-oauth-setup] and login to your account.  
   If the above link takes you to a different version of IBKR than you use in your location then instead do the following:  
   a) Go to your local IBKR login page but don't log in.  
   b) Add the following parameter at the end of the URL `&action=OAUTH` and hit enter to navigate  
   c) Login normally

1. Read the terms and conditions
1. You should now land on the OAuth setup page. At the time of writing this, it looks something like this:

   ![oauth1a_setup_page](https://github.com/user-attachments/assets/9d222fb9-700a-429c-b891-192341a9fc07)

1. Fill out as follows:
    1. Consumer Key: A 9 character password **you** choose (it will convert any alpha characters to upper-case, valid characters are A-Z)
    1. Click "Save Key"
    1. Public Signing Key: Upload the `public_signature.pem` file generated in step 1
    1. Public Encryption Key: Upload the `public_encryption.pem` file generated in step 1
    1. Diffie-Hellman Parameters: Upload the `dhparam.pem` file generated in step 1
1. The next step will generate your "Access Token" and "Access Token Secret." - they will **not** re-appear when you revisit this page.
1. Click "Generate Token". Copy these tokens and store them somewhere safe.
1. Click the toggle switch at the top of the page for "Enable OAuth Access"

### Notes
- Some users have suggested that it can take [24 hours][24-hrs] for OAuth access to be established, however one user heard the following from the support agent: _'Please note that consumer keys will only be activated after the server restart each weekend.'_. It is advisable to wait until the following week for the activation, although feel free to check earlier in case your access is enabled sooner. Some users [commented](https://github.com/Voyz/ibind/issues/109#issuecomment-2900165679) that their activation took up to two weeks.
- As noted on the [IBKR Web API documentation](https://www.interactivebrokers.com/campus/ibkr-api-page/web-api/#introduction-0):

> Much of the Web API's Trading functionality is offered to our clients without any approval process, and the available features are determined primarily by the capabilities of a client's username and account(s).
> However, many Account Management features are only suitable for clients with certain institutional account structures, and the specifics of their usage will vary according to many factors, such as the Interactive Brokers business entity that carries the client's account structure, or the type of accounts within that structure.
> Consequently, the majority of the Web API's Account Management functionality is not immediately available for client use without a review and approval by Interactive Brokers. We encourage our institutional clients to contact their Sales Representative for an introduction to this process and the considerations involved.

- If you lose your Access Token and/or Access Token Secret, you can regenerate new ones, but you'll need to update your variables if you do as they will have changed. [One user](https://github.com/Voyz/ibind/issues/113) has reported that regenerating the access token works without any noticeable delay (with OAuth 1.0a access already set up, signing/encryption keys unchanged, consumer key unchanged).
- If you want to set up OAuth 1.0a for your paper account, simply login using your paper credentials when accessing the Client Portal. Then go through the entire process in the same way as you would for the live account. It is advised to not use the same private and public keys between live and paper accounts, but to generate them separately for each account.
- The OAuth 1.0a implementation is based on code provided directly by IBKR. This implementation relies on the pyCrypto library, which is no longer actively maintained and has known security vulnerabilities. While this approach ensures compatibility with IBKR’s OAuth process, it may pose security risks. Users should be aware that IBKR has not provided an official update or alternative implementation. We have notified IBKR of the issue and will reassess if they release a more secure version. Until then, users should exercise caution when using OAuth 1.0a authentication via IBind, as we do not guarantee the security of this implementation. If security is a primary concern, consider alternative authentication methods where possible.
- IBKR has advised some users to ensure they use the US IBKR domain when setting up OAuth: https://ndcdyn.interactivebrokers.com/sso/Login?action=OAUTH&RL=1&ip2loc=US. See [this comment](https://github.com/Voyz/ibind/issues/49#issuecomment-2768420813) for more.

### OAuth 1.0a on Individual Accounts

Despite the website and some IBKR support agents claiming otherwise, indeed  it seems to be possible to use OAuth 1.0a on individual accounts. Many individual account users reported successfully registering both live and paper credentials for OAuth 1.0a. This is what one API support agent said in this regard:

> I’m not aware of any technical limitations which would prevent an individual accountholder from accessing the OAuth 1.0a self-service portal (in either paper/live mode)

## <a name="acquiring_dh_prime"></a> Acquiring the DH Prime

To use OAuth 1.0a, you'll need to provide a DH Prime extracted from the `dhparam.pem` file generated in the previous section.

Run this Python script to extract the DH Prime:
```python
import subprocess
import re

result = subprocess.run(["openssl", "dhparam", "-in", "dhparam.pem", "-text"], capture_output=True, text=True).stdout
match = re.search(r"(?:prime|P):\s*((?:\s*[0-9a-fA-F:]+\s*)+)", result)
print(re.sub(r"[\s:]", "", match.group(1)) if match else "No prime (P) value found.")
```

The result should be a hex string similar to this one:
```
00f6220dbb372eb7b734ef426c3dc68014ad46d51b9423073f40a5dc747b0d12aac75490534b114186e8dc303c3ec392e4853e2c340131ba72082ecaaf6bf577778
1620a661e95768dfe3d86292408f5d8d3e1f3e90a8096d18e8b8c1c42e0c074bbff6b9c16983f60559927538be1cd668d79411111def4d2094754cbdc28b82270bf
f75fedd2ffcf3eef6538877393587112d33abc449bfb7d4be8effa4460baf65986adc30f3cf2c38e4f633a3052e209bd6eb7680734031a12a7c982efdb222ed001a
9bce460d1f3d32a845b70c3d383c7645a9962028585945f0a8baf0d2d544aafcc400461cc77ba67ccd2340c22adbcd4709b3b1d723b0fdd9539c95a83
```

If you're running into Error 403 when uploading the dhparam.pem, note that the file line endings may cause it. Users have reported that running this code on either Windows or Linux seems to have helped. See [this issue](https://github.com/Voyz/ibind/issues/97) for more.

## <a name="using_oauth1a_in_ibind"></a> Using OAuth 1.0a in IBind

OAuth 1.0a support is an optional extension of IBind. To use it, first install its additional dependencies by running:

```python
pip install ibind[oauth]
```

In order to use OAuth 1.0a you're required to provide a number of parameters in one of the two ways:

- As environment variables
- As constructor parameters of `IbkrClient` class

### Environment Variables

Set the following environment variables:

1. `IBIND_USE_OAUTH` set to `True`.
1. `IBIND_OAUTH1A_CONSUMER_KEY`: The consumer key configured during the onboarding process. This uniquely identifies the project in the IBKR ecosystem.
1. Private encryption and signature keys (note: private, not public):
    - `IBIND_OAUTH1A_ENCRYPTION_KEY_FP`: The path to the private OAuth encryption key.
    - `IBIND_OAUTH1A_SIGNATURE_KEY_FP`: The path to the private OAuth signature key.
1. Access tokens from the portal:
    - `IBIND_OAUTH1A_ACCESS_TOKEN`: OAuth access token generated in the self-service portal.
    - `IBIND_OAUTH1A_ACCESS_TOKEN_SECRET`: OAuth access token secret generated in the self-service portal.
1. The [DH Prime](#acquiring_dh_prime) extracted in previous section of this documentation
    - `IBIND_OAUTH1A_DH_PRIME`: The hex representation of the Diffie-Hellman prime.

`IbkrClient` will automatically read these when constructed, no other setup is necessary.

```python
client = IbkrClient() # initializes OAuth from environment variables
```

### Constructor Parameters

Alternatively, all OAuth parameters can be specified as parameters to `IbkrClient`, although cautions is advised in order to avoid exposing these credentials in your code base:

```python
client = IbkrClient(
    use_oauth=True,
    oauth_config=OAuth1aConfig(
        access_token='my_access_token',
        access_token_secret='my_access_token_secret',
        consumer_key='my_consumer_key',
        dh_prime='my_dh_prime',
        encryption_key_fp='my_encryption_key_fp',
        signature_key_fp='my_signature_key_fp',
    )
)
```

Any parameters not specified programmatically will be read from environment variables.

### Basic Usage

Once correctly set up, you can utilise the `IbkrClient` class normally to communicate with the IBKR REST API:

```python
portfolio_accounts = client.portfolio_accounts().data
```

See ["rest_08_oauth"][rest_08_oauth] for an example of how to use OAuth 1.0a with IBind.

----
#### Next

See [Advanced OAuth 1.0a][advanced-oauth1a] page to learn more about customising the OAuth 1.0a setup and how to use it with WebSockets.



[ibeam]: https://github.com/Voyz/ibeam
[ibkr-oauth1a]: https://www.interactivebrokers.com/campus/ibkr-api-page/cpapi-v1/#oauth-10a
[openssl]: https://openssl-library.org
[ibkr-oauth-setup]: https://ndcdyn.interactivebrokers.com/sso/Login?action=OAUTH&RL=1&ip2loc=US
[24-hrs]: https://github.com/Voyz/ibind/pull/34#issuecomment-2574569590
[advanced-oauth1a]: ./advanced_oauth_1a.md
[rest_08_oauth]: https://github.com/Voyz/ibind/blob/master/examples/rest_08_oauth.py
