# API Reference Table of Contents

## Core REST Client
- [REST Client](./ibkr_client.md) - Main IBKR REST API client and base classes

## WebSocket Client
- [WebSocket Client](./ibkr_ws_client.md) - IBKR WebSocket client implementation
- [WebSocket Events](./ibkr_ws_events.md) - Event definitions for WebSocket subscriptions
- [WebSocket Subscriptions](./ibkr_ws_subscriptions.md) - Subscription management
- [WebSocket Sinks](./ibkr_ws_sinks.md) - Data sink implementations

## Utilities
- [Utils](./utils.md) - Utility functions and helpers

## REST Client Mixins (IbkrClient)

The IbkrClient class is organized into functional mixins, each handling a specific domain of the IBKR API:

- [Accounts Mixin](./ibkr_client/accounts_mixin.md) - Account management and information
- [Contract Mixin](./ibkr_client/contract_mixin.md) - Contract and instrument definitions
- [Financial Advisor Mixin](./ibkr_client/fa_mixin.md) - Financial advisor features
- [Market Data Mixin](./ibkr_client/marketdata_mixin.md) - Real-time market data and quotes
- [Order Mixin](./ibkr_client/order_mixin.md) - Order placement and management
- [Portfolio Mixin](./ibkr_client/portfolio_mixin.md) - Portfolio and position management
- [Scanner Mixin](./ibkr_client/scanner_mixin.md) - Market scanner functionality
- [Session Mixin](./ibkr_client/session_mixin.md) - Session and authentication management
- [Watchlist Mixin](./ibkr_client/watchlist_mixin.md) - Watchlist management
