using System.Collections.Generic;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> PortfolioAccountsAsync() => await GetAsync("portfolio/accounts");

    public async Task<Result> PortfolioSubaccountsAsync() => await GetAsync("portfolio/subaccounts");

    public async Task<Result> PortfolioAccountInformationAsync(string? accountId = null)
    {
        accountId ??= AccountId;
        return await GetAsync($"portfolio/{accountId}/meta");
    }

    public async Task<Result> PortfolioAccountAllocationAsync(string? accountId = null)
    {
        accountId ??= AccountId;
        return await GetAsync($"portfolio/{accountId}/allocation");
    }

    public async Task<Result> CombinationPositionsAsync(string? accountId = null, bool? noCache = null)
    {
        accountId ??= AccountId;
        var paramsDict = PyUtils.ParamsDict(optional: new Dictionary<string, object?>
        {
            ["nocache"] = noCache
        });
        return await GetAsync($"portfolio/{accountId}/combo/positions", paramsDict);
    }

    public async Task<Result> PositionsAsync(string? accountId = null, int page = 0, string? model = null, string? sort = null, string? direction = null, string? period = null)
    {
        accountId ??= AccountId;
        var paramsDict = PyUtils.ParamsDict(optional: new Dictionary<string, object?>
        {
            ["model"] = model,
            ["sort"] = sort,
            ["direction"] = direction,
            ["period"] = period
        });
        return await GetAsync($"portfolio/{accountId}/positions/{page}", paramsDict);
    }
}

