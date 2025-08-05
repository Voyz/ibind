using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> LiveMarketdataSnapshotAsync(IEnumerable<string> conids, IEnumerable<string> fields)
    {
        var paramsDict = new Dictionary<string, object?>
        {
            ["conids"] = string.Join(",", conids),
            ["fields"] = string.Join(",", fields)
        };
        return await GetAsync("iserver/marketdata/snapshot", paramsDict);
    }

    public async Task<IDictionary<string, IDictionary<string, object?>>> LiveMarketdataSnapshotBySymbolAsync(IEnumerable<object> queries, IEnumerable<string> fields)
    {
        var conidsBySymbolResult = await StockConidBySymbolAsync(queries);
        if (conidsBySymbolResult.Data is not IDictionary<string, string> conidsBySymbol)
            throw new InvalidOperationException("Invalid conid lookup result");

        var conids = conidsBySymbol.Values.ToList();
        var symbolsByConid = conidsBySymbol.ToDictionary(kv => kv.Value, kv => kv.Key);

        await ReceiveBrokerageAccountsAsync();
        await LiveMarketdataSnapshotAsync(conids, fields);
        var entriesResult = await LiveMarketdataSnapshotAsync(conids, fields);
        var entries = entriesResult.Data as IList<Dictionary<string, object?>> ?? new List<Dictionary<string, object?>>();

        var results = new Dictionary<string, IDictionary<string, object?>>();
        foreach (var entry in entries)
        {
            if (!entry.TryGetValue("conid", out var conidObj))
                continue;
            var conid = conidObj?.ToString() ?? string.Empty;
            var output = new Dictionary<string, object?>();
            foreach (var kv in entry)
            {
                if (IbkrDefinitions.SnapshotById.TryGetValue(kv.Key, out var mapped))
                    output[mapped] = kv.Value;
            }
            if (symbolsByConid.TryGetValue(conid, out var symbol))
                results[symbol] = output;
        }
        return results;
    }

    public async Task<Result> RegulatorySnapshotAsync(string conid)
        => await GetAsync("md/regsnapshot", new Dictionary<string, object?> { ["conid"] = conid });

    public async Task<Result> MarketdataHistoryByConidAsync(string conid, string bar, string? exchange = null, string? period = null, bool? outsideRth = null, DateTime? startTime = null)
    {
        var paramsDict = PyUtils.ParamsDict(
            new Dictionary<string, object?> { ["conid"] = conid, ["bar"] = bar },
            new Dictionary<string, object?>
            {
                ["exchange"] = exchange,
                ["period"] = period,
                ["outsideRth"] = outsideRth,
                ["startTime"] = startTime?.ToString("yyyyMMdd-HH:mm:ss")
            });
        return await GetAsync("iserver/marketdata/history", paramsDict);
    }
}

