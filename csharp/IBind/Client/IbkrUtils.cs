using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using IBind.Support;
using IBind.Base;

namespace IBind.Client;

/// <summary>
/// Utility helpers and domain models mirrored from ibkr_utils.py.
/// </summary>
public static class IbkrUtils
{
    private static readonly ILogger _logger = Logs.ProjectLogger();

    #region Stock filtering

    public record StockQuery(
        string Symbol,
        string? NameMatch = null,
        IDictionary<string, object?>? InstrumentConditions = null,
        IDictionary<string, object?>? ContractConditions = null);

    private static bool _Filter(IDictionary<string, object?> data, IDictionary<string, object?> conditions)
    {
        foreach (var (key, value) in conditions)
        {
            if (!data.TryGetValue(key, out var v) || !Equals(v, value))
                return false;
        }
        return true;
    }

    public static IList<Dictionary<string, object?>> ProcessInstruments(
        IList<Dictionary<string, object?>> instruments,
        string? nameMatch = null,
        IDictionary<string, object?>? instrumentConditions = null,
        IDictionary<string, object?>? contractConditions = null)
    {
        var filtered = new List<Dictionary<string, object?>>();
        foreach (var instrument in instruments)
        {
            if (nameMatch != null)
            {
                if (!instrument.TryGetValue("name", out var nameObj) || nameObj is not string name || !name.Contains(nameMatch, StringComparison.OrdinalIgnoreCase))
                    continue;
            }

            if (instrumentConditions != null && !_Filter(instrument, instrumentConditions))
                continue;

            if (contractConditions != null)
            {
                if (!instrument.TryGetValue("contracts", out var contractsObj) || contractsObj is not IList<Dictionary<string, object?>> contracts)
                    continue;
                var filteredContracts = contracts.Where(c => _Filter(c, contractConditions)).ToList();
                if (filteredContracts.Count == 0)
                    continue;
                instrument["contracts"] = filteredContracts;
            }

            filtered.Add(instrument);
        }
        return filtered;
    }

    public static Result FilterStocks(IEnumerable<object> queries, Result result, bool defaultFiltering = true)
    {
        var stocks = new Dictionary<string, object?>();
        if (result.Data is not IDictionary<string, object?> data)
            return ResultHelpers.PassResult(stocks, result);

        foreach (var q in queries)
        {
            var (symbol, nameMatch, instrumentConditions, contractConditions) = ProcessQuery(q, defaultFiltering);
            if (!data.TryGetValue(symbol, out var symbolData) || symbolData is not IList<Dictionary<string, object?>> instruments || instruments.Count == 0)
            {
                _logger.LogError($"Error getting stocks. Could not find valid instruments {symbol} in result: {result}. Skipping query={q}.");
                continue;
            }
            var filteredInstruments = ProcessInstruments(instruments, nameMatch, instrumentConditions, contractConditions);
            stocks[symbol] = filteredInstruments;
        }
        return ResultHelpers.PassResult(stocks, result);
    }

    public static string QueryToSymbols(IEnumerable<object> queries)
        => string.Join(",", queries.Select(q => q is string s ? s : ((StockQuery)q).Symbol));

    public static (string Symbol, string? NameMatch, IDictionary<string, object?>? InstrumentConditions, IDictionary<string, object?>? ContractConditions)
        ProcessQuery(object q, bool defaultFiltering = true)
    {
        StockQuery query = q switch
        {
            string s => new StockQuery(s),
            StockQuery sq => sq,
            _ => throw new ArgumentException("Unsupported query type", nameof(q))
        };

        IDictionary<string, object?>? contractConditions = query.ContractConditions != null
            ? new Dictionary<string, object?>(query.ContractConditions)
            : null;
        if (contractConditions == null && defaultFiltering)
            contractConditions = new Dictionary<string, object?> { { "isUS", true } };

        return (query.Symbol, query.NameMatch, query.InstrumentConditions, contractConditions);
    }

    #endregion

    #region Question handling

    public enum QuestionType
    {
        Undefined,
        PricePercentageConstraint,
        MissingMarketData,
        TickSizeLimit,
        OrderSizeLimit,
        TriggerAndFill,
        OrderValueLimit,
        SizeModificationLimit,
        MandatoryCapPrice,
        CashQuantity,
        CashQuantityOrder,
        StopOrderRisks,
        MultipleAccounts,
        DisruptiveOrders,
        ClosePosition,
    }

    private static readonly Dictionary<QuestionType, string> QuestionTypeTexts = new()
    {
        { QuestionType.PricePercentageConstraint, "price exceeds the Percentage constraint of 3%" },
        { QuestionType.MissingMarketData, "You are submitting an order without market data. We strongly recommend against this as it may result in erroneous and unexpected trades." },
        { QuestionType.TickSizeLimit, "exceeds the Tick Size Limit of" },
        { QuestionType.OrderSizeLimit, "size exceeds the Size Limit of" },
        { QuestionType.TriggerAndFill, "This order will most likely trigger and fill immediately." },
        { QuestionType.OrderValueLimit, "exceeds the Total Value Limit of" },
        { QuestionType.SizeModificationLimit, "size modification exceeds the size modification limit" },
        { QuestionType.MandatoryCapPrice, "To avoid trading at a price that is not consistent with a fair and orderly market" },
        { QuestionType.CashQuantity, "Traders are responsible for understanding cash quantity details, which are provided on a best efforts basis only." },
        { QuestionType.CashQuantityOrder, "Orders that express size using a monetary value (cash quantity) are provided on a non-guaranteed basis." },
        { QuestionType.StopOrderRisks, "You are about to submit a stop order. Please be aware of the various stop order types available and the risks associated with each one." },
        { QuestionType.MultipleAccounts, "This order will be distributed over multiple accounts. We strongly suggest you familiarize yourself with our allocation facilities before submitting orders." },
        { QuestionType.DisruptiveOrders, "If your order is not immediately executable, our systems may, depending on market conditions, reject your order" },
        { QuestionType.ClosePosition, "Would you like to cancel all open orders and then place new closing order?" },
    };

    public static string QuestionText(QuestionType type) => QuestionTypeTexts[type];

    // Additional question types can be added as they are discovered.
    public static readonly Dictionary<string, (QuestionType Type, string Message)> MessageIdToQuestionType = new()
    {
        { "o163", (QuestionType.PricePercentageConstraint, "The following order exceeds the price percentage limit") },
        { "o354", (QuestionType.MissingMarketData, "You are submitting an order without market data. We strongly recommend against this as it may result in erroneous and unexpected trades. Are you sure you want to submit this order?") },
        { "o382", (QuestionType.TickSizeLimit, "The following value exceeds the tick size limit") },
        { "o383", (QuestionType.OrderSizeLimit, "The following order BUY 650 AAPL NASDAQ.NMS size exceeds the Size Limit of 500.\nAre you sure you want to submit this order?") },
        { "o403", (QuestionType.TriggerAndFill, "This order will most likely trigger and fill immediately.\nAre you sure you want to submit this order?") },
        { "o451", (QuestionType.OrderValueLimit, "The following order BUY 650 AAPL NASDAQ.NMS value estimate of 124,995.00 USD exceeds \nthe Total Value Limit of 100,000 USD.\nAre you sure you want to submit this order?") },
        { "o2136", (QuestionType.Undefined, "Mixed allocation order warning") },
        { "o2137", (QuestionType.Undefined, "Cross side order warning") },
        { "o2165", (QuestionType.Undefined, "Warns that instrument does not support trading in fractions outside regular trading hours") },
        { "o10082", (QuestionType.Undefined, "Called Bond warning") },
        { "o10138", (QuestionType.SizeModificationLimit, "The following order size modification exceeds the size modification limit.") },
        { "o10151", (QuestionType.Undefined, "Warns about risks with Market Orders") },
        { "o10152", (QuestionType.Undefined, "Warns about risks associated with stop orders once they become active") },
        { "o10153", (QuestionType.MandatoryCapPrice, "<h4>Confirm Mandatory Cap Price</h4>To avoid trading at a price that is not consistent with a fair and orderly market, IB may set a cap (for a buy order) or sell order). THIS MAY CAUSE AN ORDER THAT WOULD OTHERWISE BE MARKETABLE TO NOT BE TRADED.") },
        { "o10164", (QuestionType.CashQuantity, "Traders are responsible for understanding cash quantity details, which are provided on a best efforts basis only.") },
        { "o10223", (QuestionType.CashQuantityOrder, "<h4>Cash Quantity Order Confirmation</h4>Orders that express size using a monetary value (cash quantity) are provided on a non-guaranteed basis. The system simulates the order by cancelling it once the specified amount is spent (for buy orders) or collected (for sell orders). In addition to the monetary value, the order uses a maximum size that is calculated using the Cash Quantity Estimate Factor, which you can modify in Presets.") },
        { "o10288", (QuestionType.Undefined, "Warns about risks associated with market orders for Crypto") },
        { "o10331", (QuestionType.StopOrderRisks, "You are about to submit a stop order. Please be aware of the various stop order types available and the risks associated with each one.\nAre you sure you want to submit this order?") },
        { "o10332", (QuestionType.Undefined, "OSL Digital Securities LTD Crypto Order Warning") },
        { "o10333", (QuestionType.Undefined, "Option Exercise at the Money warning") },
        { "o10334", (QuestionType.Undefined, "Warns that order will be placed into current omnibus account instead of currently selected global account.") },
    };

    public static bool FindAnswer(string question, IDictionary<object, bool> answers)
    {
        foreach (var (key, value) in answers)
        {
            if (key is QuestionType qt && question.Contains(QuestionText(qt)))
                return value;
            if (key is string s && question.Contains(s))
                return value;
        }
        throw new ArgumentException($"No answer found for question: \"{question}\"");
    }

    public static Result HandleQuestions(Result originalResult, IDictionary<object, bool> answers, Func<string, bool, Result> replyCallback)
    {
        var result = originalResult.Copy();
        var questions = new List<IDictionary<string, object?>>();
        for (var attempt = 0; attempt < 20; attempt++)
        {
            if (result.Data is IDictionary<string, object?> dict && dict.TryGetValue("error", out var errorObj))
            {
                var error = errorObj?.ToString();
                if (error != null && error.Contains("Order couldn't be submitted: Local order ID="))
                {
                    var orders = originalResult.Request != null && originalResult.Request.TryGetValue("json", out var json) && json is IDictionary<string, object?> j && j.TryGetValue("orders", out var o) ? o : null;
                    throw new ExternalBrokerException($"Order couldn't be submitted. Orders are already registered: {orders}");
                }
                throw new ExternalBrokerException($"While handling questions an error was returned: {System.Text.Json.JsonSerializer.Serialize(dict)}");
            }

            if (result.Data is not IList<object?> list)
                throw new ExternalBrokerException($"While handling questions unknown data was returned: {result.Data}. Request: {System.Text.Json.JsonSerializer.Serialize(result.Request)}");

            var first = list[0] as IDictionary<string, object?> ?? throw new ExternalBrokerException($"While handling questions unknown data was returned: {System.Text.Json.JsonSerializer.Serialize(result.Data)}");

            if (!first.ContainsKey("message"))
            {
                object? dataReturn = first;
                if (list.Count == 1)
                    dataReturn = first;
                return ResultHelpers.PassResult(dataReturn!, originalResult);
            }

            if (list.Count != 1)
                _logger.LogWarning($"While handling questions multiple orders were returned: {System.Text.Json.JsonSerializer.Serialize(list)}");

            var messages = first["message"] as IList<object?> ?? new List<object?>();
            if (messages.Count != 1)
                _logger.LogWarning($"While handling questions multiple messages were returned: {System.Text.Json.JsonSerializer.Serialize(messages)}");

            var question = messages[0]?.ToString()?.Trim().Replace("\n", "");
            var answer = FindAnswer(question!, answers);
            questions.Add(new Dictionary<string, object?> { ["q"] = question, ["a"] = answer });

            if (answer)
            {
                var id = first.TryGetValue("id", out var idObj) ? idObj?.ToString() ?? string.Empty : string.Empty;
                result = replyCallback(id, true);
            }
            else
            {
                throw new Exception($"A question was not given a positive reply. Question: \"{question}\". Answers: {System.Text.Json.JsonSerializer.Serialize(answers)}. Request: {System.Text.Json.JsonSerializer.Serialize(result.Request)}");
            }
        }
        throw new Exception($"Too many questions: {System.Text.Json.JsonSerializer.Serialize(originalResult.Data)}: {System.Text.Json.JsonSerializer.Serialize(questions)}");
    }

    #endregion

    #region Order requests

    public record OrderRequest(
        int? Conid,
        string Side,
        double Quantity,
        string OrderType,
        string AcctId,
        double? Price = null,
        string? Conidex = null,
        string? SecType = null,
        string? Coid = null,
        string? ParentId = null,
        string? ListingExchange = null,
        bool? IsSingleGroup = null,
        bool? OutsideRth = null,
        double? AuxPrice = null,
        string? Ticker = null,
        string? Tif = "GTC",
        double? TrailingAmt = null,
        string? TrailingType = null,
        string? Referrer = null,
        double? CashQty = null,
        double? FxQty = null,
        bool? UseAdaptive = null,
        bool? IsCcyConv = null,
        string? AllocationMethod = null,
        string? Strategy = null,
        IDictionary<string, object?>? StrategyParameters = null,
        bool? IsClose = null)
    {
        public IDictionary<string, object?> ToDictionary()
        {
            var dict = new Dictionary<string, object?>();
            foreach (var prop in GetType().GetProperties())
            {
                var value = prop.GetValue(this);
                if (value != null)
                    dict[ToSnakeCase(prop.Name)] = value;
            }
            return dict;
        }
    }

    private static string ToSnakeCase(string name)
    {
        var chars = new List<char>(name.Length + 5);
        for (int i = 0; i < name.Length; i++)
        {
            var c = name[i];
            if (char.IsUpper(c) && i > 0)
                chars.Add('_');
            chars.Add(char.ToLowerInvariant(c));
        }
        return new string(chars.ToArray());
    }

    private static readonly IDictionary<string, string> OrderRequestMapping = new Dictionary<string, string>
    {
        { "conid", "conid" },
        { "side", "side" },
        { "quantity", "quantity" },
        { "order_type", "orderType" },
        { "price", "price" },
        { "coid", "cOID" },
        { "acct_id", "acctId" },
        { "conidex", "conidex" },
        { "sec_type", "secType" },
        { "parent_id", "parentId" },
        { "listing_exchange", "listingExchange" },
        { "is_single_group", "isSingleGroup" },
        { "outside_rth", "outsideRTH" },
        { "aux_price", "auxPrice" },
        { "ticker", "ticker" },
        { "tif", "tif" },
        { "trailing_amt", "trailingAmt" },
        { "trailing_type", "trailingType" },
        { "referrer", "referrer" },
        { "cash_qty", "cashQty" },
        { "fx_qty", "fxQty" },
        { "use_adaptive", "useAdaptive" },
        { "is_ccy_conv", "isCcyConv" },
        { "allocation_method", "allocationMethod" },
        { "strategy", "strategy" },
        { "strategy_parameters", "strategyParameters" },
        { "is_close", "isClose" },
    };

    public static IDictionary<string, object?> ParseOrderRequest(object orderRequest, IDictionary<string, string>? mapping = null)
    {
        mapping ??= OrderRequestMapping;
        IDictionary<string, object?> d;
        if (orderRequest is IDictionary<string, object?> dict)
        {
            _logger.LogWarning("Order request supplied as a dict. Use 'OrderRequest' record instead.");
            d = dict;
        }
        else if (orderRequest is OrderRequest orq)
        {
            d = orq.ToDictionary();
        }
        else
        {
            throw new ArgumentException("order_request must be OrderRequest or dictionary");
        }

        if (d.ContainsKey("conidex") && d.ContainsKey("conid"))
            throw new ArgumentException("Both 'conidex' and 'conid' are provided. When using 'conidex', specify conid=null.");

        var mapped = new Dictionary<string, object?>();
        foreach (var (k, v) in d)
        {
            mapped[mapping.TryGetValue(k, out var mk) ? mk : k] = v;
        }
        return mapped;
    }

    [Obsolete("'MakeOrderRequest' is deprecated. Use 'OrderRequest' record instead.")]
    public static IDictionary<string, object?> MakeOrderRequest(
        object conid,
        string side,
        double quantity,
        string order_type,
        string acct_id,
        double? price = null,
        string? conidex = null,
        string? sec_type = null,
        string? coid = null,
        string? parent_id = null,
        string? listing_exchange = null,
        bool? is_single_group = null,
        bool? outside_rth = null,
        double? aux_price = null,
        string? ticker = null,
        string? tif = "GTC",
        double? trailing_amt = null,
        string? trailing_type = null,
        string? referrer = null,
        double? cash_qty = null,
        double? fx_qty = null,
        bool? use_adaptive = null,
        bool? is_ccy_conv = null,
        string? allocation_method = null,
        string? strategy = null,
        IDictionary<string, object?>? strategy_parameters = null)
    {
        var request = new OrderRequest(
            conid is null ? (int?)null : Convert.ToInt32(conid),
            side,
            quantity,
            order_type,
            acct_id,
            price,
            conidex,
            sec_type,
            coid,
            parent_id,
            listing_exchange,
            is_single_group,
            outside_rth,
            aux_price,
            ticker,
            tif,
            trailing_amt,
            trailing_type,
            referrer,
            cash_qty,
            fx_qty,
            use_adaptive,
            is_ccy_conv,
            allocation_method,
            strategy,
            strategy_parameters);
        return ParseOrderRequest(request);
    }

    #endregion

    #region Misc helpers

    public static DateTime DateFromIbkr(string d)
    {
        try
        {
            return new DateTime(
                int.Parse(d[..4]),
                int.Parse(d[4..6]),
                int.Parse(d[6..8]),
                int.Parse(d[8..10]),
                int.Parse(d[10..12]),
                int.Parse(d[12..14]));
        }
        catch (Exception)
        {
            throw new ArgumentException($"Date seems to be missing fields: {d}");
        }
    }

    public static string? ExtractConid(IDictionary<string, object?> data)
    {
        if (data.TryGetValue("topic", out var topicObj) && topicObj is string topic && topic.Contains('+'))
            return topic.Split('+').Last();
        if (data.TryGetValue("payload", out var payloadObj) && payloadObj is IDictionary<string, object?> payload && payload.TryGetValue("conid", out var conid))
            return conid?.ToString();
        return null;
    }

    public interface ITickleClient
    {
        void Tickle();
    }

    public class Tickler
    {
        private readonly ITickleClient _client;
        private readonly TimeSpan _interval;
        private readonly ILogger _logger = Logs.ProjectLogger();
        private Thread? _thread;
        private readonly ManualResetEventSlim _stopEvent = new(false);

        public Tickler(ITickleClient client, double? interval = null)
        {
            _client = client;
            _interval = TimeSpan.FromSeconds(interval ?? Config.TicklerInterval);
        }

        private void Worker()
        {
            _logger.LogInformation($"Tickler starts with interval={_interval.TotalSeconds} seconds.");
            while (!_stopEvent.Wait(_interval))
            {
                try
                {
                    _client.Tickle();
                }
                catch (TimeoutException)
                {
                    _logger.LogWarning("Tickler encountered a timeout error. This could indicate the servers are restarting. Investigate further if you see this log repeat frequently.");
                }
                catch (Exception e)
                {
                    _logger.LogError(e, "Tickler error");
                }
            }
            _logger.LogInformation("Tickler gracefully stopped.");
        }

        public void Start()
        {
            if (_thread != null)
            {
                _logger.LogInformation("Tickler thread already running. Stop the existing thread first by calling Tickler.Stop()");
                return;
            }
            _stopEvent.Reset();
            _thread = new Thread(Worker) { IsBackground = true };
            _thread.Start();
        }

        public void Stop(TimeSpan? timeout = null)
        {
            if (_thread == null) return;
            _stopEvent.Set();
            _thread.Join(timeout ?? Timeout.InfiniteTimeSpan);
            _thread = null;
        }
    }

    public static IDictionary<string, object> CleanupMarketHistoryResponses(
        IDictionary<string, object> marketHistoryResponse,
        bool raiseOnError = false)
    {
        var results = new Dictionary<string, object>();
        foreach (var (symbol, entry) in marketHistoryResponse)
        {
            if (entry is Exception ex)
            {
                if (raiseOnError)
                {
                    _logger.LogError($"Error fetching market data for {symbol}");
                    throw ex;
                }
                results[symbol] = ex;
                continue;
            }

            if (entry is Result res)
            {
                if (res.Data is IDictionary<string, object> data && data.TryGetValue("mdAvailability", out var availObj) && availObj is string avail)
                {
                    var upper = avail.ToUpperInvariant();
                    if (!(upper.Contains('S') || upper.Contains('R')))
                        _logger.LogWarning($"Market data for {symbol} is not live: {IbkrDefinitions.DecodeDataAvailability(upper.Select(c => c.ToString()))}");
                }

                if (res.Data is IDictionary<string, object> data2 && data2.TryGetValue("data", out var dataEntriesObj) && dataEntriesObj is IList<IDictionary<string, object>> dataEntries)
                {
                    var records = new List<Dictionary<string, object>>();
                    foreach (var record in dataEntries)
                    {
                        records.Add(new Dictionary<string, object>
                        {
                            ["open"] = record["o"],
                            ["high"] = record["h"],
                            ["low"] = record["l"],
                            ["close"] = record["c"],
                            ["volume"] = record["v"],
                            ["date"] = DateTimeOffset.FromUnixTimeMilliseconds(Convert.ToInt64(record["t"])).DateTime,
                        });
                    }
                    results[symbol] = records;
                }
                else
                {
                    results[symbol] = res.Data;
                }
            }
        }
        return results;
    }

    #endregion
}

