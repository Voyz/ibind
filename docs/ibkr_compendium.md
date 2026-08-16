# IBKR Compendium

This page is an unofficial, user-contributed compendium of knowledge regarding IBKR. It is created in order to store and share knowledge regarding IBKR that isn't categorised in other sections of this WiKi. Please be aware that this information is provided as a community effort, and it is advisable to verify its truthfulness.

It is likely that over time the information presented here will become stale. We'll try to indicate the date around which the information was added or updated.

If you have information that could be added, or a correction that could be made to the existing entry, please [create a new issue][issues].

## Currency conversion restrictions

_Feb 2025_

Currency conversion seems to be fine, as long as it is related to an investment. Depositing, converting and withdrawing immediately seem to flag the account for restriction.

From IBKR support agent :

> you can convert currency if the proceeds are going to be used to open a position in any financial investment or you can convert currency from any proceeds from an investment

> you cannot make a deposit > convert the currency > withdraw the funds

> if the system detects that your account may be restricted

It is meant to take up to 2 business days for the currency conversion to be settled. _Mar 2025_

## Subaccounts for Institutional Accounts

_Feb 2025_

For institutional accounts (also known as Organization), adding a subaccount is not an option. Instead, 'Account Partitions' are the alternative to opening a subaccounts.

From IBKR support agent:

> The add account options are mainly for individual account holders

> When logged into your ORG account, you should see 'Add trading Partition' on the Home screen

> This will create a Separate trading Limit Structure under the Organization. This would be a sub account which is self contained.

> You can also transfer cash and positions internally between the accounts.

> There would not be any difference to how you normally trade. You will be able to see both accounts on the TWS and would be able to chose which account to place a trade on.


## Contacting IBKR Support

_Nov 2025_

IBKR seems to only keep 7 days worth of logs on their end. Report issues fast and urge them to act.

From IBKR support agent:

> I understand this connectivity issue is impacting your ability to use the Client Portal Gateway effectively.
>
> Unfortunately, I'm unable to investigate this specific error at this time because our system logs are only preserved for 7 days.
>
> To help resolve your connectivity issue going forward, I'd recommend to either try reproducing the error to generate a fresh error reference within our log retention period or wait until it appears again
>
> If the Issue persists - contact our support team immediately when you encounter the error again so we can investigate while the logs are still available.
>
> I apologize for any inconvenience this limitation may cause. Our log retention policy ensures system performance, but I understand it can complicate troubleshooting older issues. Please don't hesitate to reach out again if you encounter this problem with a more recent timestamp.

# Getting Weekly Options Contracts

IBKR's Web API returns options data hierarchically. The initial contract search returns only month-level granularity. To access sub-month granularity (weekly options), you must query a specific strike price, which returns all available contracts for that strike, including standard monthlies and weekly expirations.

#### Step 1: Search for the underlying contract
```python
contracts = client.search_contract_by_symbol('SPX').data
spx_contract = contracts[0]
```
#### Step 2: Extract the options section
```python
options = None
for section in spx_contract['sections']:
    if section['secType'] == 'OPT':
        options = section
        break
```
The contract includes multiple sections - extract the options-specific ones.

#### Step 3: Parse available months
```python
options['months'] = options['months'].split(';')
```
IBKR returns months and exchanges as semicolon-delimited strings. Split them into lists for easier access.

#### Step 4: Query available strikes for the desired month
```python
strikes = client.search_strikes_by_conid(
    conid=spx_contract['conid'], 
    sec_type='OPT', 
    month=options['months'][0]
).data
```
Returns all available strike prices for the given month. This is still month-level only, it does not yet show weekly vs. monthly distinctions.

#### Step 5: Query a specific strike to reveal sub-month granularity
```python
info = client.search_secdef_info_by_conid(
    conid=spx_contract['conid'], 
    sec_type='OPT', 
    month=options['months'][0], # Or specify the month you'd like to query, eg. 'APR26'
    strike=2600,  # Example strike price
    right='C'     # 'C' for call, 'P' for put
).data
```
Querying a specific strike price (eg. 2600) returns all contracts at that strike, including:
- Standard monthly expirations
- Weekly expirations (if available) - see `maturityDate` field

The `info` list will contain multiple rows-one per expiration date. Weekly options appear as additional rows beyond the standard monthly.

Example result:
```text
    conid   symbol   secType   exchange   listingExchange   right   strike   currency   cusip      coupon   desc1                         desc2   maturityDate   multiplier   tradingClass       validExchanges   showPrips
869076997      SPX       OPT      SMART                         C   2600.0        USD           No Coupon     SPX   (SPXW) APR 06 '26 2600 Call       20260406          100           SPXW   SMART,CBOE,IBUSOPT        True
869077649      SPX       OPT      SMART                         C   2600.0        USD           No Coupon     SPX   (SPXW) APR 07 '26 2600 Call       20260407          100           SPXW   SMART,CBOE,IBUSOPT        True
869078255      SPX       OPT      SMART                         C   2600.0        USD           No Coupon     SPX   (SPXW) APR 08 '26 2600 Call       20260408          100           SPXW   SMART,CBOE,IBUSOPT        True
...
```

Note:
- Month-level queries don't show weeklies - steps 1-4 return only month-level data.
- Strike-level queries reveal weeklies - step 5 is where weekly options become visible.
- Different strikes may have different weekly availability - some strikes may have only one contract returned.

[issues]: https://github.com/Voyz/ibind/issues
