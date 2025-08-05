using System.Collections.Generic;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> CreateWatchlistAsync(string id, string name, IEnumerable<IDictionary<string, object?>> rows)
        => await PostAsync("iserver/watchlist", new Dictionary<string, object?> { ["id"] = id, ["name"] = name, ["rows"] = rows });

    public async Task<Result> GetAllWatchlistsAsync(string sc = "USER_WATCHLIST")
        => await GetAsync("iserver/watchlists", new Dictionary<string, object?> { ["SC"] = sc });

    public async Task<Result> GetWatchlistInformationAsync(string id)
        => await GetAsync("iserver/watchlist", new Dictionary<string, object?> { ["id"] = id });

    public async Task<Result> DeleteWatchlistAsync(string id)
        => await DeleteAsync("iserver/watchlist", new Dictionary<string, object?> { ["id"] = id });
}

