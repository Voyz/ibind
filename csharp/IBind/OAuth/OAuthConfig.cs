using System;

namespace IBind.OAuth;

/// <summary>
/// Base configuration for OAuth flows.
/// Mirrors ibind.oauth.OAuthConfig.
/// </summary>
public abstract record OAuthConfig
{
    /// <summary>OAuth version string.</summary>
    public abstract string Version { get; }

    /// <summary>Whether OAuth should be automatically initialised.</summary>
    public bool InitOAuth { get; init; } = Config.InitOAuth;

    /// <summary>Whether the brokerage session should be initialised on startup.</summary>
    public bool InitBrokerageSession { get; init; } = Config.InitBrokerageSession;

    /// <summary>Whether OAuth maintenance should run automatically.</summary>
    public bool MaintainOAuth { get; init; } = Config.MaintainOAuth;

    /// <summary>Whether OAuth should be shutdown automatically on termination.</summary>
    public bool ShutdownOAuth { get; init; } = Config.ShutdownOAuth;

    /// <summary>Interval in seconds for keep-alive tickler.</summary>
    public int TicklerInterval { get; init; } = Config.TicklerInterval;

    /// <summary>
    /// Validate configuration values. Subclasses may override.
    /// </summary>
    public virtual void VerifyConfig() { }
}
