using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;
using Microsoft.Extensions.Logging;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> AuthenticationStatusAsync()
        => await PostAsync("iserver/auth/status");

    public async Task<Result> InitializeBrokerageSessionAsync(bool compete = true)
        => await PostAsync("iserver/auth/ssodh/init", new Dictionary<string, object?>
        {
            ["publish"] = true,
            ["compete"] = compete,
        });

    public async Task<Result> LogoutAsync() => await PostAsync("logout");

    public async Task<Result> TickleAsync(bool log = false)
        => await PostAsync("tickle", log: log);

    public async Task<Result> ReauthenticateAsync() => await PostAsync("iserver/reauthenticate");

    public async Task<Result> ValidateAsync() => await GetAsync("sso/validate");

    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var result = await TickleAsync();
            if (result.Data is not IDictionary<string, object?> data)
                throw new InvalidOperationException("Health check request returned invalid data");
            if (data.TryGetValue("iserver", out var iserverObj) &&
                iserverObj is IDictionary<string, object?> iserver &&
                iserver.TryGetValue("authStatus", out var authObj) &&
                authObj is IDictionary<string, object?> auth)
            {
                var authenticated = auth.TryGetValue("authenticated", out var a) && a is bool b1 && b1;
                var competing = auth.TryGetValue("competing", out var c) && c is bool b2 && b2;
                var connected = auth.TryGetValue("connected", out var d) && d is bool b3 && b3;
                return authenticated && !competing && connected;
            }
            throw new InvalidOperationException("Health check request returned invalid data");
        }
        catch (ExternalBrokerException e) when (e.StatusCode == 401)
        {
            Logger.LogInformation("Gateway session is not authenticated.");
            return false;
        }
        catch (TaskCanceledException)
        {
            Logger.LogError("Gateway connect timeout.");
            return false;
        }
        catch (Exception e)
        {
            Logger.LogError(e, "Tickle request failed");
            return false;
        }
    }

    void IbkrUtils.ITickleClient.Tickle()
    {
        TickleAsync().GetAwaiter().GetResult();
    }
}

