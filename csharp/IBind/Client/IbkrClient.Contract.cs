using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> SecurityDefinitionByConidAsync(IEnumerable<string> conids)
    {
        var joined = string.Join(",", conids);
        return await GetAsync("trsrv/secdef", new Dictionary<string, object?> { ["conids"] = joined });
    }

    public async Task<Result> ContractInformationByConidAsync(string conid)
        => await GetAsync($"iserver/contract/{conid}/info");

    public async Task<Result> SecurityStocksBySymbolAsync(IEnumerable<object> queries, bool? defaultFiltering = null)
    {
        var symbols = IbkrUtils.QueryToSymbols(queries);
        var result = await GetAsync("trsrv/stocks", new Dictionary<string, object?> { ["symbols"] = symbols });
        return IbkrUtils.FilterStocks(queries, result, defaultFiltering ?? true);
    }

    public async Task<Result> StockConidBySymbolAsync(IEnumerable<object> queries, bool? defaultFiltering = null, string returnType = "dict")
    {
        var stocksResult = await SecurityStocksBySymbolAsync(queries, defaultFiltering);
        if (stocksResult.Data is not IDictionary<string, object?> data)
            return stocksResult;
        var conids = new Dictionary<string, string>();
        foreach (var (symbol, value) in data)
        {
            if (value is IList<Dictionary<string, object?>> instruments &&
                instruments.Count == 1 &&
                instruments[0].TryGetValue("contracts", out var contractsObj) &&
                contractsObj is IList<Dictionary<string, object?>> contracts &&
                contracts.Count == 1 &&
                contracts[0].TryGetValue("conid", out var conidObj))
            {
                conids[symbol] = conidObj?.ToString() ?? string.Empty;
            }
            else
            {
                throw new ExternalBrokerException($"Filtering stock \"{symbol}\" did not yield exactly one contract. Use filters to avoid ambiguity.");
            }
        }
        return ResultHelpers.PassResult(conids, stocksResult);
    }
}

