using System;

namespace IBind.Support;

/// <summary>
/// Represents an unexpected error originating from an external broker.
/// </summary>
public class ExternalBrokerException : Exception
{
    public int? StatusCode { get; }

    public ExternalBrokerException(string message, int? statusCode = null, Exception? innerException = null)
        : base(message, innerException)
    {
        StatusCode = statusCode;
    }
}

