from typing import TYPE_CHECKING, Dict, List

from ibind.base.rest_client import Result
from ibind.support.logs import project_logger
from ibind.support.py_utils import params_dict

if TYPE_CHECKING:  # pragma: no cover
    from ibind import IbkrClient

_LOGGER = project_logger(__file__)


class FaMixin:  # pragma: no cover
    """
    Financial Advisor model portfolio endpoints ('Trading FA Allocation Management').

    * https://www.interactivebrokers.com/campus/ibkr-api-page/web-api/

    Covers the `/fa/model/*` and `/fa/fa-preset/*` endpoint group, allowing Financial Advisor accounts to
    list, create, rebalance and monitor model portfolios programmatically.

    Note:
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
    """

    def fa_model_list(self: 'IbkrClient', req_id: int) -> Result:
        """
        POST /fa/model/list

        Retrieve summaries for all models under the advisor account.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
        """
        return self.post('fa/model/list', {'reqID': req_id})

    def fa_model_positions(
        self: 'IbkrClient',
        req_id: int,
        model: str,
        sort_field: str = None,
        sort_direction: str = None,
        limit: int = None,
    ) -> Result:
        """
        POST /fa/model/positions

        Request all positions held within the model.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Name of your model.
            sort_field (str, optional): Field to sort the response by. Available values: 'actual', 'actualRangeMax', 'actualRangeMin', 'ccy', 'conid', 'dlv', 'instrumentImbalance', 'instrument', 'mismatchType', 'mv', 'position', 'target'.
            sort_direction (str, optional): Direction to sort the request by. Available values: 'ASC', 'DESC'.
            limit (int, optional): Maximum number of positions to return.
        """
        params = params_dict(
            {'reqID': req_id, 'model': model},
            optional={
                'sortField': sort_field,
                'sortDirection': sort_direction,
                'limit': limit,
            },
        )
        return self.post('fa/model/positions', params)

    def fa_model_summary(self: 'IbkrClient', req_id: int, model: str) -> Result:
        """
        POST /fa/model/summary

        Request a summary for a single model.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Name of your model.
        """
        return self.post('fa/model/summary', {'reqID': req_id, 'model': model})

    def fa_model_accounts_details(self: 'IbkrClient', req_id: int, model: str, calc_pnls: bool = None) -> Result:
        """
        POST /fa/model/accounts-details

        Request all accounts held within a model.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Request model to pull account details from.
            calc_pnls (bool, optional): Determine if Profit and Loss values should be calculated.
        """
        params = params_dict(
            {'reqID': req_id, 'model': model},
            optional={'calcPnls': calc_pnls},
        )
        return self.post('fa/model/accounts-details', params)

    def fa_model_save(
        self: 'IbkrClient',
        req_id: int,
        model: str,
        desc: str,
        is_static: bool,
        cash_targets: List[Dict],
        position_targets: List[Dict],
    ) -> Result:
        """
        POST /fa/model/save

        Create or Modify a model's target positions.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Name of your model.
            desc (str): Personal description of model to read in IBKR GUI elements.
            is_static (bool): Determine if investing and rebalancing should be handled statically or dynamically. Set to True for static models that always use the original targets, or False for dynamic models that adjust allocation in response to market movements.
            cash_targets (List[Dict]): Array of target cash objects. Each object may include:
                - ccy (str): Currency code to hold positions.
                - target (float): Fraction of the model to allocate to the given currency, in [0, 1].
            position_targets (List[Dict]): List containing all contracts to hold in the model. Each object may include:
                - conid (int): Contract identifier, conid, to designate which security to hold.
                - target (float): Fraction of the model to allocate to the given contract, in [0, 1].

        Note:
            The following behaviors were observed against a live FA account and differ from or extend IBKR's specification:

            - `target` values are fractions in [0, 1] and must sum to 1.0 across cash_targets and position_targets
              combined. IBKR's OpenAPI schema describes them as percentages, but 0-100 values are rejected with a 400.
            - Omitting `desc` results in a bare 400 response with no body.
            - `is_static` cannot be changed on a model that already has invested accounts (400) - use the IBKR GUI instead.
            - On an invested dynamic model, a save can succeed silently with no effect. Read the targets back
              (`fa_model_list` / `fa_model_positions`) to verify the save took effect.
        """
        params = params_dict(
            {
                'reqID': req_id,
                'model': model,
                'desc': desc,
                'isStatic': is_static,
                'cashTargets': cash_targets,
                'positionTargets': position_targets,
            }
        )
        return self.post('fa/model/save', params)

    def fa_model_invest_divest(self: 'IbkrClient', req_id: int, model: str, account_list: List[Dict]) -> Result:
        """
        POST /fa/model/invest-divest

        Assign an account and the amount of cash to allocate into a model.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Define the model to invest accounts into.
            account_list (List[Dict]): Collection of accounts to invest in a model. Each object may include:
                - account (str): Account identifier to invest.
                - amtToInvest (float): Amount of cash to invest in the model from the account. Use a negative amount to divest.

        Note:
            The following behaviors were observed against a live FA account:

            - Despite the `subscriptionKey`/`subscriptionStatus` fields suggesting asynchronous delivery, the
              response returns the drafted transfers synchronously, including a `transfersInstructionId` -
              pass it as `fp_order_id` to `fa_model_submit_transfers` to transmit the draft.
            - A zero `amtToInvest` is rejected with an HTTP 500 - it cannot be used to trigger a rebalance of
              previously modified allocation targets.
            - The draft only allocates the incremental cash amount toward targets; it does not liquidate
              existing off-target positions.
        """
        params = params_dict({'reqID': req_id, 'model': model, 'accountList': account_list})
        return self.post('fa/model/invest-divest', params)

    def fa_model_invest_divest_positions(self: 'IbkrClient', req_id: int, model: str, subscription_status: int = None) -> Result:
        """
        POST /fa/model/invest-divest-positions

        Request the list of all accounts already invested in the provided model and a summary of their investment.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            model (str): Define the model to retrieve accounts from.
            subscription_status (int, optional): Describes if the model is in polling mode.
        """
        params = params_dict(
            {'reqID': req_id, 'model': model},
            optional={'subscriptionStatus': subscription_status},
        )
        return self.post('fa/model/invest-divest-positions', params)

    def fa_model_submit_transfers(self: 'IbkrClient', req_id: int, fp_order_id: int) -> Result:
        """
        POST /fa/model/submit-transfers

        Submit all pending orders to the models. This is similar to the Model page's Submit All Orders selection.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            fp_order_id (int): Order identifier to monitor the order transmissions. Use the `transfersInstructionId`
                returned synchronously by `fa_model_invest_divest` (this sourcing is not documented in IBKR's
                specification but was confirmed against a live FA account).

        Note:
            - Calling with `fp_order_id=-1` (or with no pending transfer draft) results in an HTTP 500.
            - Verified live as reachable and authenticated; a successful `{reqID, success}` response requires
              a real pending transfer draft from `fa_model_invest_divest`.
        """
        return self.post('fa/model/submit-transfers', {'reqID': req_id, 'fpOrderId': fp_order_id})

    def fa_preset_get(self: 'IbkrClient', req_id: int) -> Result:
        """
        POST /fa/fa-preset/get

        Get the preset behavior for model rebalancing.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
        """
        return self.post('fa/fa-preset/get', {'reqID': req_id})

    def fa_preset_save(
        self: 'IbkrClient',
        req_id: int,
        avoid_negative_cash_in_independent: bool = None,
        close_divest_independent_position: bool = None,
        fully_invest_existing_long_positions: bool = None,
        keep_model_open: bool = None,
        prefer_cross_with_independent: bool = None,
        prefer_transfer_from_independent: bool = None,
        round_allocation_quantity_to_exchange_board_lot: bool = None,
        use_non_base_ccy: bool = None,
        use_tolerance_range: bool = None,
    ) -> Result:
        """
        POST /fa/fa-preset/save

        Set the preset behavior for models.

        Parameters:
            req_id (int): Request identifier to uniquely track a request.
            avoid_negative_cash_in_independent (bool, optional): Avoid negative offsetting cash in Independent.
            close_divest_independent_position (bool, optional): Close out the full position while divesting.
            fully_invest_existing_long_positions (bool, optional): Use the maximum available funds to increase long positions.
            keep_model_open (bool, optional): Keep model open for fully divested accounts.
            prefer_cross_with_independent (bool, optional): Transfer positions to Independent instead of liquidating.
            prefer_transfer_from_independent (bool, optional): Transfer positions from Independent structure when possible.
            round_allocation_quantity_to_exchange_board_lot (bool, optional): Determine if allocation quantities should be handled by lot size.
            use_non_base_ccy (bool, optional): Use non-base balances when available.
            use_tolerance_range (bool, optional): Designate if tolerance ranges should be used for rebalancing.
        """
        params = params_dict(
            {'reqID': req_id},
            optional={
                'avoidNegativeCashInIndependent': avoid_negative_cash_in_independent,
                'closeDivestIndependentPosition': close_divest_independent_position,
                'fullyInvestExistingLongPositions': fully_invest_existing_long_positions,
                'keepModelOpen': keep_model_open,
                'preferCrossWithIndependent': prefer_cross_with_independent,
                'preferTransferFromIndependent': prefer_transfer_from_independent,
                'roundAllocationQuantityToExchangeBoardLot': round_allocation_quantity_to_exchange_board_lot,
                'useNonBaseCcy': use_non_base_ccy,
                'useToleranceRange': use_tolerance_range,
            },
        )
        return self.post('fa/fa-preset/save', params)
