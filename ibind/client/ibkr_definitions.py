"""
This file contains hard coded definitions of what various IBKR market data snapshot fields stand for.
See: https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#market-data-fields
"""
from typing import Union

snapshot_by_key = {
    # Contract
    'symbol': '55',  # Symbol
    'conid': '6008',  # Conid - Contract identifier from IBKR's database.
    'sec_type': '6070',  # SecType - The asset class of the instrument.
    'underlying_conid': '6457',  # Underlying Conid. Use /trsrv/secdef to get more information about the security
    'market_data_availability': '6509',  # Market Data Availability. The field may contain three chars. First char defines: R = RealTime, D = Delayed, Z = Frozen, Y = Frozen Delayed, N = Not Subscribed. Second char defines: P = Snapshot, p = Consolidated. Third char defines: B = Book
    'conid_exchange': '7094',  # Conid + Exchange

    ##Regulator snapshot
    'ask_codes': '7057',  # Returns the series of character codes for the Ask exchange.

    'bid_codes': '7068',  # Returns the series of character codes for the Bid exchange.

    'last_exch_codes': '7058',  # Returns the series of character codes for the Last exchange.

    # Price and Volume
    'open': '7295',  # Open - Today's opening price.
    'high': '70',  # High - Current day high price
    'low': '71',  # Low - Current day low price
    'close': '7296',  # Close - Today's closing price.
    'last_price': '31',  # Last Price - The last price at which the contract traded. May contain one of the following prefixes: C - Previous day's closing price. H - Trading has halted.
    'bid_price': '84',  # Bid Price - The highest-priced bid on the contract.
    'ask_price': '86',  # Ask Price - The lowest-priced offer on the contract.
    'last_size': '7059',  # Last Size - The number of unites traded at the last price.
    'bid_size': '88',  # Bid Size - The number of contracts or shares bid for at the bid price. For US stocks, the number displayed is divided by 100.
    'ask_size': '85',  # Ask Size - The number of contracts or shares offered at the ask price. For US stocks, the number displayed is divided by 100.
    'prior_close': '7741',  # Prior Close - Yesterday's closing price
    'mark_price': '7635',  # Mark - The mark price is, the ask price if ask is less than last price, the bid price if bid is more than the last price, otherwise it's equal to last price.
    'volume': '87',  # Volume - Volume for the day, formatted with 'K' for thousands or 'M' for millions. For higher precision volume refer to field 7762.
    'volume_long': '7762',  # Volume Long - High precision volume for the day. For formatted volume refer to field 87.
    'change': '82',  # Change - The difference between the last price and the close on the previous trading day
    'change_since_open': '7682',  # Change Since Open - The difference between the last price and the open price.
    'change_percent': '83',  # Change % - The difference between the last price and the close on the previous trading day in percentage.

    # Volatility
    'implied_vol_hist_vol_percent': '7084',  # Implied Vol./Hist. Vol % - The ratio of the implied volatility over the historical volatility, expressed as a percentage.
    'hist_vol_close_percent': '7088',  # Hist. Vol. Close % - Shows the historical volatility based on previous close price.
    'spx_delta': '7696',  # SPX Delta - Beta Weighted Delta is calculated using the formula; Delta x dollar adjusted beta, where adjusted beta is adjusted by the ratio of the close price.
    'beta': '7718',  # Beta - Beta is against standard index.

    # Financial Information
    'hist_vol_percent': '7087',  # Hist. Vol. % - 30-day real-time historical volatility.
    'average_volume_90': '7282',  # Average Volume - The average daily trading volume over 90 days.
    'dividend_amount': '7286',  # Dividend Amount - Displays the amount of the next dividend.
    'dividend_yield_percent': '7287',  # Dividend Yield % - This value is the total of the expected dividend payments over the next twelve months per share divided by the Current Price and is expressed as a percentage. For derivatives, this displays the total of the expected dividend payments over the expiry date.
    'ex_date_dividend': '7288',  # Ex-date of the dividend
    'market_cap': '7289',  # Market Cap
    'p_e': '7290',  # P/E
    'eps': '7291',  # EPS
    '52_week_high': '7293',  # 52 Week High - The highest price for the past 52 weeks.
    '52_week_low': '7294',  # 52 Week Low - The lowest price for the past 52 weeks.
    'ema_200': '7674',  # EMA(200) - Exponential moving average (N=200).
    'ema_100': '7675',  # EMA(100) - Exponential moving average (N=100).
    'ema_50': '7676',  # EMA(50) - Exponential moving average (N=50).
    'ema_20': '7677',  # EMA(20) - Exponential moving average (N=20).
    'price_to_ema_200_percent': '7678',  # Price/EMA(200) - Price to Exponential moving average (N=200) ratio -1, displayed in percents.
    'price_to_ema_100_percent': '7679',  # Price/EMA(100) - Price to Exponential moving average (N=100) ratio -1, displayed in percents.
    'price_to_ema_50_percent': '7680',  # Price/EMA(50) - Price to Exponential moving average (N=50) ratio -1, displayed in percents.
    'price_to_ema_20_percent': '7681',  # Price/EMA(20) - Price to Exponential moving average (N=20) ratio -1, displayed in percents.

    # Portfolio
    'market_value': '73',  # Market Value - The current market value of your position in the security. Market Value is calculated with real-time market data (even when not subscribed to market data).
    'avg_price': '74',  # Avg Price - The average price of the position.
    'unrealized_pnl': '75',  # Unrealized PnL - Unrealized profit or loss. Unrealized PnL is calculated with real-time market data (even when not subscribed to market data).
    'formatted_position': '76',  # Formatted position
    'formatted_unrealized_pnl': '77',  # Formatted Unrealized PnL
    'daily_pnl': '78',  # Daily PnL - Your profit or loss of the day since prior close. Daily PnL is calculated with real-time market data (even when not subscribed to market data).
    'realized_pnl': '79',  # Realized PnL - Realized profit or loss. Realized PnL is calculated with real-time market data (even when not subscribed to market data).
    'unrealized_pnl_percent': '80',  # Unrealized PnL % - Unrealized profit or loss expressed in percentage.
    'daily_pnl_raw': '7920',  # Daily PnL Raw - Your profit or loss of the day since prior close. Daily PnL is calculated with real-time market data (even when not subscribed to market data).
    'cost_basis_raw': '7921',  # Cost Basis Raw - Your current position in this security multiplied by the average price and multiplier.
    'cost_basis': '7292',  # Cost Basis - Your current position in this security multiplied by the average price and multiplier.

    # Company and Industry Information
    'company_name': '7051',  # Company name
    'exchange': '6004',  # Exchange
    'listing_exchange': '7221',  # Listing Exchange
    'industry': '7280',  # Industry - Displays the type of industry under which the underlying company can be categorized.
    'category': '7281',  # Category - Displays a more detailed level of description within the industry under which the underlying company can be categorized.
    'ratings': '7706',  # Ratings - Ratings issued for bond contract.
    'bond_state_code': '7707',  # Bond State Code
    'bond_type': '7708',  # Bond Type
    'last_trading_date': '7714',  # Last Trading Date
    'issue_date': '7715',  # Issue Date
    'organization_type': '7704',  # Organization Type
    'debt_class': '7705',  # Debt Class

    # Options and Futures
    'opt_volume': '7089',  # Opt. Volume - Option Volume
    'put_call_ratio': '7285',  # Put/Call Ratio
    'option_open_interest': '7638',  # Option Open Interest
    'percent_of_mark_value': '7639',  # % of Mark Value - Displays the market value of the contract as a percentage of the total market value of the account. Mark Value is calculated with real-time market data (even when not subscribed to market data).
    'probability_of_max_return': '7694',  # Probability of Max Return - Customer implied probability of maximum potential gain.
    'break_even': '7695',  # Break Even - Break even points
    'probability_of_max_loss': '7702',  # Probability of Max Loss - Customer implied probability of maximum potential loss.
    'profit_probability': '7703',  # Profit Probability - Customer implied probability of any gain.
    'last_yield': '7698',  # Last Yield - Implied yield of the bond if it is purchased at the current last price. Last yield is calculated using the Last price on all possible call dates. It is assumed that prepayment occurs if the bond has call or put provisions and the issuer can offer a lower coupon rate based on current market rates. The yield to worst will be the lowest of the yield to maturity or yield to call (if the bond has prepayment provisions). Yield to worse may be the same as yield to maturity but never higher.
    'bid_yield': '7699',  # Bid Yield - Implied yield of the bond if it is purchased at the current bid price. Bid yield is calculated using the Ask on all possible call dates. It is assumed that prepayment occurs if the bond has call or put provisions and the issuer can offer a lower coupon rate based on current market rates. The yield to worst will be the lowest of the yield to maturity or yield to call (if the bond has prepayment provisions). Yield to worse may be the same as yield to maturity but never higher.
    'futures_open_interest': '7697',  # Futures Open Interest - Total number of outstanding futures contracts
    'put_call_interest': '7085',  # Put/Call Interest - Put option open interest/call option open interest for the trading day.
    'put_call_volume': '7086',  # Put/Call Volume - Put option volume/call option volume for the trading day.
    'option_implied_vol_percent': '7283',  # Option Implied Vol. % - A prediction of how volatile an underlying will be in the future. At the market volatility estimated for a maturity thirty calendar days forward of the current trading day, and based on option prices from two consecutive expiration months. To query the Implied Vol. % of a specific strike refer to field 7633.
    'delta': '7308',  # Delta - The ratio of the change in the price of the option to the corresponding change in the price of the underlying.
    'gamma': '7309',  # Gamma - The rate of change for the delta with respect to the underlying asset’s price.
    'theta': '7310',  # Theta - A measure of the rate of decline the value of an option due to the passage of time.
    'vega': '7311',  # Vega - The amount that the price of an option changes compared to a 1% change in the volatility.
    'implied_vol_percent': '7633',  # Implied Vol. % - The implied volatility for the specific strike of the option in percentage. To query the Option Implied Vol. % from the underlying refer to field 7283.

    # Wall Street Horizon
    'upcoming_event': '7683',  # Upcoming Event - Shows the next major company event. Requires Wall Street Horizon subscription.
    'upcoming_event_date': '7684',  # Upcoming Event Date - The date of the next major company event. Requires Wall Street Horizon subscription.
    'upcoming_analyst_meeting': '7685',  # Upcoming Analyst Meeting - The date and time of the next scheduled analyst meeting. Requires Wall Street Horizon subscription.
    'upcoming_earnings': '7686',  # Upcoming Earnings - The date and time of the next scheduled earnings/earnings call event. Requires Wall Street Horizon subscription.
    'upcoming_misc_event': '7687',  # Upcoming Misc Event - The date and time of the next shareholder meeting, presentation, or other event. Requires Wall Street Horizon subscription.
    'recent_analyst_meeting': '7688',  # Recent Analyst Meeting - The date and time of the most recent analyst meeting. Requires Wall Street Horizon subscription.
    'recent_earnings': '7689',  # Recent Earnings - The date and time of the most recent earnings/earning call event. Requires Wall Street Horizon subscription.
    'recent_misc_event': '7690',  # Recent Misc Event - The date and time of the most recent shareholder meeting, presentation, or other event. Requires Wall Street Horizon subscription.

    # Miscellaneous
    'shortable': '7644',  # Shortable - Describes the level of difficulty with which the security can be sold short.
    'service_params': '6508',  # Service Params.
    'market_data_marker': '6119',  # Marker for market data delivery method (similar to request id)
    'months': '6072',  # Months
    'regular_expiry': '6073',  # Regular Expiry
    'has_trading_permissions': '7768',  # hasTradingPermissions - if the user has trading permissions for the specified contract. Returns 1(true) or 0(false).
    'server_id': 'string',
    'conid_str': 'integer_str',
    '_updated_str': 'integer_str',
}

snapshot_by_id = {str(value): key for key, value in snapshot_by_key.items()}


def snapshot_ids_to_keys(ids: [Union[str, int]]):  # pragma: no cover
    """
    Converts a list of IBKR market data field IDs to their corresponding human-readable keys.

    Parameters:
        ids (list[Union[str, int]]): A list of numeric field IDs, as strings or integers.

    Returns:
        list[str]: A list of human-readable field keys.

    Example:
        >>> snapshot_ids_to_keys(["55", 6008])
        ["symbol", "conid"]

    Raises:
        KeyError: If an invalid field ID is provided.

    See:
        - `snapshot_by_id`: Dictionary mapping IBKR market data field IDs to human-readable keys.
    """
    return [snapshot_by_id[str(idx)] for idx in ids]


def snapshot_keys_to_ids(keys: [str]):  # pragma: no cover
    """
    Converts a list of human-readable IBKR market data field keys to their corresponding numeric field IDs.

    Parameters:
        keys (list[str]): A list of human-readable field keys.

    Returns:
        list[str]: A list of numeric field IDs.

    Example:
        >>> snapshot_keys_to_ids(["symbol", "conid"])
        ["55", "6008"]

    Raises:
        KeyError: If an invalid field key is provided.

    See:
        - `snapshot_by_key`: Dictionary mapping human-readable keys to IBKR market data field IDs.
    """
    return [snapshot_by_key[key] for key in keys]


data_availability_by_key = {
    'S': 'Streaming',
    'R': 'Realtime',
    'D': 'Delayed',
    'Z': 'Frozen',
    'Y': 'Frozen Delayed',
    'P': 'Snapshot Available',
    'p': 'Consolidated',
}


def decode_data_availability(md_availability: [str]):
    """
    Decodes a list of market data availability codes into human-readable descriptions.

    The availability string may contain multiple characters indicating different states:
    - 'S': Streaming
    - 'R': Realtime
    - 'D': Delayed
    - 'Z': Frozen
    - 'Y': Frozen Delayed
    - 'P': Snapshot Available
    - 'p': Consolidated

    Parameters:
        md_availability (list[str]): A list of market data availability codes.

    Returns:
        str: A human-readable description of the market data availability.

    Example:
        >>> decode_data_availability(["S", "R"])
        "Streaming, Realtime"

    Raises:
        KeyError: If an invalid availability code is provided.

    See:
        - `data_availability_by_key`: Dictionary mapping availability codes to human-readable descriptions.
    """
    return ", ".join([data_availability_by_key[c] for c in md_availability])
