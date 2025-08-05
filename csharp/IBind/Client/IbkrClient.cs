using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using IBind.Base;
using IBind.Support;
using IBind.OAuth;

namespace IBind.Client;

/// <summary>
/// REST client for the Interactive Brokers HTTP API.
/// </summary>
public partial class IbkrClient : RestClient, IbkrUtils.ITickleClient
{
    private readonly bool _useOauth;
    private OAuth1aConfig? _oauthConfig;
    private string? _liveSessionToken;
    private long _liveSessionTokenExpiresMs;
    private string? _liveSessionTokenSignature;
    private IbkrUtils.Tickler? _tickler;
    private readonly ILogger _logger;
    protected ILogger Logger => _logger;

    public string? AccountId { get; private set; }

    public string BaseUrl { get; }

    public OAuth1aConfig OAuthConfig => _oauthConfig ??= new OAuth1aConfig();

    public string? LiveSessionToken => _liveSessionToken;

    public IbkrClient(
        string? accountId = null,
        string? url = null,
        string host = "127.0.0.1",
        string port = "5000",
        string baseRoute = "/v1/api/",
        object? cacert = null,
        TimeSpan? timeout = null,
        int maxRetries = 3,
        bool? useSession = null,
        bool? autoRegisterShutdown = null,
        bool? logResponses = null,
        bool useOauth = false,
        OAuth1aConfig? oauthConfig = null)
        : base(
            (url ?? (useOauth
                ? (oauthConfig ?? new OAuth1aConfig()).OAuthRestUrl
                : $"https://{host}:{port}{baseRoute}")),
            cacert: useOauth ? true : cacert,
            timeout: timeout,
            maxRetries: maxRetries,
            useSession: useSession,
            autoRegisterShutdown: autoRegisterShutdown,
            logResponses: logResponses)
    {
        var finalUrl = url ?? (useOauth
            ? (oauthConfig ?? new OAuth1aConfig()).OAuthRestUrl
            : $"https://{host}:{port}{baseRoute}");
        BaseUrl = finalUrl.EndsWith("/") ? finalUrl : finalUrl + "/";

        AccountId = accountId;
        _logger = Logs.NewDailyRotatingFileLogger(
            "IbkrClient",
            Path.Combine(Config.LogsDir, $"ibkr_client_{accountId ?? "default"}"));
        _useOauth = useOauth;
        if (_useOauth)
        {
            _oauthConfig = oauthConfig ?? new OAuth1aConfig();
            _oauthConfig.VerifyConfig();
        }

        Logger.LogInformation("#################");
        Logger.LogInformation(
            $"New IbkrClient(base_url={BaseUrl}, account_id={AccountId}, ssl={cacert}, timeout={timeout?.TotalSeconds ?? 10}, max_retries={maxRetries}, use_oauth={_useOauth})");
    }

    protected override IDictionary<string, string> GetHeaders(string requestMethod, string requestUrl)
    {
        if (!_useOauth || requestUrl == $"{BaseUrl}{OAuthConfig.LiveSessionTokenEndpoint}")
            return new Dictionary<string, string>();

        return OAuth1aClient.GenerateOAuthHeaders(
            OAuthConfig,
            new HttpMethod(requestMethod),
            requestUrl,
            liveSessionToken: _liveSessionToken,
            extraHeaders: new Dictionary<string, string>
            {
                ["Authorization"] = $"Bearer {_liveSessionToken}"
            });
    }

    protected override async Task<Result> _RequestAsync(
        HttpMethod method,
        string endpoint,
        string? baseUrl,
        IDictionary<string, string>? extraHeaders,
        bool log,
        IDictionary<string, object?>? query,
        IDictionary<string, object?>? json)
    {
        try
        {
            return await base._RequestAsync(method, endpoint, baseUrl, extraHeaders, log, query, json);
        }
        catch (ExternalBrokerException e) when (e.StatusCode == 400 && e.Message.Contains("Bad Request: no bridge"))
        {
            throw new ExternalBrokerException("IBKR returned 400 Bad Request: no bridge. Try calling InitializeBrokerageSessionAsync first.", e.StatusCode, e);
        }
    }

    public async Task GenerateLiveSessionTokenAsync()
    {
        var client = new OAuth1aClient(new HttpClient(), OAuthConfig);
        var (lst, expires, sig) = await client.RequestLiveSessionTokenAsync();
        _liveSessionToken = lst;
        _liveSessionTokenExpiresMs = expires;
        _liveSessionTokenSignature = sig;
    }

    public async Task OauthInitAsync(bool maintainOauth, bool initBrokerageSession)
    {
        await GenerateLiveSessionTokenAsync();
        if (initBrokerageSession)
            await InitializeBrokerageSessionAsync();
        if (maintainOauth)
            StartTickler();
    }

    private void StartTickler()
    {
        if (_tickler != null) return;
        _tickler = new IbkrUtils.Tickler(this, TimeSpan.FromMinutes(1).TotalSeconds);
        _tickler.Start();
    }

    public void StopTickler()
    {
        _tickler?.Stop();
        _tickler = null;
    }
}

