using System.Collections.Generic;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> AccountSummaryAsync(string? accountId = null)
    {
        accountId ??= AccountId;
        return await GetAsync($"iserver/account/{accountId}/summary");
    }

    public async Task<Result> AccountProfitAndLossAsync()
        => await GetAsync("iserver/account/pnl/partitioned");

    public async Task<Result> SearchDynamicAccountAsync(string searchPattern)
        => await GetAsync($"iserver/account/search/{searchPattern}");

    public async Task<Result> SetDynamicAccountAsync(string accountId)
        => await PostAsync("iserver/dynaccount", new Dictionary<string, object?> { ["acctId"] = accountId });

    public async Task<Result> SignaturesAndOwnersAsync(string? accountId = null)
    {
        accountId ??= AccountId;
        return await GetAsync($"acesws/{accountId}/signatures-and-owners");
    }

    public async Task<Result> SwitchAccountAsync(string accountId)
    {
        var result = await PostAsync("iserver/account", new Dictionary<string, object?> { ["acctId"] = accountId });
        AccountId = accountId;
        // Potentially switch websocket account as well
        Logger.LogWarning($"ALSO NEED TO SWITCH WEBSOCKET ACCOUNT TO {AccountId}");
        return result;
    }

    public async Task<Result> ReceiveBrokerageAccountsAsync()
        => await GetAsync("iserver/accounts");
}

