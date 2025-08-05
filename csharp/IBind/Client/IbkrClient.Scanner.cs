using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    public async Task<Result> ScannerParametersAsync() => await GetAsync("iserver/scanner/params");

    public async Task<Result> MarketScannerAsync(string instrument, string type, string location, IEnumerable<IDictionary<string, string>>? filter = null)
    {
        var paramsDict = PyUtils.ParamsDict(
            new Dictionary<string, object?>
            {
                ["instrument"] = instrument,
                ["type"] = type,
                ["location"] = location
            },
            new Dictionary<string, object?> { ["filter"] = filter?.ToList() ?? new List<IDictionary<string, string>>() });
        return await PostAsync("iserver/scanner/run", paramsDict);
    }
}

