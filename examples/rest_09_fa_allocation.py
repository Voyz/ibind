"""
REST FA Allocation Management

In this example we:

* Initialise the IBind logs
* List all Financial Advisor model portfolios and detect allocation drift
* Request positions of a mismatched model, sorted by imbalance
* Read the model rebalancing presets

Assumes a Financial Advisor account and that the IBIND_ACCOUNT_ID and IBIND_CACERT environment variables have been set.

Note: the FA model endpoints have not yet been verified against a live FA account. See the FaMixin documentation for details.
"""

import os

from ibind import IbkrClient, ibind_logs_initialize

ibind_logs_initialize()

cacert = os.getenv('IBIND_CACERT', False)  # insert your cacert path here
client = IbkrClient(cacert=cacert)

print('\n#### fa_model_list ####')
model_list = client.fa_model_list(req_id=1).data
print(f'\t Master account: {model_list["masterAccount"]} ({model_list["baseCcy"]})')
mismatched_models = []
for model in model_list['models']:
    print(f'\t Model {model["model"]}: nlv={model["nlv"]}, accounts={model["numAccounts"]}, mismatch={model["mismatch"]}')
    if model['mismatch']:
        mismatched_models.append(model['model'])

for model_name in mismatched_models:
    print(f'\n#### fa_model_positions ({model_name}) ####')
    positions = client.fa_model_positions(req_id=2, model=model_name, sort_field='instrumentImbalance', sort_direction='DESC').data
    for position in positions['positionList']:
        print(
            f'\t {position["instrument"]}: target={position["target"]}%, actual={position["actual"]}%, imbalance={position["instrumentImbalance"]}%'
        )

print('\n#### fa_preset_get ####')
presets = client.fa_preset_get(req_id=3).data
print(presets)

# To rebalance a mismatched model, invest or divest accounts and submit the resulting transfers.
# These calls modify the account - uncomment only when you intend to trade, ideally on a paper account first.
#
# invest_result = client.fa_model_invest_divest(
#     req_id=4,
#     model='Sample-Model',
#     account_list=[{'account': 'DU1234567', 'amtToInvest': 1000.0}],
# ).data
# print(invest_result)
#
# print(client.fa_model_invest_divest_positions(req_id=5, model='Sample-Model').data)
#
# The source of a valid fp_order_id is not yet confirmed - see the fa_model_submit_transfers documentation.
# print(client.fa_model_submit_transfers(req_id=6, fp_order_id=-1).data)
