# Table of Contents

* [watchlist\_mixin](#client.ibkr_client_mixins.watchlist_mixin)
  * [WatchlistMixin](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin)
    * [create\_watchlist](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.create_watchlist)
    * [get\_all\_watchlists](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_all_watchlists)
    * [get\_watchlist\_information](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_watchlist_information)
    * [delete\_watchlist](#client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.delete_watchlist)

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin"></a>

## WatchlistMixin

https://ibkrcampus.com/ibkr-api-page/cpapi-v1/#watchlists

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.create_watchlist"></a>

### create\_watchlist

```python
def create_watchlist(id: str, name: str,
                     rows: List[Dict[str, Union[str, int]]]) -> Result
```

Create a watchlist to monitor a series of contracts.

Arguments:

- `id` _str_ - Supply a unique identifier to track a given watchlist. Must supply a number.
- `name` _str_ - Supply the human readable name of a given watchlist. Displayed in TWS and Client Portal.
- `rows` _List[Dict[str, Union[str, int]]]_ - Provide details for each contract or blank space in the watchlist. Each object may include:
  - C (int): Provide the conid, or contract identifier, of the conid to add.
  - H (str): Can be used to add a blank row between contracts in the watchlist.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_all_watchlists"></a>

### get\_all\_watchlists

```python
def get_all_watchlists(sc: str = 'USER_WATCHLIST') -> Result
```

Retrieve a list of all available watchlists for the account.

Arguments:

- `SC` _str_ - Optional. Specify the scope of the request. Valid Values: USER_WATCHLIST.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.get_watchlist_information"></a>

### get\_watchlist\_information

```python
def get_watchlist_information(id: str) -> Result
```

Request the contracts listed in a particular watchlist.

Arguments:

- `id` _str_ - Set equal to the watchlist ID you would like data for.

<a id="client.ibkr_client_mixins.watchlist_mixin.WatchlistMixin.delete_watchlist"></a>

### delete\_watchlist

```python
def delete_watchlist(id: str) -> Result
```

Permanently delete a specific watchlist for all platforms.

Arguments:

- `id` _str_ - Include the watchlist ID you wish to delete.
