# Table of Contents

* [portfolio\_mixin](#client.ibkr_client_mixins.portfolio_mixin)
  * [PortfolioMixin](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin)
    * [portfolio\_accounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_accounts)
    * [portfolio\_subaccounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_subaccounts)
    * [large\_portfolio\_subaccounts](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.large_portfolio_subaccounts)
    * [portfolio\_account\_information](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_information)
    * [portfolio\_account\_allocation](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocation)
    * [portfolio\_account\_allocations](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocations)
    * [combination\_positions](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.combination_positions)
    * [positions](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions)
    * [positions2](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions2)
    * [positions\_by\_conid](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions_by_conid)
    * [invalidate\_backend\_portfolio\_cache](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.invalidate_backend_portfolio_cache)
    * [portfolio\_summary](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_summary)
    * [get\_ledger](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.get_ledger)
    * [position\_and\_contract\_info](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.position_and_contract_info)
    * [account\_performance](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.account_performance)
    * [all\_periods](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.all_periods)
    * [transaction\_history](#client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.transaction_history)

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin"></a>

## PortfolioMixin

* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#portfolio
* https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#pa

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_accounts"></a>

### portfolio\_accounts

```python
def portfolio_accounts() -> Result
```

In non-tiered account structures, returns a list of accounts for which the user can view position and account information. This endpoint must be called prior to calling other /portfolio endpoints for those accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_subaccounts"></a>

### portfolio\_subaccounts

```python
def portfolio_subaccounts() -> Result
```

Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of up to 100 sub-accounts for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.large_portfolio_subaccounts"></a>

### large\_portfolio\_subaccounts

```python
def large_portfolio_subaccounts(page: int = 0) -> Result
```

Used in tiered account structures (such as Financial Advisor and IBroker Accounts) to return a list of sub-accounts, paginated up to 20 accounts per page, for which the user can view position and account-related information. This endpoint must be called prior to calling other /portfolio endpoints for those sub-accounts.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_information"></a>

### portfolio\_account\_information

```python
def portfolio_account_information(account_id: str = None) -> Result
```

Account information related to account Id. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

Arguments:

- `account_id` _str, optional_ - Specify the AccountID to receive portfolio information for.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocation"></a>

### portfolio\_account\_allocation

```python
def portfolio_account_allocation(account_id: str = None) -> Result
```

Information about the account's portfolio allocation by Asset Class, Industry and Category. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.

Arguments:

- `account_id` _str, optional_ - Specify the account ID for the request.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_account_allocations"></a>

### portfolio\_account\_allocations

```python
@ensure_list_arg('account_ids')
def portfolio_account_allocations(account_ids: OneOrMany[str]) -> Result
```

Similar to /portfolio/{accountId}/allocation but returns a consolidated view of all the accounts returned by /portfolio/accounts.

Arguments:

- `account_ids` _OneOrMany[str]_ - Contains all account IDs as strings the user should receive data for.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.combination_positions"></a>

### combination\_positions

```python
def combination_positions(account_id: str = None,
                          no_cache: bool = False) -> Result
```

Provides all positions held in the account acquired as a combination, including values such as ratios, size, and market value.

Arguments:

- `account_id` _str, optional_ - The account ID for which account should place the order.
- `nocache` _bool, optional_ - Set if request should be made without caching. Defaults to false.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions"></a>

### positions

```python
def positions(account_id: str = None,
              page: int = 0,
              model: str = None,
              sort: str = None,
              direction: str = None,
              period: str = None) -> Result
```

Returns a list of positions for the given account. The endpoint supports paging, each page will return up to 100 positions.

Arguments:

- `account_id` _str, optional_ - The account ID for which account should place the order.
- `page_id` _str, optional_ - The �page� of positions that should be returned. One page contains a maximum of 100 positions. Pagination starts at 0.
- `model` _str, optional_ - Code for the model portfolio to compare against.
- `sort` _str, optional_ - Declare the table to be sorted by which column.
- `direction` _str, optional_ - The order to sort by. 'a' means ascending 'd' means descending.
- `period` _str, optional_ - Period for pnl column. Value Format: 1D, 7D, 1M.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions2"></a>

### positions2

```python
def positions2(account_id: str = None,
               model: str = None,
               sort: str = None,
               direction: str = None) -> Result
```

Returns a list of positions for the given account.
/portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint.
This endpoint provides near-real time updates and removes caching otherwise found in the /portfolio/{accountId}/positions/{pageId} endpoint.

Arguments:

- `account_id` _str, optional_ - The account ID for which account should place the order.
- `model` _str, optional_ - Code for the model portfolio to compare against.
- `sort` _str, optional_ - Declare the table to be sorted by which column.
- `direction` _str, optional_ - The order to sort by. 'a' means ascending 'd' means descending.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.positions_by_conid"></a>

### positions\_by\_conid

```python
def positions_by_conid(account_id: str, conid: str) -> Result
```

Returns a list containing position details only for the specified conid.

Arguments:

- `account_id` _str_ - The account ID for which account should place the order.
- `conid` _str_ - The contract ID to receive position information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.invalidate_backend_portfolio_cache"></a>

### invalidate\_backend\_portfolio\_cache

```python
def invalidate_backend_portfolio_cache(account_id: str = None) -> Result
```

Invalidates the cached value for your portfolio�s positions and calls the /portfolio/{accountId}/positions/0 endpoint automatically.

Arguments:

- `account_id` _str_ - The account ID for which cache to invalidate.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.portfolio_summary"></a>

### portfolio\_summary

```python
def portfolio_summary(account_id: str = None) -> Result
```

Information regarding settled cash, cash balances, etc. in the account�s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

Arguments:

- `account_id` _str_ - Specify the account ID for which account you require ledger information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.get_ledger"></a>

### get\_ledger

```python
def get_ledger(account_id: str = None) -> Result
```

Information regarding settled cash, cash balances, etc. in the account�s base currency and any other cash balances hold in other currencies. /portfolio/accounts or /portfolio/subaccounts must be called prior to this endpoint. The list of supported currencies is available at https://www.interactivebrokers.com/en/index.php?f=3185.

Arguments:

- `account_id` _str_ - Specify the account ID for which account you require ledger information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.position_and_contract_info"></a>

### position\_and\_contract\_info

```python
def position_and_contract_info(conid: str) -> Result
```

Returns an object containing information about a given position along with its contract details.

Arguments:

- `conid` _str_ - The contract ID to receive position information on.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.account_performance"></a>

### account\_performance

```python
@ensure_list_arg('account_ids')
def account_performance(account_ids: OneOrMany[str], period: str) -> Result
```

Returns the performance (MTM) for the given accounts, if more than one account is passed, the result is consolidated.

Arguments:

- `account_ids` _OneOrMany[str]_ - Include each account ID to receive data for.
- `period` _str_ - Specify the period for which the account should be analyzed. Available Values: �1D�, �7D�, �MTD�, �1M�, �YTD�, �1Y�.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.all_periods"></a>

### all\_periods

```python
@ensure_list_arg('account_ids')
def all_periods(account_ids: OneOrMany[str]) -> Result
```

Returns the performance across all available time periods for the given accounts, if more than one account is passed, the result is consolidated.

Arguments:

- `account_ids` _OneOrMany[str]_ - Include each account ID to receive data for.

<a id="client.ibkr_client_mixins.portfolio_mixin.PortfolioMixin.transaction_history"></a>

### transaction\_history

```python
@ensure_list_arg('account_ids', 'conids')
def transaction_history(account_ids: OneOrMany[str],
                        conids: OneOrMany[str],
                        currency: str,
                        days: int = None) -> Result
```

Transaction history for a given number of conids and accounts. Types of transactions include dividend payments, buy and sell transactions, transfers.

Arguments:

- `account_ids` _OneOrMany[str]_ - Include each account ID to receive data for.
- `conids` _OneOrMany[str]_ - Include contract ID to receive data for. Only supports one contract id at a time.
- `currency` _str_ - Define the currency to display price amounts with. Defaults to USD.
- `days` _str, optional_ - Specify the number of days to receive transaction data for. Defaults to 90 days of transaction history if unspecified.
