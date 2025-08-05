using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace IBind.Support;

/// <summary>
/// Helper utilities that mirror functionality from the Python support module.
/// </summary>
public static class PyUtils
{
    /// <summary>
    /// Recursively remove null values from a dictionary.
    /// </summary>
    public static IDictionary<string, object?> FilterNone(IDictionary<string, object?> dict)
    {
        var result = new Dictionary<string, object?>();
        foreach (var (key, value) in dict)
        {
            if (value is IDictionary<string, object?> nested)
            {
                var filtered = FilterNone(nested);
                if (filtered.Count > 0)
                    result[key] = filtered;
            }
            else if (value != null)
            {
                result[key] = value;
            }
        }
        return result;
    }

    /// <summary>
    /// Build a dictionary from required and optional parameters, dropping null values.
    /// </summary>
    public static IDictionary<string, object?>? ParamsDict(
        IDictionary<string, object?>? required = null,
        IDictionary<string, object?>? optional = null,
        IDictionary<string, Func<object?, object?>>? preprocessors = null)
    {
        var d = required != null ? new Dictionary<string, object?>(required) : new Dictionary<string, object?>();

        if (optional != null)
        {
            foreach (var (key, value) in optional)
            {
                if (value != null && !(value is IList list && list.Count == 0))
                {
                    var newValue = value;
                    if (preprocessors != null && preprocessors.TryGetValue(key, out var pre))
                        newValue = pre(value);
                    d[key] = newValue;
                }
            }
        }

        return d.Count > 0 ? d : null;
    }

    /// <summary>
    /// Wait until a condition is met or timeout expires.
    /// </summary>
    public static async Task<bool> WaitUntil(Func<bool> condition, TimeSpan timeout, string? timeoutMessage = null, ILogger? logger = null)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            if (condition())
                return true;
            await Task.Delay(100);
        }
        if (timeoutMessage != null)
            logger?.LogError(timeoutMessage);
        return false;
    }

    /// <summary>
    /// Generate a unique name for the current thread.
    /// </summary>
    public static string ThreadName() => $"{Thread.CurrentThread.Name ?? "thread"}-{Environment.CurrentManagedThreadId}";

    /// <summary>
    /// Convert an exception and its inner exceptions to a string.
    /// </summary>
    public static string ExceptionToString(Exception exception)
    {
        var sb = new StringBuilder();
        BuildExceptionString(exception, sb);
        return sb.ToString();
    }

    private static void BuildExceptionString(Exception ex, StringBuilder sb)
    {
        sb.AppendLine(ex.ToString());
        if (ex.InnerException != null)
        {
            sb.AppendLine();
            sb.AppendLine("The below exception was the direct cause of the above exception:");
            BuildExceptionString(ex.InnerException, sb);
        }
    }

    /// <summary>
    /// A lock with timeout behaviour.
    /// </summary>
    public sealed class TimeoutLock : IDisposable
    {
        private readonly object _sync = new();
        private readonly TimeSpan _timeout;
        private bool _acquired;

        public TimeoutLock(TimeSpan timeout)
        {
            _timeout = timeout;
        }

        public bool Acquire()
        {
            _acquired = Monitor.TryEnter(_sync, _timeout);
            return _acquired;
        }

        public void Release()
        {
            if (_acquired)
            {
                Monitor.Exit(_sync);
                _acquired = false;
            }
        }

        public void Dispose() => Release();
    }
}

