# Table of Contents

* [accounts\_mixin](#client.ibkr_client_mixins.accounts_mixin)
  * [AccountsMixin](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin)
    * [account\_summary](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_summary)
    * [account\_profit\_and\_loss](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_profit_and_loss)
    * [search\_dynamic\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.search_dynamic_account)
    * [set\_dynamic\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.set_dynamic_account)
    * [signatures\_and\_owners](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.signatures_and_owners)
    * [switch\_account](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.switch_account)
    * [receive\_brokerage\_accounts](#client.ibkr_client_mixins.accounts_mixin.AccountsMixin.receive_brokerage_accounts)

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin"></a>

## AccountsMixin

https://www.interactivebrokers.com/docs/web-api/v1/endpoints/accounts

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_summary"></a>

### account\_summary

```python
def account_summary(account_id: str = None) -> Result
```

Returns a summary of the account's information.

Arguments:

- `account_id` _str_ - The account identifier. If not provided, the active account is used.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.account_profit_and_loss"></a>

### account\_profit\_and\_loss

```python
def account_profit_and_loss() -> Result
```

Returns an object containing PnL for the selected account and its models (if any).

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.search_dynamic_account"></a>

### search\_dynamic\_account

```python
def search_dynamic_account(search_pattern: str) -> Result
```

Searches for broker accounts configured with the DYNACCT property using a specified pattern.

Arguments:

- `search_pattern` _str_ - The pattern used to describe credentials to search for. Valid Format: �DU� in order to query all paper accounts.
  

Notes:

  - Customers without the DYNACCT property will receive the following 503 message: "Details currently unavailable. Please try again later and contact client services if the issue persists."

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.set_dynamic_account"></a>

### set\_dynamic\_account

```python
def set_dynamic_account(account_id: str) -> Result
```

Set the active dynamic account. Values retrieved from Search Dynamic Account.

Arguments:

- `account_id` _str_ - The account ID that should be set for future requests.
  

Notes:

  - If the account does not have the DYNACCT property, a 503 error message is returned.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.signatures_and_owners"></a>

### signatures\_and\_owners

```python
def signatures_and_owners(account_id: str = None) -> Result
```

Receive a list of all applicant names on the account and for which account and entity is represented.

Arguments:

- `account_id` _str_ - Pass the account identifier to receive information for. Valid Structure: �U1234567�.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.switch_account"></a>

### switch\_account

```python
def switch_account(account_id: str) -> Result
```

Switch the active account for how you request data.

Only available for financial advisors and multi-account structures.

Arguments:

- `acctId` _str_ - Identifier for the unique account to retrieve information from. Value Format: �DU1234567�.

<a id="client.ibkr_client_mixins.accounts_mixin.AccountsMixin.receive_brokerage_accounts"></a>

### receive\_brokerage\_accounts

```python
def receive_brokerage_accounts() -> Result
```

Returns a list of accounts the user has trading access to, their respective aliases, and the currently selected account. Note this endpoint must be called before modifying an order or querying open orders.
