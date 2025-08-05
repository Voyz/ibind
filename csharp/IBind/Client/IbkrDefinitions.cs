using System;
using System.Collections.Generic;
using System.Linq;

namespace IBind.Client;

/// <summary>
/// Hard coded IBKR market data snapshot field mappings and helpers.
/// Ported from ibind/client/ibkr_definitions.py
/// </summary>
public static class IbkrDefinitions
{
    /// <summary>
    /// Map of human readable snapshot keys to IBKR field identifiers.
    /// </summary>
    public static readonly IDictionary<string, string> SnapshotByKey = new Dictionary<string, string>
    {
        // Contract
        {"symbol", "55"}, // Symbol
        {"conid", "6008"}, // Contract identifier from IBKR's database.
        {"sec_type", "6070"}, // Asset class of the instrument.
        {"underlying_conid", "6457"}, // Underlying Conid
        {"market_data_availability", "6509"}, // Market Data Availability
        {"conid_exchange", "7094"}, // Conid + Exchange

        // Regulator snapshot
        {"ask_codes", "7057"}, // Series of character codes for the Ask exchange
        {"bid_codes", "7068"}, // Series of character codes for the Bid exchange
        {"last_exch_codes", "7058"}, // Series of character codes for the Last exchange

        // Price and Volume
        {"open", "7295"}, // Today's opening price
        {"high", "70"}, // Current day high price
        {"low", "71"}, // Current day low price
        {"close", "7296"}, // Today's closing price
        {"last_price", "31"}, // Last Price
        {"bid_price", "84"}, // Bid Price
        {"ask_price", "86"}, // Ask Price
        {"last_size", "7059"}, // Last Size
        {"bid_size", "88"}, // Bid Size
        {"ask_size", "85"}, // Ask Size
        {"prior_close", "7741"}, // Prior Close
        {"mark_price", "7635"}, // Mark price
        {"volume", "87"}, // Volume formatted
        {"volume_long", "7762"}, // High precision volume
        {"change", "82"}, // Difference between last and previous close
        {"change_since_open", "7682"}, // Difference between last and open price
        {"change_percent", "83"}, // Change percentage

        // Volatility
        {"implied_vol_hist_vol_percent", "7084"},
        {"hist_vol_close_percent", "7088"},
        {"spx_delta", "7696"},
        {"beta", "7718"},

        // Financial Information
        {"hist_vol_percent", "7087"},
        {"average_volume_90", "7282"},
        {"dividend_amount", "7286"},
        {"dividend_yield_percent", "7287"},
        {"ex_date_dividend", "7288"},
        {"market_cap", "7289"},
        {"p_e", "7290"},
        {"eps", "7291"},
        {"52_week_high", "7293"},
        {"52_week_low", "7294"},
        {"ema_200", "7674"},
        {"ema_100", "7675"},
        {"ema_50", "7676"},
        {"ema_20", "7677"},
        {"price_to_ema_200_percent", "7678"},
        {"price_to_ema_100_percent", "7679"},
        {"price_to_ema_50_percent", "7680"},
        {"price_to_ema_20_percent", "7681"},

        // Portfolio
        {"market_value", "73"},
        {"avg_price", "74"},
        {"unrealized_pnl", "75"},
        {"formatted_position", "76"},
        {"formatted_unrealized_pnl", "77"},
        {"daily_pnl", "78"},
        {"realized_pnl", "79"},
        {"unrealized_pnl_percent", "80"},
        {"daily_pnl_raw", "7920"},
        {"cost_basis_raw", "7921"},
        {"cost_basis", "7292"},

        // Company and Industry Information
        {"company_name", "7051"},
        {"exchange", "6004"},
        {"listing_exchange", "7221"},
        {"industry", "7280"},
        {"category", "7281"},
        {"ratings", "7706"},
        {"bond_state_code", "7707"},
        {"bond_type", "7708"},
        {"last_trading_date", "7714"},
        {"issue_date", "7715"},
        {"organization_type", "7704"},
        {"debt_class", "7705"},

        // Options and Futures
        {"opt_volume", "7089"},
        {"put_call_ratio", "7285"},
        {"option_open_interest", "7638"},
        {"percent_of_mark_value", "7639"},
        {"probability_of_max_return", "7694"},
        {"break_even", "7695"},
        {"probability_of_max_loss", "7702"},
        {"profit_probability", "7703"},
        {"last_yield", "7698"},
        {"bid_yield", "7699"},
        {"futures_open_interest", "7697"},
        {"shortable_shares", "7636"},
        {"put_call_interest", "7085"},
        {"put_call_volume", "7086"},
        {"option_implied_vol_percent", "7283"},
        {"delta", "7308"},
        {"gamma", "7309"},
        {"theta", "7310"},
        {"vega", "7311"},
        {"implied_vol_percent", "7633"},

        // Wall Street Horizon
        {"upcoming_event", "7683"},
        {"upcoming_event_date", "7684"},
        {"upcoming_analyst_meeting", "7685"},
        {"upcoming_earnings", "7686"},
        {"upcoming_misc_event", "7687"},
        {"recent_analyst_meeting", "7688"},
        {"recent_earnings", "7689"},
        {"recent_misc_event", "7690"},

        // Miscellaneous
        {"shortable", "7644"},
        {"service_params", "6508"},
        {"market_data_marker", "6119"},
        {"months", "6072"},
        {"regular_expiry", "6073"},
        {"has_trading_permissions", "7768"},
        {"server_id", "string"},
        {"conid_str", "integer_str"},
        {"_updated_str", "integer_str"},
    }; // fmt: skip

    /// <summary>
    /// Reverse mapping of snapshot identifiers to keys.
    /// </summary>
    public static readonly IDictionary<string, string> SnapshotById =
        SnapshotByKey.ToDictionary(kv => kv.Value, kv => kv.Key);

    public static List<string> SnapshotIdsToKeys(IEnumerable<object> ids)
        => ids.Select(id => SnapshotById[id.ToString()]).ToList();

    public static List<string> SnapshotKeysToIds(IEnumerable<string> keys)
        => keys.Select(key => SnapshotByKey[key]).ToList();

    public static readonly IDictionary<string, string> DataAvailabilityByKey = new Dictionary<string, string>
    {
        {"S", "Streaming"},
        {"R", "Realtime"},
        {"D", "Delayed"},
        {"Z", "Frozen"},
        {"Y", "Frozen Delayed"},
        {"P", "Snapshot Available"},
        {"p", "Consolidated"},
    };

    public static string DecodeDataAvailability(IEnumerable<string> mdAvailability)
        => string.Join(", ", mdAvailability.Select(c => DataAvailabilityByKey[c]));
}

