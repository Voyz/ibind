# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IBind is a Python library providing REST and WebSocket clients for the Interactive Brokers Client Portal Web API (CPAPI 1.0). It supports both traditional authentication via IBeam/CP Gateway and headless OAuth 1.0a authentication.

## Core Architecture

The library is structured around two main client classes:

### IbkrClient (REST API)
- **Location**: `ibind/client/ibkr_client.py`
- **Purpose**: REST API client extending `RestClient` base class
- **Mixins**: Functionality is organized into mixins in `ibind/client/ibkr_client_mixins/`:
  - `accounts_mixin.py` - Account operations
  - `contract_mixin.py` - Contract/security operations  
  - `marketdata_mixin.py` - Market data operations
  - `order_mixin.py` - Order management
  - `portfolio_mixin.py` - Portfolio operations
  - `scanner_mixin.py` - Market scanner
  - `session_mixin.py` - Session management
  - `watchlist_mixin.py` - Watchlist operations

### IbkrWsClient (WebSocket API)
- **Location**: `ibind/client/ibkr_ws_client.py`
- **Purpose**: WebSocket client for real-time data streams
- **Features**: Subscription management, queue-based data access, thread lifecycle handling

### Base Components
- `ibind/base/` - Core infrastructure classes:
  - `rest_client.py` - Base REST client with retry logic, session management
  - `ws_client.py` - Base WebSocket client
  - `queue_controller.py` - Thread-safe queue management
  - `subscription_controller.py` - WebSocket subscription handling

### Authentication
- `ibind/oauth/` - OAuth 1.0a implementation for headless authentication
- Environment variable configuration via `ibind/var.py`

## Development Commands

### Setup
```bash
# Install dependencies
make install
# OR manually:
pip install -r requirements.txt
pip install -r requirements-oauth.txt  # For OAuth support
pip install -r requirements-dev.txt    # For development
```

### Code Quality
```bash
make lint          # Run ruff linting with auto-fix
make scan          # Run bandit security checks
make check-all     # Run all checks (lint, scan, format)
```

### Testing
```bash
make test          # Run all tests
```

### Formatting
```bash
make format        # Format code using ruff
```

### Cleanup
```bash
make clean         # Remove Python cache files
```

## Key Configuration

### Linting Rules (pyproject.toml)
- Uses ruff for linting and formatting
- Line length: 150 characters
- Single quotes for strings
- Specific rule ignores for legacy code (E501, PLR2004, etc.)

### Environment Variables
Key environment variables are defined in `ibind/var.py`:
- `IBIND_ACCOUNT_ID` - IBKR account identifier
- `IBIND_REST_URL` - REST API base URL
- `IBIND_CACERT` - SSL certificate path
- `IBIND_USE_OAUTH` - Enable OAuth authentication
- `IBIND_USE_SESSION` - Use persistent HTTP sessions

## Testing Structure

Tests are organized in `test/` directory:
- `unit/` - Unit tests for individual components
- `integration/` - Integration tests with mocked IBKR responses
- `e2e/` - End-to-end tests (require live IBKR connection)

## Examples

The `examples/` directory contains comprehensive usage examples:
- `rest_*.py` - REST API examples (basic to advanced)
- `ws_*.py` - WebSocket API examples

## Important Notes

- The library supports both OAuth 1.0a (headless) and traditional CP Gateway authentication
- WebSocket client requires careful lifecycle management (start/stop, subscription handling)
- Rate limiting and parallel request handling are built into the REST client
- All API endpoints follow IBKR's REST API documentation structure
- Environment variables can be configured via `.env` files (auto-patched via `patch_dotenv()`)