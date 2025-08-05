using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using IBind.Base;
using IBind.Support;

namespace IBind.Client;

public partial class IbkrClient
{
    private static readonly object OrderSubmissionLock = new();

    public async Task<Result> LiveOrdersAsync(IEnumerable<string>? filters = null, bool? force = null, string? accountId = null)
    {
        var paramsDict = PyUtils.ParamsDict(optional: new Dictionary<string, object?>
        {
            ["filters"] = filters != null ? string.Join(",", filters) : null,
            ["force"] = force,
            ["accountId"] = accountId
        });
        return await GetAsync("iserver/account/orders", paramsDict);
    }

    public async Task<Result> OrderStatusAsync(string orderId)
        => await GetAsync($"iserver/account/order/status/{orderId}");

    public async Task<Result> TradesAsync(string? days = null, string? accountId = null)
    {
        accountId ??= AccountId;
        var paramsDict = PyUtils.ParamsDict(optional: new Dictionary<string, object?>
        {
            ["days"] = days,
            ["accountId"] = accountId
        });
        return await GetAsync("iserver/account/trades/", paramsDict);
    }

    public Task<Result> PlaceOrderAsync(IEnumerable<IbkrUtils.OrderRequest> orderRequest, IDictionary<object, bool> answers, string? accountId = null)
    {
        accountId ??= AccountId;
        var parsed = orderRequest.Select(r => IbkrUtils.ParseOrderRequest(r)).ToList();
        lock (OrderSubmissionLock)
        {
            var result = PostAsync($"iserver/account/{accountId}/orders", new Dictionary<string, object?>
            {
                ["orders"] = parsed
            }).GetAwaiter().GetResult();
            var handled = IbkrUtils.HandleQuestions(result, answers, (id, confirmed) => ReplyAsync(id, confirmed).GetAwaiter().GetResult());
            return Task.FromResult(handled);
        }
    }

    public async Task<Result> ReplyAsync(string replyId, bool confirmed)
        => await PostAsync($"iserver/reply/{replyId}", new Dictionary<string, object?> { ["confirmed"] = confirmed });

    public async Task<Result> WhatIfOrderAsync(IbkrUtils.OrderRequest orderRequest, string? accountId = null)
    {
        accountId ??= AccountId;
        var parsed = IbkrUtils.ParseOrderRequest(orderRequest);
        return await PostAsync($"iserver/account/{accountId}/orders/whatif", new Dictionary<string, object?> { ["orders"] = new List<IDictionary<string, object?>> { parsed } });
    }

    public async Task<Result> CancelOrderAsync(string orderId, string? accountId = null)
    {
        accountId ??= AccountId;
        return await DeleteAsync($"iserver/account/{accountId}/order/{orderId}");
    }

    public Task<Result> ModifyOrderAsync(string orderId, IbkrUtils.OrderRequest orderRequest, IDictionary<object, bool> answers, string? accountId = null)
    {
        accountId ??= AccountId;
        var parsed = IbkrUtils.ParseOrderRequest(orderRequest);
        lock (OrderSubmissionLock)
        {
            var result = PostAsync($"iserver/account/{accountId}/order/{orderId}", parsed).GetAwaiter().GetResult();
            var handled = IbkrUtils.HandleQuestions(result, answers, (id, confirmed) => ReplyAsync(id, confirmed).GetAwaiter().GetResult());
            return Task.FromResult(handled);
        }
    }

    public async Task<Result> SuppressMessagesAsync(IEnumerable<string> messageIds)
        => await PostAsync("iserver/questions/suppress", new Dictionary<string, object?> { ["messageIds"] = messageIds.ToList() });

    public async Task<Result> ResetSuppressedMessagesAsync()
        => await PostAsync("iserver/questions/suppress/reset");
}

