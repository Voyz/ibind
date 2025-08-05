using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace IBind.OAuth;

public record OAuth1aConfig : OAuthConfig
{
    public override string Version => "1.0a";

    public string OAuthRestUrl { get; init; } = Config.OAuth1aRestUrl;
    public string LiveSessionTokenEndpoint { get; init; } = Config.OAuth1aLiveSessionTokenEndpoint;
    public string? AccessToken { get; init; } = Config.OAuth1aAccessToken;
    public string? AccessTokenSecret { get; init; } = Config.OAuth1aAccessTokenSecret;
    public string? ConsumerKey { get; init; } = Config.OAuth1aConsumerKey;
    public string? DhPrime { get; init; } = Config.OAuth1aDhPrime;
    public string? EncryptionKeyFp { get; init; } = Config.OAuth1aEncryptionKeyFp;
    public string? SignatureKeyFp { get; init; } = Config.OAuth1aSignatureKeyFp;
    public int DhGenerator { get; init; } = Config.OAuth1aDhGenerator;
    public string Realm { get; init; } = Config.OAuth1aRealm;

    public override void VerifyConfig()
    {
        var required = new Dictionary<string, string?>
        {
            [nameof(OAuthRestUrl)] = OAuthRestUrl,
            [nameof(LiveSessionTokenEndpoint)] = LiveSessionTokenEndpoint,
            [nameof(AccessToken)] = AccessToken,
            [nameof(AccessTokenSecret)] = AccessTokenSecret,
            [nameof(ConsumerKey)] = ConsumerKey,
            [nameof(DhPrime)] = DhPrime,
            [nameof(EncryptionKeyFp)] = EncryptionKeyFp,
            [nameof(SignatureKeyFp)] = SignatureKeyFp,
        };
        var missing = new List<string>();
        foreach (var (key, value) in required)
        {
            if (string.IsNullOrWhiteSpace(value))
                missing.Add(key);
        }
        if (missing.Count > 0)
            throw new ArgumentException($"OAuth1aConfig is missing required parameters: {string.Join(", ", missing)}");

        var missingFiles = new List<string>();
        if (!File.Exists(EncryptionKeyFp!))
            missingFiles.Add(nameof(EncryptionKeyFp));
        if (!File.Exists(SignatureKeyFp!))
            missingFiles.Add(nameof(SignatureKeyFp));
        if (missingFiles.Count > 0)
            throw new ArgumentException($"OAuth1aConfig's filepaths don't exist: {string.Join(", ", missingFiles)}");
    }
}

public class OAuth1aClient
{
    private readonly HttpClient _httpClient;
    private readonly OAuth1aConfig _config;

    public OAuth1aClient(HttpClient httpClient, OAuth1aConfig config)
    {
        _httpClient = httpClient;
        _config = config;
    }

    public async Task<(string LiveSessionToken, long Expiration, string Signature)> RequestLiveSessionTokenAsync()
    {
        var (prepend, extraHeaders, dhRandom) = PrepareOAuth(_config);
        var url = new Uri(new Uri(_config.OAuthRestUrl), _config.LiveSessionTokenEndpoint).ToString();
        var headers = GenerateOAuthHeaders(_config, HttpMethod.Post, url,
            extraHeaders: extraHeaders, signatureMethod: "RSA-SHA256", prepend: prepend);
        var request = new HttpRequestMessage(HttpMethod.Post, url);
        foreach (var kv in headers)
            request.Headers.TryAddWithoutValidation(kv.Key, kv.Value);
        var response = await _httpClient.SendAsync(request);
        response.EnsureSuccessStatusCode();
        using var stream = await response.Content.ReadAsStreamAsync();
        using var doc = await JsonDocument.ParseAsync(stream);
        var root = doc.RootElement;
        var lstExpires = root.GetProperty("live_session_token_expiration").GetInt64();
        var dhResponse = root.GetProperty("diffie_hellman_response").GetString()!;
        var lstSignature = root.GetProperty("live_session_token_signature").GetString()!;
        var lst = CalculateLiveSessionToken(_config.DhPrime!, dhRandom, dhResponse, prepend);
        return (lst, lstExpires, lstSignature);
    }

    public static Dictionary<string, string> GenerateOAuthHeaders(
        OAuth1aConfig config,
        HttpMethod requestMethod,
        string requestUrl,
        string? liveSessionToken = null,
        IDictionary<string, string>? extraHeaders = null,
        IDictionary<string, string>? requestParams = null,
        string signatureMethod = "HMAC-SHA256",
        string? prepend = null)
    {
        var headers = new Dictionary<string, string>
        {
            ["oauth_consumer_key"] = config.ConsumerKey!,
            ["oauth_nonce"] = GenerateOAuthNonce(),
            ["oauth_signature_method"] = signatureMethod,
            ["oauth_timestamp"] = GenerateRequestTimestamp(),
            ["oauth_token"] = config.AccessToken!,
        };
        if (extraHeaders != null)
        {
            foreach (var kv in extraHeaders)
                headers[kv.Key] = kv.Value;
        }
        var baseString = GenerateBaseString(
            requestMethod.Method.ToUpperInvariant(),
            requestUrl,
            headers,
            requestParams,
            prepend: prepend);
        string signature = signatureMethod == "HMAC-SHA256"
            ? GenerateHmacSha256Signature(baseString, liveSessionToken ?? string.Empty)
            : GenerateRsaSha256Signature(baseString, ReadPrivateKey(config.SignatureKeyFp!));
        headers["oauth_signature"] = signature;
        var headerString = GenerateAuthorizationHeaderString(headers, config.Realm);
        return new Dictionary<string, string>
        {
            ["Accept"] = "*/*",
            ["Accept-Encoding"] = "gzip,deflate",
            ["Authorization"] = headerString,
            ["Connection"] = "keep-alive",
            ["Host"] = "api.ibkr.com",
            ["User-Agent"] = "ibind",
        };
    }

    private static (string Prepend, Dictionary<string, string> ExtraHeaders, string DhRandom) PrepareOAuth(OAuth1aConfig config)
    {
        var dhRandom = GenerateDhRandomBytes();
        var dhChallenge = GenerateDhChallenge(config.DhPrime!, dhRandom, config.DhGenerator);
        var prepend = CalculateLiveSessionTokenPrepend(config.AccessTokenSecret!, ReadPrivateKey(config.EncryptionKeyFp!));
        var extra = new Dictionary<string, string> { ["diffie_hellman_challenge"] = dhChallenge };
        return (prepend, extra, dhRandom);
    }

    public static string GenerateRequestTimestamp()
        => DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString();

    private static RSA ReadPrivateKey(string path)
    {
        var pem = File.ReadAllText(path);
        var rsa = RSA.Create();
        rsa.ImportFromPem(pem);
        return rsa;
    }

    public static string GenerateOAuthNonce()
    {
        const int length = 16;
        const string chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        var bytes = new byte[length];
        RandomNumberGenerator.Fill(bytes);
        var charsArr = new char[length];
        for (int i = 0; i < length; i++)
            charsArr[i] = chars[bytes[i] % chars.Length];
        return new string(charsArr);
    }

    private static string Quote(string value)
        => Uri.EscapeDataString(value).Replace("%20", "+");

    public static string GenerateBaseString(
        string requestMethod,
        string requestUrl,
        IDictionary<string, string> requestHeaders,
        IDictionary<string, string>? requestParams = null,
        IDictionary<string, string>? requestFormData = null,
        IDictionary<string, string>? requestBody = null,
        IDictionary<string, string>? extraHeaders = null,
        string? prepend = null)
    {
        var all = new SortedDictionary<string, string>(StringComparer.Ordinal);
        foreach (var kv in requestHeaders) all[kv.Key] = kv.Value;
        if (requestParams != null)
            foreach (var kv in requestParams) all[kv.Key] = kv.Value;
        if (requestFormData != null)
            foreach (var kv in requestFormData) all[kv.Key] = kv.Value;
        if (requestBody != null)
            foreach (var kv in requestBody) all[kv.Key] = kv.Value;
        if (extraHeaders != null)
            foreach (var kv in extraHeaders) all[kv.Key] = kv.Value;
        var paramString = string.Join("&", all.Select(kv => $"{kv.Key}={kv.Value}"));
        var encodedUrl = Quote(requestUrl);
        var encodedParams = Quote(paramString);
        var baseString = string.Join("&", new[] { requestMethod, encodedUrl, encodedParams });
        if (!string.IsNullOrEmpty(prepend))
            baseString = prepend + baseString;
        return baseString;
    }

    public static string GenerateDhRandomBytes()
    {
        Span<byte> bytes = stackalloc byte[32];
        RandomNumberGenerator.Fill(bytes);
        return Convert.ToHexString(bytes).ToLowerInvariant();
    }

    public static string GenerateDhChallenge(string dhPrime, string dhRandom, int dhGenerator = 2)
    {
        var prime = BigInteger.Parse("0" + dhPrime, NumberStyles.HexNumber);
        var random = BigInteger.Parse("0" + dhRandom, NumberStyles.HexNumber);
        var challenge = BigInteger.ModPow(new BigInteger(dhGenerator), random, prime);
        return challenge.ToString("x");
    }

    public static string CalculateLiveSessionTokenPrepend(string accessTokenSecret, RSA privateKey)
    {
        var secretBytes = Convert.FromBase64String(accessTokenSecret);
        var decrypted = privateKey.Decrypt(secretBytes, RSAEncryptionPadding.Pkcs1);
        return Convert.ToHexString(decrypted).ToLowerInvariant();
    }

    public static string GenerateRsaSha256Signature(string baseString, RSA privateSignatureKey)
    {
        var data = Encoding.UTF8.GetBytes(baseString);
        var signature = privateSignatureKey.SignData(data, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        return Quote(Convert.ToBase64String(signature));
    }

    public static string GenerateHmacSha256Signature(string baseString, string liveSessionToken)
    {
        var key = Convert.FromBase64String(liveSessionToken);
        using var hmac = new HMACSHA256(key);
        var sig = hmac.ComputeHash(Encoding.UTF8.GetBytes(baseString));
        return Quote(Convert.ToBase64String(sig));
    }

    public static IList<int> GetAccessTokenSecretBytes(string accessTokenSecret)
    {
        var bytes = Convert.FromHexString(accessTokenSecret);
        return bytes.Select(b => (int)b).ToList();
    }

    private static int BitLength(BigInteger x)
    {
        var bytes = x.ToByteArray(isUnsigned: true, isBigEndian: true);
        if (bytes.Length == 0) return 0;
        int bitlen = (bytes.Length - 1) * 8;
        byte msb = bytes[0];
        while (msb > 0)
        {
            bitlen++;
            msb >>= 1;
        }
        return bitlen;
    }

    public static IList<int> ToByteArray(BigInteger x)
    {
        var hex = x.ToString("x");
        if (hex.Length % 2 > 0)
            hex = "0" + hex;
        var list = new List<int>();
        if (BitLength(x) % 8 == 0)
            list.Add(0);
        for (int i = 0; i < hex.Length; i += 2)
            list.Add(Convert.ToInt32(hex.Substring(i, 2), 16));
        return list;
    }

    public static string CalculateLiveSessionToken(string dhPrime, string dhRandomValue, string dhResponse, string prepend)
    {
        var accessTokenSecretBytes = GetAccessTokenSecretBytes(prepend).Select(b => (byte)b).ToArray();
        var dhRandomInt = BigInteger.Parse("0" + dhRandomValue, NumberStyles.HexNumber);
        var dhResponseInt = BigInteger.Parse("0" + dhResponse, NumberStyles.HexNumber);
        var prime = BigInteger.Parse("0" + dhPrime, NumberStyles.HexNumber);
        var sharedSecret = BigInteger.ModPow(dhResponseInt, dhRandomInt, prime);
        var key = ToByteArray(sharedSecret).Select(i => (byte)i).ToArray();
        using var hmac = new HMACSHA1(key);
        var digest = hmac.ComputeHash(accessTokenSecretBytes);
        return Convert.ToBase64String(digest);
    }

    public static bool ValidateLiveSessionToken(string liveSessionToken, string liveSessionTokenSignature, string consumerKey)
    {
        using var hmac = new HMACSHA1(Convert.FromBase64String(liveSessionToken));
        var digest = hmac.ComputeHash(Encoding.UTF8.GetBytes(consumerKey));
        var hex = BitConverter.ToString(digest).Replace("-", string.Empty).ToLowerInvariant();
        return hex == liveSessionTokenSignature;
    }

    public static string GenerateAuthorizationHeaderString(IDictionary<string, string> requestData, string realm)
    {
        var header = string.Join(", ", requestData.OrderBy(kv => kv.Key).Select(kv => $"{kv.Key}=\"{kv.Value}\""));
        return $"OAuth realm=\"{realm}\", {header}";
    }
}
