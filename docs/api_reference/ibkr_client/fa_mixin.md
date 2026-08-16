# Table of Contents

* [fa\_mixin](#client.ibkr_client_mixins.fa_mixin)
  * [FaMixin](#client.ibkr_client_mixins.fa_mixin.FaMixin)
    * [fa\_model\_list](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_list)
    * [fa\_model\_positions](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_positions)
    * [fa\_model\_summary](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_summary)
    * [fa\_model\_accounts\_details](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_accounts_details)
    * [fa\_model\_save](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_save)
    * [fa\_model\_invest\_divest](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_invest_divest)
    * [fa\_model\_invest\_divest\_positions](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_invest_divest_positions)
    * [fa\_model\_submit\_transfers](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_submit_transfers)
    * [fa\_preset\_get](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_preset_get)
    * [fa\_preset\_save](#client.ibkr_client_mixins.fa_mixin.FaMixin.fa_preset_save)

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin"></a>

## FaMixin

Financial Advisor model portfolio endpoints ('Trading FA Allocation Management').

* https://www.interactivebrokers.com/campus/ibkr-api-page/web-api/

Covers the `/fa/model/*` and `/fa/fa-preset/*` endpoint group, allowing Financial Advisor accounts to
list, create, rebalance and monitor model portfolios programmatically.

Notes:

  - These endpoints are defined in IBKR's Web API OpenAPI specification (served from
  https://api.ibkr.com/gw/api/v3/api-docs) under the 'Trading FA Allocation Management' tag.
  IBind requests them relative to the client's regular base URL (e.g. `https://api.ibkr.com/v1/api/`),
  consistent with all other endpoint mixins - verified against a live FA account.
  - Several of these endpoints include `subscriptionStatus` fields suggesting asynchronous delivery;
  in live testing however, `invest-divest` returned its transfer draft synchronously rather than
  via a WebSocket push.
  - The `/fa/model/*` endpoints do not validate model names: an unknown or wrong-case model name
  returns empty 'ghost' data (zero NLV, no accounts) with no error, rather than a 404. Model names
  are case-sensitive in effect - resolve them against `fa_model_list` before use.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_list"></a>

### fa\_model\_list

```python
def fa_model_list(req_id: int) -> Result
```

POST /fa/model/list

Retrieve summaries for all models under the advisor account.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_positions"></a>

### fa\_model\_positions

```python
def fa_model_positions(req_id: int,
                       model: str,
                       sort_field: str = None,
                       sort_direction: str = None,
                       limit: int = None) -> Result
```

POST /fa/model/positions

Request all positions held within the model.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Name of your model.
- `sort_field` _str, optional_ - Field to sort the response by. Available values: 'actual', 'actualRangeMax', 'actualRangeMin', 'ccy', 'conid', 'dlv', 'instrumentImbalance', 'instrument', 'mismatchType', 'mv', 'position', 'target'.
- `sort_direction` _str, optional_ - Direction to sort the request by. Available values: 'ASC', 'DESC'.
- `limit` _int, optional_ - Maximum number of positions to return.
  

Notes:

  - Allocation values in the response (`target`, `actual`, `actualRangeMin`/`actualRangeMax`,
  `instrumentImbalance`) are fractions in [0, 1], not percentages as IBKR's specification
  describes (observed against a live FA account) - consistent with the targets accepted
  by `fa_model_save`.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_summary"></a>

### fa\_model\_summary

```python
def fa_model_summary(req_id: int, model: str) -> Result
```

POST /fa/model/summary

Request a summary for a single model.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Name of your model.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_accounts_details"></a>

### fa\_model\_accounts\_details

```python
def fa_model_accounts_details(req_id: int,
                              model: str,
                              calc_pnls: bool = None) -> Result
```

POST /fa/model/accounts-details

Request all accounts held within a model.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Request model to pull account details from.
- `calc_pnls` _bool, optional_ - Determine if Profit and Loss values should be calculated.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_save"></a>

### fa\_model\_save

```python
def fa_model_save(req_id: int, model: str, desc: str, is_static: bool,
                  cash_targets: List[Dict],
                  position_targets: List[Dict]) -> Result
```

POST /fa/model/save

Create or Modify a model's target positions.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Name of your model.
- `desc` _str_ - Personal description of model to read in IBKR GUI elements.
- `is_static` _bool_ - Determine if investing and rebalancing should be handled statically or dynamically. Set to True for static models that always use the original targets, or False for dynamic models that adjust allocation in response to market movements.
- `cash_targets` _List[Dict]_ - Array of target cash objects. Each object may include:
  - ccy (str): Currency code to hold positions.
  - target (float): Fraction of the model to allocate to the given currency, in [0, 1].
- `position_targets` _List[Dict]_ - List containing all contracts to hold in the model. Each object may include:
  - conid (int): Contract identifier, conid, to designate which security to hold.
  - target (float): Fraction of the model to allocate to the given contract, in [0, 1].
  

Notes:

  The following behaviors were observed against a live FA account and differ from or extend IBKR's specification:
  
  - `target` values are fractions in [0, 1] and must sum to 1.0 across cash_targets and position_targets
  combined. IBKR's OpenAPI schema describes them as percentages, but 0-100 values are rejected with a 400.
  - Omitting `desc` results in a bare 400 response with no body.
  - `is_static` cannot be changed on a model that already has invested accounts (400) - use the IBKR GUI instead.
  - On an invested dynamic model, a save can succeed silently with no effect. Read the targets back
  (`fa_model_list` / `fa_model_positions`) to verify the save took effect.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_invest_divest"></a>

### fa\_model\_invest\_divest

```python
def fa_model_invest_divest(req_id: int, model: str,
                           account_list: List[Dict]) -> Result
```

POST /fa/model/invest-divest

Assign an account and the amount of cash to allocate into a model.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Define the model to invest accounts into.
- `account_list` _List[Dict]_ - Collection of accounts to invest in a model. Each object may include:
  - account (str): Account identifier to invest.
  - amtToInvest (float): Amount of cash to invest in the model from the account. Use a negative amount to divest.
  

Notes:

  The following behaviors were observed against a live FA account:
  
  - Despite the `subscriptionKey`/`subscriptionStatus` fields suggesting asynchronous delivery, the
  response returns the drafted transfers synchronously, including a `transfersInstructionId` -
  pass it as `fp_order_id` to `fa_model_submit_transfers` to transmit the draft.
  - A zero `amtToInvest` is rejected with an HTTP 500 - it cannot be used to trigger a rebalance of
  previously modified allocation targets.
  - The draft only allocates the incremental cash amount toward targets; it does not liquidate
  existing off-target positions.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_invest_divest_positions"></a>

### fa\_model\_invest\_divest\_positions

```python
def fa_model_invest_divest_positions(req_id: int,
                                     model: str,
                                     subscription_status: int = None
                                     ) -> Result
```

POST /fa/model/invest-divest-positions

Request the list of all accounts already invested in the provided model and a summary of their investment.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `model` _str_ - Define the model to retrieve accounts from.
- `subscription_status` _int, optional_ - Describes if the model is in polling mode.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_model_submit_transfers"></a>

### fa\_model\_submit\_transfers

```python
def fa_model_submit_transfers(req_id: int, fp_order_id: int) -> Result
```

POST /fa/model/submit-transfers

Submit all pending orders to the models. This is similar to the Model page's Submit All Orders selection.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `fp_order_id` _int_ - Order identifier to monitor the order transmissions. Use the `transfersInstructionId`
  returned synchronously by `fa_model_invest_divest` (this sourcing is not documented in IBKR's
  specification but was confirmed against a live FA account).
  

Notes:

  - Calling with `fp_order_id=-1` (or with no pending transfer draft) results in an HTTP 500.
  - Verified live as reachable and authenticated; a successful `{reqID, success}` response requires
  a real pending transfer draft from `fa_model_invest_divest`.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_preset_get"></a>

### fa\_preset\_get

```python
def fa_preset_get(req_id: int) -> Result
```

POST /fa/fa-preset/get

Get the preset behavior for model rebalancing.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.

<a id="client.ibkr_client_mixins.fa_mixin.FaMixin.fa_preset_save"></a>

### fa\_preset\_save

```python
def fa_preset_save(
        req_id: int,
        avoid_negative_cash_in_independent: bool = None,
        close_divest_independent_position: bool = None,
        fully_invest_existing_long_positions: bool = None,
        keep_model_open: bool = None,
        prefer_cross_with_independent: bool = None,
        prefer_transfer_from_independent: bool = None,
        round_allocation_quantity_to_exchange_board_lot: bool = None,
        use_non_base_ccy: bool = None,
        use_tolerance_range: bool = None) -> Result
```

POST /fa/fa-preset/save

Set the preset behavior for models.

Arguments:

- `req_id` _int_ - Request identifier to uniquely track a request.
- `avoid_negative_cash_in_independent` _bool, optional_ - Avoid negative offsetting cash in Independent.
- `close_divest_independent_position` _bool, optional_ - Close out the full position while divesting.
- `fully_invest_existing_long_positions` _bool, optional_ - Use the maximum available funds to increase long positions.
- `keep_model_open` _bool, optional_ - Keep model open for fully divested accounts.
- `prefer_cross_with_independent` _bool, optional_ - Transfer positions to Independent instead of liquidating.
- `prefer_transfer_from_independent` _bool, optional_ - Transfer positions from Independent structure when possible.
- `round_allocation_quantity_to_exchange_board_lot` _bool, optional_ - Determine if allocation quantities should be handled by lot size.
- `use_non_base_ccy` _bool, optional_ - Use non-base balances when available.
- `use_tolerance_range` _bool, optional_ - Designate if tolerance ranges should be used for rebalancing.
