# How to implement OAuth


Hello Hugh,

 

Thank you, let me share some details regarding 1st party OAuth1 key registration and implementation:

Link to the self-service portal: https://ndcdyn.interactivebrokers.com/sso/Login?action=OAUTH&RL=1&ip2loc=US

After login, follow the instructions provided in the self-service portal and generate your consumer key, signature key, encryption key and DH-params. You should get an access token + access token secret as a result, save them. Please note that consumer keys will only be activated after the server restart each weekend.

I have attached some materials for easier implementation:

-              How-to guide for OAuth implementation. (Although this can be confusing since it covers parts that do not concern 1st party OAuth workflow, it explains the relevant authentication steps accurately.)

-              First-party-oauth Python sample app. This has all the 1st party OAuth authentication steps implemented, you just need to follow the readme file inside and replace the consumer key, access token + secret, private signature and encryption keys, DH prime.

-              Oauth web demo JS app. You can test 1st party OAuth similar to the above from step 4 in the app. In order to make it work, remove .txt from the .js files in dist folder and run it in a browser with disabled security.

 


1. OAuth request basics:

    1.1 The authorization header:
    
       1.1a Realm
       
       1.1b oauth_callback
       
       1.1c oauth_nonce
       
       1.1d oauth_signature
       
       1.1e oauth_signature_method
       
       1.1f oauth_timestamp
       
       1.1g oauth_verifier
       
       1.1h oauth_token
       
       1.1i diffie_hellman_challenge
       
    1.2 The OAuth signature
    
       1.2a The base string
       
       1.2b The parameter list
       
       1.2c The prepend
       
       1.2d Generating the signature
       
2. OAuth Process

    2.1 Request Token
    
    2.2 /authorization step
    
    2.3 Access Token
    
    2.4 Live Session Token
    
       2.4a Diffie-Hellman Challenge
       
       2.4b Prepend
       
       2.4c The Response
       
       2.4d Calculation of the Live Session Token
       
       2.4e Verification of the Live Session Token
       
    2.5 Gaining Access to /iserver Endpoints
    
       2.5a SSODH Init Request

Example of OAuth Process
Registration
Obtaining Request Token
Obtaining Access Token
Obtaining Live Session Token
Calculating Live Session Token
SSODH Authorization
Accessing Protected GET Resources
Accessing Protected POST Resources

## 1. OAuth request basics:

## 1.1 The authorization header:

OAuth requests require a header with the name “Authorization”. The authorization header must start with the string “OAuth”. Following "OAuth", it has to
contain the following key/value pairs separated by comma:

```
realm
oauth_callback (only when getting request token)
oauth_consumer_key
oauth_nonce
oauth_signature
oauth_signature_method
oauth_timestamp
oauth_verifier (only when getting access token)
oauth_token (all requests except getting request token)
diffie_hellman_challenge (only when getting live session token)
```
All values should be percent-encoded. The code for building the authorization header in the demo can be found in src/mixins/mx-oauth.js. Search for "oauth.toHeader".

Authorization header examples:

Request token


```
authorization: OAuth realm="test_realm", oauth_callback="oob", oauth_consumer_key="TESTCONS", oauth_nonce="
3Xa0XhqFEoXbifYZUeflx6svQUDQsgB4", oauth_signature="KZohSaZYvwAKZr%2FKxlhYc145hV%2BNwok93%
2BSlbza47RdycKPSOCxL9J2zH8AuG69MCasG0qWy1fCS2BB1vRwt%2BxThOsQmECk%2B8UGjPJU9JEwy9PHMEfT%
2FJg7ieVIj8OrsAYhkGFDUlUfwn6Voh98MWqmZdcAFgv1RrfBFxGVvqBPKcC3sWw1SC7yEm9zNi%
2FNpUgUmpX4W0z74NBoBIKYZw33z5sCMDSE8Zkitw4GBtVh3IR43bO6vyWDXc0d7u%2FdcNEM2pI519kRPHmq%2FpsqgwUq6mt%
2BVN5QxncWvTXUwB0wM%2FkRvXqfrHUl6jcCmDic4e2c2awndoOLAK%2FJl6II3dA%3D%3D", oauth_signature_method="RSA-SHA256",
oauth_timestamp="1605211001"
```
Access token

```
authorization: OAuth realm="test_realm", oauth_consumer_key="TESTCONS", oauth_nonce="
B65wGkbQspBFN0lQjFZyIlr6ZA4T7iuw", oauth_signature="LhSvlaMU943AT2MO660T4f7SnbchCQkfJJTJ4S6PVsG%
2FMtWp3o5kAksxxgIF6MA9ZPEZ34vMac52P5Yg0dMBgnZKYeJKWM1Cfo3G%2FzJTWQ4vo%
2FOOeS3Zvvpt057YbT6NdRSRbylxW7s0aEMWo518BaFUwUzhLT%2FUjyJVXwdu9q6sNc0gcEbEUPgRVKi3YLd%2FBn%
2FySG7cMWeEnuHVgzoBKaeVKO6MiiUl8e6WOlWPB5eiOQ0ny%
2BoTGIhVPoQhfdCW91GqP6ZxwEJTp4hwFy8skpv9D3KLB7nHEDYZDzNsxReBBHH339JPtEvQgCV9qW2TZ1FRb%2FEeBeGd1uW1gpdXkg%3D%
3D", oauth_signature_method="RSA-SHA256", oauth_timestamp="1605211316", oauth_token="98cb431e61ae03817f6a",
oauth_verifier="4e253ee389df74010b6b"
```
Live session token

```
authorization: OAuth realm="test_realm", diffie_hellman_challenge="
76ebad1411bb88283c3195498402ac238459ecfef83ab11c466a04e6cf7fb93c77a35e63f25055eae1720e702a0c218286d8dd00f04ae
e42da57daa7f3a3d1560d2eada9cbb5b3d6f4e76d4d651c86bec396afeabdcb34fcc676bdcff017fa3ee5712198725b86a1a72e854d5da
f8fc7f60801cecc6eeaa4892fae21effec8dc7d0514d0b7667d5c33ba32c502a908ddb7518a80f7221f76bde8b6e182d42c6ee30f925cdc
e752c5907e0e9d3eeffc2e0ab314acb721fd83c45ca7ceba01e98c8e14623aeb19cad5a20093d937f29609f3336fa8214ba997f41c7943c
a611d56128423229af7f01f8a21c6c9953c52f15c99d61cc472f05c4caf76183", oauth_consumer_key="TESTCONS", oauth_nonce="
Hqx0Q3UxBdyEvo4I71bmAZ1lIj7LRRz7", oauth_signature="OXOscqVhUah5crXc%
2FK6ZrYAjLtSJFwgKvIGXgnpWskOWTEiAoNRYmj4INwz6%2FeSxKd7OJAyotSymNlirwqumcI8ee95Dsy1gsYeX084Ty9L3uZO8fsGzuFam2N%
2FTUF%2BUJDhZP%2BYJxzMzFlBoAaS%2BeQyNRh7LHMITTIWh0%2Fga%2FFUmHT0dTGeEcx%2F%2F6ee8pqgEsyrA1%
2BJoKFS91GgQ5Xt8MXW2S8OLluFFTrwhUWFPBp4NCGNa1arWHXulJF%2FjhwY9SU5OUJYgxtzvIkaJO9rSxZ5z34GOvGs%
2FzNszfPz09k2n9keTznP%2B2bgfyfpfecRBjz8dMylbiAVThbt1F%2BFpGg%3D%3D", oauth_signature_method="RSA-SHA256",
oauth_timestamp="1605211318", oauth_token="eb31c080cc0bd45b2f55"
```
Protected resources

```
authorization: OAuth realm="test_realm", oauth_consumer_key="TESTCONS", oauth_nonce="
1q8YmKU101RVyGwUBrq1CkJdcybucp23", oauth_signature="AwqwlUGJcIAV0yEAt7jjUTrNhoTQ39YdOEY%2BbGw8R%2Fw%3D",
oauth_signature_method="HMAC-SHA256", oauth_timestamp="1605211498", oauth_token="eb31c080cc0bd45b2f55"
```
##### **1.1a Realm**

The realm is generally set to "limited_poa", or "test_realm" when testing OAuth using the TESTCONS consumer key.

##### **1.1b oauth_callback**

This is only required when getting a request token, and should just be set to "oob"

##### **1.1c oauth_nonce**

The nonce needs to be a randomly generated, unique value. Each oauth request needs to have a different and unique nonce.

An example of how to generate a nonce is here: https://github.com/ddo/oauth-1.0a/blob/master/oauth-1.0a.js
Refer to the getNonce() method, found by searching for "OAuth.prototype.getNonce = function() {"

##### **1.1d oauth_signature**

The signature is the base string signed using a private signing key or live session token. More details about this value can be found in section 1.2.

##### **1.1e oauth_signature_method**

The method which we sign the base string. It is "RSA-SHA256" for the steps leading up to and including getting the live session token, and "HMAC-
SHA256" when accessing protected resources.

##### **1.1f oauth_timestamp**


The timestamp in milliseconds of when the request is made

##### **1.1g oauth_verifier**

After logging in with a user during the /authorize step, you will be redirected to a page with the verifier token in the URL as a query parameter. The
oauth_verifier value is the verifier token. This is only used for getting the access token and not required for any other request.

##### **1.1h oauth_token**

When getting the access token, this value is the same as the request token value. For all other requests (except request token requests where this is not
required) this value is the access token.

##### **1.1i diffie_hellman_challenge**

This value is only required for the live session token step. Explanation on how to get it is below

#### **1.2 The OAuth signature**

The signature is acquired by signing the base string of the OAuth request using your private signing key and the OAuth signature method.

##### **1.2a The base string**

The base string is a string generated based on the parameters of the OAuth request. The method the demo uses to build the base string can be found
here: https://github.com/ddo/oauth-1.0a/blob/master/oauth-1.0a.js. Search for "OAuth.prototype.getBaseString = function(request, oauth_data) {".

The base string is in the following format:

###### [HTTP_METHOD]&[BASE_URL]&[PARAMETER_LIST]

There is a special case where there is a prepend string added to the front of the base string, only for live session token requests. In this case, the base
string would be:

###### [PREPEND][HTTP_METHOD]&[BASE_URL]&[PARAMETER_LIST]

[HTTP_METHOD] = the HTTP method, such as GET, POST, DELETE etc.

[BASE_URL] = The percent encoded URL of the request, without any query parameters

[PARAMETER_LIST] = A lexicographically sorted list of key/value pairs including the authorization header pairs, query parameters and if the request
contains a body of type x-www-form-urlencoded, the body parameters. The list values are separated using the character '&', then the list is percent
encoded. See section 1.2b.

[PREPEND] = A string needed to be included at the front of the base string. Unlike other parts of the base string, this value is not separated by &

Base string examples :

Normal base string

```
POST&https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Foauth%2Fsession_token&device_id%3DCCCCCC95%7C48-DF-37-57-33-80%
26oauth_consumer_key%3DTESTCONS%26oauth_nonce%3DmQfUqcZD3TjC5RNguaYVQwOXfFyCgt0m%26oauth_signature_method%3DRSA-
SHA256%26oauth_timestamp%3D1605211475%26oauth_token%3Deb31c080cc0bd45b2f55%26username%3D
```
```
[HTTP_METHOD] = POST
[BASE_URL] = https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Foauth%2Fsession_token
[PARAMETER_LIST] = device_id%3DCCCCCC95%7C48-DF-37-57-33-80%26oauth_consumer_key%3DTESTCONS%26oauth_nonce%
3DmQfUqcZD3TjC5RNguaYVQwOXfFyCgt0m%26oauth_signature_method%3DRSA-SHA256%26oauth_timestamp%3D1605211475%
26oauth_token%3Deb31c080cc0bd45b2f55%26username%3D
```
Live session token base string


```
901c5e47fc1abec4ae9b4747024ff4d3ba186f16522eaf823238f4cadbef9cdcPOST&https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%
2Foauth%2Flive_session_token&device_id%3DCCCCCC95%7C48-DF-37-57-33-80%26diffie_hellman_challenge%
3D76ebad1411bb88283c3195498402ac238459ecfef83ab11c466a04e6cf7fb93c77a35e63f25055eae1720e702a0c218286d8dd00f04ae
40e42da57daa7f3a3d1560d2eada9cbb5b3d6f4e76d4d651c86bec396afeabdcb34fcc676bdcff017fa3ee5712198725b86a1a72e854d5da
17f8fc7f60801cecc6eeaa4892fae21effec8dc7d0514d0b7667d5c33ba32c502a908ddb7518a80f7221f76bde8b6e182d42c6ee30f925cd
c4e752c5907e0e9d3eeffc2e0ab314acb721fd83c45ca7ceba01e98c8e14623aeb19cad5a20093d937f29609f3336fa8214ba997f41c
c3a611d56128423229af7f01f8a21c6c9953c52f15c99d61cc472f05c4caf76183%26oauth_consumer_key%3DTESTCONS%
26oauth_nonce%3DHqx0Q3UxBdyEvo4I71bmAZ1lIj7LRRz7%26oauth_signature_method%3DRSA-SHA256%26oauth_timestamp%
3D1605211318%26oauth_token%3Deb31c080cc0bd45b2f
```
```
[PREPEND] = 901c5e47fc1abec4ae9b4747024ff4d3ba186f16522eaf823238f4cadbef9cdc
[HTTP_METHOD] = POST
[BASE_URL] = https%3A%2F%2Fapi.ibkr.com%2Fv1%2Fapi%2Foauth%2Flive_session_token
[PARAMETER_LIST] = device_id%3DCCCCCC95%7C48-DF-37-57-33-80%26diffie_hellman_challenge%
3D76ebad1411bb88283c3195498402ac238459ecfef83ab11c466a04e6cf7fb93c77a35e63f25055eae1720e702a0c218286d8dd00f04ae
40e42da57daa7f3a3d1560d2eada9cbb5b3d6f4e76d4d651c86bec396afeabdcb34fcc676bdcff017fa3ee5712198725b86a1a72e854d5da
17f8fc7f60801cecc6eeaa4892fae21effec8dc7d0514d0b7667d5c33ba32c502a908ddb7518a80f7221f76bde8b6e182d42c6ee30f925cd
c4e752c5907e0e9d3eeffc2e0ab314acb721fd83c45ca7ceba01e98c8e14623aeb19cad5a20093d937f29609f3336fa8214ba997f41c
c3a611d56128423229af7f01f8a21c6c9953c52f15c99d61cc472f05c4caf76183%26oauth_consumer_key%3DTESTCONS%
26oauth_nonce%3DHqx0Q3UxBdyEvo4I71bmAZ1lIj7LRRz7%26oauth_signature_method%3DRSA-SHA256%26oauth_timestamp%
3D1605211318%26oauth_token%3Deb31c080cc0bd45b2f
```
##### **1.2b The parameter list**

The parameter list is a list of leixcographically sorted parameters in the following format:

key=value&key=value&key=value

The list is then url encoded, so it would look something like this:

key%3Dvalue%26key%3Dvalue%26key%3Dvalue

The method the demo uses to build the parameter list can be found here: https://github.com/ddo/oauth-1.0a/blob/master/oauth-1.0a.js. Search for "OAuth.p
rototype.getParameterString = function(request, oauth_data) {"

Parameters consist of the following:

They key/value pairs in the authorization header, such as oauth_signature_method, oauth_nonce, but NOT the oauth_signature

Any key/value pairs in the body of the request if the content-type of the request is x-www-urlencoded (so the body is excluded if it is of type JSON)

##### **1.2c The prepend**

When we successfully request an access token, we are given an oauth_token_secret in the response. This secret must be decrypted using your private
encryption key, and then converted to a hex value. The hex value of the decrypted secret is the prepend string we add in front of the base string when
requesting a live session token.'

##### **1.2d Generating the signature**

Once the base string has been successfully created, it must then be signed. When getting the request, access or live session token, the key used for
signing is the private signing key, and the signature method is RSA-SHA256.

When accessing any other endpoint, which means any protected resource, the key used is the live session token as a byte array and the signature
method is HMAC-SHA256.

The signature method the demo uses can be found in src/mixins/mx-oauth.js. Search for "oauth.getSignature".

### 2. OAuth Process

#### 2.1 Request Token

To start the OAuth process, we must first get a request token.

To get a request token, an OAuth request to https://api.ibkr.com/v1/api/oauth/request_token must be made.

The request should be a POST request but with no body. Remember that an authorization header we mentioned in 1.1 has to be added. Refer to the
example there.


This step is a good indicator of whether or not something is wrong with your OAuth request. If you are missing any portion of the authorization header, the
response will tell you so. If something is wrong with either the base string or signature creation, then you will be met with a 401 response.

The method for getting the request token in the demo can be found in src/ib/ib-oauth-settings.vue. Search for "sessionTokenRequest: function".

#### 2.2 /authorization step

After getting the request token, you must then redirect the user to https://www.interactivebrokers.com/authorize?oauth_token=REQUEST_TOKEN

Replace REQUEST_TOKEN with the request token you generated

After the user logs in, they will be redirected to a URL specified during consumer key creation, and there will be two query parameters in the URL:
oauth_token and oauth_verifier

oauth_token is the request token, and oauth_verifier is the verifier token required for the next step.

e.g.

```
http://localhost:20000/?oauth_token=dc75fcf43e3752c1a1ce&oauth_verifier=f11e2c5d9b6d0624e
```
#### 2.3 Access Token

A POST OAuth request to https://api.ibkr.com/v1/api/oauth/access_token must now be made.

This time, oauth_verifier must be added to the authorization header, with the value being the verifier token retrieved from the previous step.

oauth_token must also be added to the authorization header, the value being the request token from step 2.1.

If the request succeeds, the response will contain two values: oauth_token and oauth_token_secret.

The oauth_token in the response is the access token, and the oauth_token_secret will be used for the next step.

The method for getting the access token in the demo can be found in src/ib/ib-oauth-settings.vue. Search for "accessTokenRequest: function".

#### 2.4 Live Session Token

The final step in the OAuth authorization process is the live session token. A POST OAuth request to https://api.ibkr.com/v1/api/oauth/live_session_token
must be made. 

If you are an IB customer who registered using the Self-Service OAuth page then on that same page you should have completed step 2.3 Access Token. You would now proceed to this final step to complete the OAuth authorization process.

In this step we must calculate a Diffie-Hellman challenge using the prime and generator in the Diffie-Hellman spec provided when registering your
consumer key.

The method for getting the live session token in the demo can be found in src/ib/ib-oauth-settings.vue. Search for "liveSessionTokenRequest: function".

##### **2.4a Diffie-Hellman Challenge**

To calculate the Diffie-Hellman challenge, we must use the following formula

A is the Diffie-Hellman challenge

g is the Diffie-Hellman generator

p is the Diffie-Hellman prime

a is the Diffie-Hellman random value, randomly generated

The calculation can be see in the liveSessionTokenRequest mentioned above.

##### **2.4b Prepend**

For live session token requests, we have to add a prepend to the base string (1.2c).

The prepend in this case is the decrypted oauth_token_secret received from the access token step (2.3).

oauth_token_secret needs to be decrypted using your private encryption key with scheme pkcs1. The result needs to be recorded as a hex value.

The prepend is therefore the hex value of oauth_token_secret decrypted.

Demo code:

```
var prepend = key.decrypt(this.oauth.tokenSecret, 'hex');
```
##### **2.4c The Response**

If the live session token request is successful, the response will contain a value "diffie_hellman"response". This diffie_hellman_response is used to
calculate the live session token. diffie_hellman_response will be in hex form.

##### **2.4d Calculation of the Live Session Token**

To calculate a live session token, we must first calculate to value of K.

B is the diffie_hellman_response

a is the Diffie-Hellman random value from step 2.4a

p is the Diffie-Hellman prime

To calculate the live session token, we must use K as the key to signing oauth_token_secret (as a byte array) from the access token response. The
method of signing is HMAC-SHA1. The result is the live session token.

Remember that when using the live session token to sign requests, it must be a byte array.

The method for LST calculation in the demo can b efound in src/oauth.functions.js. Search for "calculateLST".

IMPORTANT NOTE:

When K is a byte array, it MUST have a leading zero bit denoting the sign. This is because Java's BigInteger's toByteArray() method always includes a
sign bit. In our case, the sign bit will always be 0 because the value of K is always positive.

If your conversion of K to a byte array does not include this sign bit, please make sure to add it before using K to calculate the live session
token. Otherwise, it will be wrong. So if you are using any sort of library that includes this function, such as Java's BigInteger, then you don't need to
worry about this.

An easy way to ensure your K byte array includes a sign bit, convert K to bits. If there is no remainder after dividing the length of bits by 8, then you need
to manually add a 0 byte at the beginning of the K byte array.
This is because when the number of bits is divisible by 8, then adding an extra sign bit would result in one extra byte in the array.

Example 1:

```
K = 0xff
K in bytes = [255]
K in bits = 11111111
K in bits length = 8
8 % 8 = 0
Append 0 to head of byte array
Result K byte array = [0, 255]
```
Example 2


```
K = 0x7f
K in bytes = [127]
K in bits = 1111111
K in bits length = 7
7 % 8 = 7
Don't do anything special
Result K byte array = [127]
```
##### **2.4e Verification of the Live Session Token**

In the live session token response, there is a value called "live_session_token_signature". The purpose of this is to verify whether or not the live session
token you calculated was correct.

To verify, create an HMAC-SHA1 hash of your consumer key in bytes, with the live session token you calculated in bytes as the signing key. Then convert
the result to hex format. If hex result is the same as live_session_token_signature, the live session token you calculated is correct.

The method for verification can be found in src/oauth.functions.js. Search for "verifyLST".

Now that you have a live session token, non-brokerage endpoints (non-/iserver endpoints) are now accessible. To access brokerage endpoints, continue:

#### 2.5 Gaining Access to /iserver Endpoints

If a session token was successfully published, there is one last step before /iserver endpoints can be accessed.

##### **2.5a SSODH Init Request**

An OAuth protected-resource POST request must be made to https://api.ibkr.com/v1/api/iserver/auth/ssodh/init

There are two required parameters:

```
compete (Boolean)
publish (Boolean)
```

compete is whether or not the session should compete, usually set to false, but can be set to true if you want to disconnect other sessions.

publish must be set to true.

The parameters can be sent as request parameters or in the POST body of type JSON.

If the request is successful, the response will contain a JSON object telling you if you are authenticated and connected.

### Using Websocket

The websocket end point is available at: wss://api.ibkr.com/v1/api/ws 

Some services require the client to establish a brokerage session first, for example account and order updates.

There are two ways of authorizing yourself with the websocket connection. 

The first is to include the cookies from the "set-cookie" headers from previous requests.  Most browsers will automatically do this for you, although there are some exception such as Chrome.

The second is to send the "session" value obtained via the /tickle endpoint.  Once a websocket without the proper cookies is opened, the websocket will reply with a message saying "waiting for session".  This indicates it is waiting for you to send the session value.

The session value should be sent as a JSON object, with one key/pair as follows:

```
{"session":"SESSION_VALUE_HERE"}
```

With SESSION_VALUE_HERE replaced with the actual session.

If the session is valid, the websocket will send a response confirming that you are authenticated.

e.g.

Open websocket

Receive response:

```
{"message":"waiting for session"}
```

Access https://api.ibkr.com/v1/api/tickle

Receive response: 

```
{
  "session": "aeccc9d7515398c50fa894d967d099b1",
  "iserver": {
    "tickle": true,
    "authStatus": {
      "authenticated": true,
      "competing": false,
      "connected": true,
      "message": "",
      "MAC": "98:F2:B3:23:CF:10"
    }
  }
}
```

Send following message to websocket:

```
{"session":"aeccc9d7515398c50fa894d967d099b1"}
```

Receive response:

```
{"topic":"sts","args":{"authenticated":true}}
{"topic":"system","success":"username"}
```

## Example of OAuth Process

### Registration

Consumer registers with IBKR, provides two 2048-bit RSA public keys, a signature method, and a Diffie-Hellman prime and group. They specify RSA-
SHA256 as the encryption method and supplies https://www.example.com/callback as the callback. They are then issued with a consumer key:

consumer_key=TESTCONS

### Obtaining Request Token

Consumer sends the following POST to /oauth/request_token


```
POST /oauth/request_token HTTP/1.
Authorization: OAuth oauth_callback="oob", \
oauth_consumer_key="TESTCONS", \
oauth_nonce="abcdefg", \
oauth_signature="nHp...AA%3D%3D", \
oauth_signature_method="RSA-SHA256", \
ouath_timestamp="1473793701", \
realm="test_realm"
Content-Length: 0
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encodig: gzip,deflate
```
The Consumer receives the following response

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-
Content-Length: 38
x-response-time: 79ms
{"oauth_token":"25ebcc75204da80b73f4"}
```
### Obtaining Access Token

Consumer sends the following POST to /oauth/access_token

```
POST /oauth/access_token HTTP/1.
Authorization: OAuth oauth_consumer_key="TESTCONS", \
oauth_nonce="zsxdefg", \
oauth_signature="Yb01...rWBA%3D%3D", \
oauth_signature_method="RSA-SHA256", \
ouath_timestamp="1473793702", \
oauth_token="25ebcc75204da80b73f4", \
oauth_verifier="61c107d4cf34ac6d9f2b"
Content-Length: 0
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encodig: gzip,deflate
```
The Consumer receives the following response

```
 HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-
Content-Length: 38
x-response-time: 79ms
{"is_paper":true,\
"oauth_token":"6f531f8fd316915af53f",\
"oauth_token_secret":"MtUT...GJA=="}
```
### Obtaining Live Session Token

The Consumer chooses an integer

a = 1435329019564828319111943272230435123117133842132517761382825

and computes which is


adcc3e6d1a297418336fd90f41f0b1a1d9b025b35725f6803d6b13309bc3d0fcfdaeff17306bcafa5d
0e91a66ad540254cacae28550e30145df9d7a3847bb7774b6c53a6f1e5c1aaed51fffb17807c8e
d93ede25801b41a83dd9fcce5b3f8cff4200dff23ebf907c6eab820a35fc32133eb09c653d7ceebbad
f14715a3c191a37a442d1063232ddbc7fbc1be855d62b7383e134175e33c19b9118d6e3213e
87319b39960efc5eb7e9f0e891d3bc71fd7e0f13f0330c0edf8f67007e5bf327219569298bea3ebde
c772c2b9461f484ed956e888c7c545f11a05c02812ef07ea026d0bd69a0b2fe60d7c106e059515a
780ebd1143b0765bebb

The Consumer sends the following POST to /oauth/live_session_token

```
POST /oauth/access_token HTTP/1.
Authorization: OAuth diffie-hellman_challenge="adcc...bebb", \
oauth_consumer_key="TESTCONS", \
oauth_nonce="12xdzfg", \
oauth_signature="KzaCo...eBUw%3D%3D", \
oauth_signature_method="RSA-SHA256", \
ouath_timestamp="1473793703", \
oauth_token="6f531f8fd316915af53f"
Content-Length: 0
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encodig: gzip,deflate
```
The Consumer receives the following response

###### HTTP/1.1 200 OK

```
Content-Type: application/json; charset=utf-
Content-Length: 38
x-response-time: 79ms
```
```
{"diffie_hellman_response":"51...0e", "live_session_token_signature":"54...f4"}
```
The full Diffie-Hellman response is:

51a8175da12f6952e935756321e0d3589cbd7c2535413deafe67ea4395da94af3ac589ec99d0680cbf
29f475c56450fd66bc403080bedc8be1805408e461acd6ae0f00fbb3ee8e81927448edff8b011af0f
2eeefb4d2bc1ae8099d1e62cb9d2963e84195c8dce1e43d0694d32be7651f108d9b973439da6690b8f
9409ffcba6f5e588e05611d161edb09464babd10fa84310d62551775745cacb5bb5071f179181eda
aea6de7bdba997ed8820a52cf7c84d41605895bdddb44972f06726866cd30472a8f53c1d50ba4d92c
9737a1f54ffba404b389ee8c14ed10821403476584137811acbfca733147db6b776af4261af7cf9ff
224a3043ec705af760e

And the full live session token signature is

543c55477d6cbb0e792d1e4f8111cec7305ba3f

#### Calculating Live Session Token

First we need to calculate K

Using the Diffie-Hellman response as B, we get

K= 6262468731191716683916525460981637432269697150114366475089957235034556054645865209
7727466193918128491278351377747537675165331206606577881303560193892583906396297713
0285681861128917558036055166314200723585833452614598893039983793075173417203185616
8887029288967531594210251515114214270648331076558038219524053473452048253881320127
1884787556741085253161782311759691397680487566604132871880546809466098442097571479
8594795590947008746401693222302341952432123212575873140979848617085540126903548680
6152769695999321982943785989707170257093535822989962797048573685671123477713856278
66241600484929153836364971579931995994781

Now to calculate the live session token

Live session token = HMAC_SHA1(K, access_token_secret)

We get

YBWbLw+9RYP2nWrPQHxHZkBb1aM=

### SSODH Authorization

The Consumer sends the following POST to /iserver/auth/ssodh/init

```
POST /iserver/auth/ssodh/init HTTP/1.
Authorization: OAuth realm="test_realm", \
oauth_consumer_key="TESTCONS", \
oauth_nonce="SIbRp1GZMR8DBurG48iPSezBa2QGtAKy", \
oauth_signature="EjfgOZpz7C08tlAO3Xfs%2Blch%2BToU9LGa4INY0V3%2Fh%2Fo%3D", \
oauth_signature_method="HMAC-SHA256", \
oauth_timestamp="1605648453", \
oauth_token="6f531f8fd316915af53f"
Content-Length: 78
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encoding: gzip,deflate
```
```
compete=false&publish=true
```
### Accessing Protected GET Resources

The Consumer sends the following GET to /marketdata/snapshot to get some data about a specific security (IBM stock in this example)


```
GET /marketdata/snapshot?conid=8314 HTTP/1.
Authorization: OAuth realm="test_realm", \
oauth_consumer_key="TESTCONS", \
oauth_nonce="sdgdzfg", \
oauth_signature="+BdI...v8%3D", \
oauth_signature_method="HMAC-SHA256", \
ouath_timestamp="1473793704", \
oauth_token="6f531f8fd316915af53f"
Content-Length: 0
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encoding: gzip,deflate
```
The signature is calculated as

HMAC_SHA256(live session token, signature base string)

The Consumer receives the following response

```
 HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-
Content-Length: 146
x-response-time: 79ms
{"Closing":{"price":158.29},"Trade":{"price":155.76,"size":1,"time":1473795686},\
"Bid":{"price":155.74,"size":2},"Offer":{"price":155.76,"size":5}}
```
### Accessing Protected POST Resources

The Consumer sends the following POST to /accounts/:accountid/order_impact where :accountid is the account id of the user

```
POST /accounts/DU216409/order-impact HTTP/1.
Authorization: OAuth realm="test_realm", \
oauth_consumer_key="TESTCONS", \
oauth_nonce="123456g", \
oauth_signature="PsR...us%3D", \
oauth_signature_method="HMAC-SHA256", \
ouath_timestamp="1473793705", \
oauth_token="6f531f8fd316915af53f"
Content-Length: 115
Host: localhost:
Connection: Keep-Alive
User-Agent: Apache-HttpClient/4.5.1 (Java/1.8.0_102)
Accept-Encodig: gzip,deflate
```
```
CustomerOrderId=ibm1&ContractId=8314&Exchange=SMART&\
Quantity=100&Price=100&OrderType=Limit&TimeInForce=DAY&Side=BUY
```
The Consumer receives the following response

```
HTTP/1.1 200 OK

Content-Type: application/json; charset=utf-
Content-Length: 259
x-response-time: 79ms

{"EquityWithLoan":9899985.0,\
"EquityWithLoanBefore":9899985.0,\
"InitMargin":14504.36,\
"InitMarginBefore":10578.76,\
"MaintMargin":14504.36,\
"MaintMarginBefore":10578.76,\
"MarginCurrency":"USD",\
"MinCommissions":1.0,\
"MaxCommissions":2.35,\
"CommissionsCurrency":"USD"}
```

