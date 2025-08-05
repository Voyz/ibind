using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Extensions.Configuration;

namespace IBind;

/// <summary>
/// Configuration constants with environment and appsettings overrides.
/// Mirrors values from the Python var.py module.
/// </summary>
public static class Config
{
    private static readonly IConfiguration _cfg;

    static Config()
    {
        var builder = new ConfigurationBuilder()
            .AddJsonFile("appsettings.json", optional: true)
            .AddEnvironmentVariables();
        _cfg = builder.Build();
    }

    private static readonly Dictionary<string, bool> BoolMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["y"] = true,
        ["yes"] = true,
        ["t"] = true,
        ["true"] = true,
        ["on"] = true,
        ["1"] = true,
        ["n"] = false,
        ["no"] = false,
        ["f"] = false,
        ["false"] = false,
        ["off"] = false,
        ["0"] = false,
    };

    private static bool GetBool(string key, bool defaultValue)
    {
        var value = _cfg[key];
        if (string.IsNullOrEmpty(value))
            return defaultValue;
        if (BoolMap.TryGetValue(value, out var result))
            return result;
        throw new ArgumentException($"\"{value}\" is not a valid bool value");
    }

    private static int GetInt(string key, int defaultValue)
    {
        var value = _cfg[key];
        if (string.IsNullOrEmpty(value))
            return defaultValue;
        return int.TryParse(value, out var result)
            ? result
            : throw new FormatException($"\"{value}\" is not a valid int value for {key}");
    }

    private static string? GetString(string key, string? defaultValue = null)
        => _cfg[key] ?? defaultValue;

    // General
    public static bool UseSession => GetBool("IBIND_USE_SESSION", true);
    public static bool AutoRegisterShutdown => GetBool("IBIND_AUTO_REGISTER_SHUTDOWN", true);
    public static bool LogResponses => GetBool("IBIND_LOG_RESPONSES", false);

    // Logs
    public static bool LogToConsole => GetBool("IBIND_LOG_TO_CONSOLE", true);
    public static bool LogToFile => GetBool("IBIND_LOG_TO_FILE", true);
    public static string LogLevel => GetString("IBIND_LOG_LEVEL", "INFO")!;
    public static string LogFormat => GetString("IBIND_LOG_FORMAT", "%(asctime)s|%(levelname)-.1s| %(message)s")!;
    public static string LogsDir => GetString("IBIND_LOGS_DIR", Path.GetTempPath())!;
    public static bool PrintFileLogs => GetBool("IBIND_PRINT_FILE_LOGS", false);

    // IBKR
    public static string? RestUrl => GetString("IBIND_REST_URL");
    public static string? WsUrl => GetString("IBIND_WS_URL");
    public static string? AccountId => GetString("IBIND_ACCOUNT_ID");
    public static string? CaCert => GetString("IBIND_CACERT");
    public static int WsPingInterval => GetInt("IBIND_WS_PING_INTERVAL", 45);
    public static int WsMaxPingInterval => GetInt("IBIND_WS_MAX_PING_INTERVAL", 300);
    public static int WsTimeout => GetInt("IBIND_WS_TIMEOUT", 5);
    public static int WsSubscriptionRetries => GetInt("IBIND_WS_SUBSCRIPTION_RETRIES", 5);
    public static int WsSubscriptionTimeout => GetInt("IBIND_WS_SUBSCRIPTION_TIMEOUT", 2);
    public static bool WsLogRawMessages => GetBool("IBIND_WS_LOG_RAW_MESSAGES", false);

    // OAuth common
    public static bool UseOAuth => GetBool("IBIND_USE_OAUTH", false);
    public static bool InitOAuth => GetBool("IBIND_INIT_OAUTH", true);
    public static bool InitBrokerageSession => GetBool("IBIND_INIT_BROKERAGE_SESSION", true);
    public static bool MaintainOAuth => GetBool("IBIND_MAINTAIN_OAUTH", true);
    public static bool ShutdownOAuth => GetBool("IBIND_SHUTDOWN_OAUTH", true);
    public static int TicklerInterval => GetInt("IBIND_TICKLER_INTERVAL", 60);

    // OAuth 1.0a
    public static string OAuth1aRestUrl => GetString("IBIND_OAUTH1A_REST_URL", "https://api.ibkr.com/v1/api/")!;
    public static string OAuth1aWsUrl => GetString("IBIND_OAUTH1A_WS_URL", "wss://api.ibkr.com/v1/api/ws")!;
    public static string OAuth1aLiveSessionTokenEndpoint => GetString("IBIND_OAUTH1A_LIVE_SESSION_TOKEN_ENDPOINT", "oauth/live_session_token")!;
    public static string? OAuth1aAccessToken => GetString("IBIND_OAUTH1A_ACCESS_TOKEN");
    public static string? OAuth1aAccessTokenSecret => GetString("IBIND_OAUTH1A_ACCESS_TOKEN_SECRET");
    public static string? OAuth1aConsumerKey => GetString("IBIND_OAUTH1A_CONSUMER_KEY");
    public static string? OAuth1aDhPrime => GetString("IBIND_OAUTH1A_DH_PRIME");
    public static string? OAuth1aEncryptionKeyFp => GetString("IBIND_OAUTH1A_ENCRYPTION_KEY_FP");
    public static string? OAuth1aSignatureKeyFp => GetString("IBIND_OAUTH1A_SIGNATURE_KEY_FP");
    public static int OAuth1aDhGenerator => GetInt("IBIND_OAUTH1A_DH_GENERATOR", 2);
    public static string OAuth1aRealm => GetString("IBIND_OAUTH1A_REALM", "limited_poa")!;
}

