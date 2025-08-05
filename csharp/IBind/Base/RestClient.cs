using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using IBind.Support;

namespace IBind.Base;

public record Result(object? Data = null, IDictionary<string, object?>? Request = null)
{
    public Result Copy(object? data = null, IDictionary<string, object?>? request = null)
        => new(data ?? Data, request ?? (Request != null ? new Dictionary<string, object?>(Request) : null));
}

public static class ResultHelpers
{
    public static Result PassResult(object data, Result oldResult) => oldResult.Copy(data: data);
}

public class RestClient : IDisposable
{
    private readonly TimeSpan _timeout;
    private readonly int _maxRetries;
    private readonly bool _logResponses;
    private readonly bool _useSession;
    private readonly object? _cacert;
    private HttpClient? _client;
    private ILogger? _logger;
    private readonly string _baseUrl;
    private bool _closed;

    public RestClient(
        string url,
        object? cacert = null,
        TimeSpan? timeout = null,
        int maxRetries = 3,
        bool? useSession = null,
        bool? autoRegisterShutdown = null,
        bool? logResponses = null)
    {
        if (url == null) throw new ArgumentNullException(nameof(url));
        _baseUrl = url.EndsWith("/") ? url : url + "/";

        _cacert = cacert ?? (Config.CaCert ?? (object)false);
        _timeout = timeout ?? TimeSpan.FromSeconds(10);
        _maxRetries = maxRetries;
        _useSession = useSession ?? Config.UseSession;
        _logResponses = logResponses ?? Config.LogResponses;

        _make_logger();
        if (_useSession)
            MakeClient();

        if (autoRegisterShutdown ?? Config.AutoRegisterShutdown)
            RegisterShutdownHandler();
    }

    private void _make_logger()
    {
        _logger = Logs.NewDailyRotatingFileLogger("RestClient", Path.Combine(Config.LogsDir, "rest_client"));
    }

    private ILogger Logger => _logger ??= Logs.NewDailyRotatingFileLogger("RestClient", Path.Combine(Config.LogsDir, "rest_client"));

    private HttpClient CreateClient()
    {
        var handler = new HttpClientHandler();
        if (_cacert is bool b && b == false)
        {
            handler.ServerCertificateCustomValidationCallback = HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
        }
        else if (_cacert is string path && File.Exists(path))
        {
            try
            {
                var cert = new X509Certificate2(path);
                handler.ClientCertificates.Add(cert);
            }
            catch (Exception e)
            {
                Logger.LogWarning(e, $"Failed to load certificate from {path}, continuing with default certificates.");
            }
        }
        var client = new HttpClient(handler);
        client.Timeout = _timeout;
        return client;
    }

    private void MakeClient()
    {
        _client = CreateClient();
    }

    public async Task<Result> GetAsync(
        string path,
        IDictionary<string, object?>? @params = null,
        string? baseUrl = null,
        IDictionary<string, string>? extraHeaders = null,
        bool log = true)
    {
        return await RequestAsync(HttpMethod.Get, path, baseUrl, extraHeaders, log, query: @params);
    }

    public async Task<Result> PostAsync(
        string path,
        IDictionary<string, object?>? @params = null,
        string? baseUrl = null,
        IDictionary<string, string>? extraHeaders = null,
        bool log = true)
    {
        return await RequestAsync(HttpMethod.Post, path, baseUrl, extraHeaders, log, json: @params);
    }

    public async Task<Result> DeleteAsync(
        string path,
        IDictionary<string, object?>? @params = null,
        string? baseUrl = null,
        IDictionary<string, string>? extraHeaders = null,
        bool log = true)
    {
        return await RequestAsync(HttpMethod.Delete, path, baseUrl, extraHeaders, log, json: @params);
    }

    protected virtual IDictionary<string, string> GetHeaders(string requestMethod, string requestUrl)
        => new Dictionary<string, string>();

    public async Task<Result> RequestAsync(
        HttpMethod method,
        string endpoint,
        string? baseUrl = null,
        IDictionary<string, string>? extraHeaders = null,
        bool log = true,
        IDictionary<string, object?>? query = null,
        IDictionary<string, object?>? json = null)
    {
        return await _RequestAsync(method, endpoint, baseUrl, extraHeaders, log, query, json);
    }

    protected virtual async Task<Result> _RequestAsync(
        HttpMethod method,
        string endpoint,
        string? baseUrl,
        IDictionary<string, string>? extraHeaders,
        bool log,
        IDictionary<string, object?>? query,
        IDictionary<string, object?>? json)
    {
        baseUrl ??= _baseUrl;
        endpoint = endpoint.TrimStart('/');
        var url = baseUrl + endpoint;

        if (query != null)
        {
            var filtered = PyUtils.FilterNone(query);
            if (filtered.Count > 0)
            {
                var qs = string.Join("&", filtered.Select(kv => $"{Uri.EscapeDataString(kv.Key)}={Uri.EscapeDataString(kv.Value!.ToString()!)}"));
                url += (url.Contains("?") ? "&" : "?") + qs;
            }
        }

        var headers = GetHeaders(method.Method, url);
        if (extraHeaders != null)
        {
            foreach (var (k, v) in extraHeaders)
                headers[k] = v;
        }

        var data = json != null ? PyUtils.FilterNone(json) : null;
        string? content = null;
        if (data != null && data.Count > 0)
            content = JsonSerializer.Serialize(data);

        for (var attempt = 0; attempt <= _maxRetries; attempt++)
        {
            HttpClient? tempClient = null;
            var client = _useSession ? _client ?? (tempClient = CreateClient()) : (tempClient = CreateClient());

            try
            {
                if (log)
                {
                    var attemptStr = attempt > 0 ? $" (attempt: {attempt})" : string.Empty;
                    Logger.LogInformation($"{method.Method} {url} {attemptStr}");
                }

                using var request = new HttpRequestMessage(method, url);
                foreach (var (k, v) in headers)
                    request.Headers.TryAddWithoutValidation(k, v);
                if (content != null)
                    request.Content = new StringContent(content, Encoding.UTF8, "application/json");

                var response = await client.SendAsync(request);
                var requestDict = new Dictionary<string, object?> { ["url"] = url };
                if (query != null) requestDict["params"] = query;
                if (data != null) requestDict["json"] = data;
                var result = new Result(null, requestDict);
                result = await ProcessResponseAsync(response, result);
                if (_logResponses)
                    Logger.LogInformation(JsonSerializer.Serialize(result));
                return result;
            }
            catch (TaskCanceledException e) when (!e.CancellationToken.IsCancellationRequested)
            {
                if (attempt >= _maxRetries)
                    throw new TimeoutException($"{this}: Reached max retries ({_maxRetries}) for {method.Method} {url}", e);
                var msg = $"{this}: Timeout for {method.Method} {url}, retrying attempt {attempt + 1}/{_maxRetries}";
                Logger.LogInformation(msg);
                continue;
            }
            catch (HttpRequestException e)
            {
                var msg = $"{this}: Connection error detected, resetting session and retrying attempt {attempt + 1}/{_maxRetries} :: {e.Message}";
                Logger.LogWarning(msg);
                Close();
                if (_useSession)
                    MakeClient();
                continue;
            }
            catch (ExternalBrokerException)
            {
                throw;
            }
            catch (Exception e)
            {
                Logger.LogError(e, $"{this}: request error");
                throw new ExternalBrokerException($"{this}: request error: {e.Message}", null, e);
            }
            finally
            {
                if (!_useSession)
                    tempClient?.Dispose();
            }
        }

        throw new ExternalBrokerException($"{this}: request error: exceeded retries");
    }

    protected virtual async Task<Result> ProcessResponseAsync(HttpResponseMessage response, Result result)
    {
        try
        {
            response.EnsureSuccessStatusCode();
            var content = await response.Content.ReadAsStringAsync();
            if (!string.IsNullOrWhiteSpace(content))
                result = result.Copy(data: JsonSerializer.Deserialize<object>(content));
            return result;
        }
        catch (TaskCanceledException e)
        {
            throw new ExternalBrokerException($"{this}: Timeout error ({_timeout.TotalSeconds}s)", (int)response.StatusCode, e);
        }
        catch (JsonException e)
        {
            Logger.LogError("Invalid JSON response: {Message}", e.Message);
            throw new ExternalBrokerException($"{this}: API returned invalid JSON.", (int)response.StatusCode, e);
        }
        catch (Exception e)
        {
            var text = await response.Content.ReadAsStringAsync();
            throw new ExternalBrokerException($"{this}: response error {result} :: {(int)response.StatusCode} :: {response.ReasonPhrase} :: {text}", (int)response.StatusCode, e);
        }
    }

    public void Close()
    {
        _client?.Dispose();
        _client = null;
    }

    public void RegisterShutdownHandler()
    {
        _closed = false;
        void CloseHandler(object? sender, EventArgs e)
        {
            if (_closed) return;
            _closed = true;
            Close();
        }

        AppDomain.CurrentDomain.ProcessExit += CloseHandler;
        Console.CancelKeyPress += (_, _) => CloseHandler(null, EventArgs.Empty);
    }

    public override string ToString() => GetType().Name;

    public void Dispose() => Close();
}
