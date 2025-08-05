using System;
using System.IO;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;

namespace IBind.Support;

/// <summary>
/// Logging helpers that mirror the Python logging utilities.
/// </summary>
public static class Logs
{
    private const string DefaultFormat = "{0:HH:mm:ss}|{1}| {2}";
    private static readonly object Sync = new();
    private static ILoggerFactory _factory = NullLoggerFactory.Instance;
    private static bool _initialized;
    private static bool _logToFile;

    /// <summary>
    /// Create a project specific logger.
    /// </summary>
    public static ILogger ProjectLogger(string? filePath = null)
    {
        var name = "ibind" + (filePath != null ? $".{Path.GetFileNameWithoutExtension(filePath)}" : string.Empty);
        return _factory.CreateLogger(name);
    }

    /// <summary>
    /// Initialise the logging system.
    /// </summary>
    public static void Initialize(
        bool logToConsole = true,
        bool logToFile = false,
        LogLevel logLevel = LogLevel.Information,
        string? logsDirectory = null,
        bool printFileLogs = false)
    {
        if (_initialized) return;
        lock (Sync)
        {
            if (_initialized) return;
            _factory = LoggerFactory.Create(builder =>
            {
                builder.AddFilter((_, level) => level >= logLevel);
                if (logToConsole)
                {
                    builder.AddSimpleConsole(options =>
                    {
                        options.TimestampFormat = "HH:mm:ss|";
                        options.SingleLine = true;
                    });
                }
                if (logToFile)
                {
                    var path = Path.Combine(logsDirectory ?? Path.GetTempPath(), "ibind");
                    builder.AddProvider(new DailyFileLoggerProvider(path, DefaultFormat, printFileLogs));
                }
            });
            _logToFile = logToFile;
            _initialized = true;
        }
    }

    /// <summary>
    /// Create a new daily rotating file logger.
    /// </summary>
    public static ILogger NewDailyRotatingFileLogger(string loggerName, string filePath)
    {
        if (_logToFile && _factory is ILoggerFactory factory)
        {
            factory.AddProvider(new DailyFileLoggerProvider(filePath, DefaultFormat, false));
            return factory.CreateLogger($"ibind_fh.{loggerName}");
        }
        return NullLogger.Instance;
    }

    private sealed class DailyFileLoggerProvider : ILoggerProvider
    {
        private readonly string _basePath;
        private readonly string _format;
        private readonly bool _echo;
        private readonly object _sync = new();
        private StreamWriter _writer;
        private DateTime _currentDate;

        public DailyFileLoggerProvider(string basePath, string format, bool echo)
        {
            _basePath = basePath;
            _format = format;
            _echo = echo;
            _currentDate = DateTime.UtcNow.Date;
            Directory.CreateDirectory(Path.GetDirectoryName(basePath)!);
            _writer = CreateWriter();
        }

        public ILogger CreateLogger(string categoryName) => new DailyFileLogger(this);

        private StreamWriter CreateWriter()
        {
            var file = $"{_basePath}__{_currentDate:yyyy-MM-dd}.txt";
            return new StreamWriter(File.Open(file, FileMode.Append, FileAccess.Write, FileShare.Read));
        }

        internal void Write(string message)
        {
            lock (_sync)
            {
                if (DateTime.UtcNow.Date != _currentDate)
                {
                    _writer.Dispose();
                    _currentDate = DateTime.UtcNow.Date;
                    _writer = CreateWriter();
                }
                _writer.WriteLine(message);
                _writer.Flush();
            }
            if (_echo)
                Console.WriteLine(message);
        }

        public void Dispose()
        {
            lock (_sync)
            {
                _writer.Dispose();
            }
        }

        private sealed class DailyFileLogger : ILogger
        {
            private readonly DailyFileLoggerProvider _provider;

            public DailyFileLogger(DailyFileLoggerProvider provider)
            {
                _provider = provider;
            }

            IDisposable ILogger.BeginScope<TState>(TState state)
            {
                return NullScope.Instance;
            }

            bool ILogger.IsEnabled(LogLevel logLevel) => true;

            void ILogger.Log<TState>(LogLevel logLevel, EventId eventId, TState state, Exception? exception, Func<TState, Exception?, string> formatter)
            {
                var time = DateTime.UtcNow;
                var line = string.Format(_provider._format, time, logLevel.ToString()[0], formatter(state, exception));
                if (exception != null)
                    line += Environment.NewLine + exception;
                _provider.Write(line);
            }
        }

        private sealed class NullScope : IDisposable
        {
            public static NullScope Instance { get; } = new();
            public void Dispose() { }
        }
    }
}

