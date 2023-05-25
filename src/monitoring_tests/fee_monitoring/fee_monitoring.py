"""
Fee Monitoring
"""

import json
from typing import Tuple
import requests
from src.monitoring_tests.template_test import TemplateTest
from src.constants import SUCCESS_CODE, header
from src.helper_functions import DecodedSettlement


class FeeMonitoring:
    """
    Class for fee monitoring.
    """

    def get_order_execution(self, order, tx_hash) -> Tuple[int, int, int]:
        """
        Given an order and a transaction hash, compute buy_amount, sell_amount, and fee_amount
        of the trade.
        """
        order_uid = order["uid"]
        prod_endpoint_url = (
            "https://api.cow.fi/mainnet/api/v1/trades?orderUid=" + order_uid
        )
        trades_response = requests.get(
            prod_endpoint_url,
            headers=header,
            timeout=30,
        )
        trades = json.loads(trades_response.text)
        for trade in trades:
            if trade["txHash"] == tx_hash:
                trade_0 = trade
                break

        fee_amount = TemplateTest.get_fee(order, tx_hash)
        sell_amount = int(trade_0["sellAmount"]) - fee_amount
        buy_amount = int(trade_0["buyAmount"])

        return buy_amount, sell_amount, fee_amount

    def get_quote(self, decoded_settlement, i) -> Tuple[int, int, int]:
        """
        Given a trade, compute buy_amount, sell_amount, and fee_amount of the trade
        as proposed by our quoting infrastructure.
        """
        trade = decoded_settlement.trades[i]

        if str(f"{trade['flags']:08b}")[-1] == "0":
            kind = "sell"
        else:
            kind = "buy"

        request_dict = {
            "sellToken": decoded_settlement.tokens[trade["sellTokenIndex"]],
            "buyToken": decoded_settlement.tokens[trade["buyTokenIndex"]],
            "receiver": trade["receiver"],
            "appData": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "partiallyFillable": False,
            "sellTokenBalance": "erc20",
            "buyTokenBalance": "erc20",
            "from": trade["receiver"],
            "priceQuality": "optimal",
            "signingScheme": "eip712",
            "onchainOrder": False,
            "kind": kind,
            "sellAmountBeforeFee": str(trade["executedAmount"]),
        }

        try:
            prod_endpoint_url = "https://api.cow.fi/mainnet/api/v1/quote"
            quote_response = requests.post(
                prod_endpoint_url,
                headers=header,
                json=request_dict,
                timeout=30,
            )
            if quote_response.status_code != SUCCESS_CODE:
                barn_endpoint_url = "https://barn.api.cow.fi/mainnet/api/v1/quote"
                quote_response = requests.post(
                    barn_endpoint_url,
                    headers=header,
                    json=json.dumps(request_dict),
                    timeout=30,
                )
                if quote_response.status_code != SUCCESS_CODE:
                    TemplateTest.logger.error(
                        "Quote error: %s.", quote_response.status_code
                    )
        except ValueError as except_err:
            TemplateTest.logger.error("Unhandled exception: %s.", str(except_err))

        quote_json = json.loads(quote_response.text)

        quote_buy_amount = int(quote_json["quote"]["buyAmount"])
        quote_sell_amount = int(quote_json["quote"]["sellAmount"])
        quote_fee_amount = int(quote_json["quote"]["feeAmount"])

        return quote_buy_amount, quote_sell_amount, quote_fee_amount

    def fee_test(self, tx_hash) -> bool:  # pylint: disable=too-many-locals
        """
        Given a transaction hash, check if there is a partially-fillable order in the settlement.
        If this is the case, perform multiple tests on the execution of those orders to check if
        the fee was set correctly.
        TODO: add more explanations
        """
        # get trades via api
        orders = TemplateTest.get_endpoint_order_data(tx_hash)
        # loop through trades

        encoded_transaction = TemplateTest.get_encoded_transaction(tx_hash)
        decoded_settlement = TemplateTest.get_decoded_settlement_raw(
            encoded_transaction
        )

        partially_fillable_indices = []
        for i, order in enumerate(orders):
            if order["partiallyFillable"]:
                partially_fillable_indices.append(i)

        if len(partially_fillable_indices) > 0:
            # get additional data for the batch
            receipt = TemplateTest.get_encoded_receipt(tx_hash)
            competition_data_list = TemplateTest.get_solver_competition_data([tx_hash])
            if len(competition_data_list) == 0:
                return False
            competition_data = competition_data_list[0]

            for i in partially_fillable_indices:
                # get additional data for the trade
                (  # pylint: disable=unused-variable
                    buy_amount,
                    sell_amount,
                    fee_amount,
                ) = self.get_order_execution(orders[i], tx_hash)
                (  # pylint: disable=unused-variable
                    quote_buy_amount,
                    quote_sell_amount,
                    quote_fee_amount,
                ) = self.get_quote(decoded_settlement, i)

                diff_fee_abs = fee_amount - quote_fee_amount
                diff_fee_rel = (fee_amount - quote_fee_amount) / quote_fee_amount

                log_output = (
                    "Quote test:"
                    "Tx hash: "
                    + tx_hash
                    + "\t\t"
                    + "Order indices: "
                    + str(i)
                    + "\t\t"
                    + "Winning Solver: "
                    + competition_data["solutions"][-1]["solver"]
                    + "\t\t"
                    + "Fee: "
                    + str(fee_amount)
                    + "\t\t"
                    + "Fee quote: "
                    + str(quote_fee_amount)
                    + "\t\t"
                    + "Absolute difference: "
                    + str(diff_fee_abs)
                    + "\t\t"
                    + "Relative difference: "
                    + (str(format(100 * diff_fee_rel, ".2f")) + "%")
                )
                if abs(diff_fee_abs) > 1e15 or abs(diff_fee_rel) > 0.2:
                    TemplateTest.logger.warning(log_output)
                else:
                    TemplateTest.logger.info(log_output)

            # get batch costs
            gas_amount, gas_price = TemplateTest.get_gas_costs(
                encoded_transaction, receipt
            )
            cost = gas_amount * gas_price
            # get batch fees (not correct if some orders are market orders)
            fee = int(competition_data["solutions"][-1]["objective"]["fees"])

            a_abs = fee - cost
            a_rel = (fee - cost) / cost

            log_output = (
                "Cost coverage test:"
                "Tx hash: "
                + tx_hash
                + "\t\t"
                + "Order indices: "
                + str(partially_fillable_indices)
                + "\t\t"
                + "Winning Solver: "
                + competition_data["solutions"][-1]["solver"]
                + "\t\t"
                + "Fee: "
                + (str(format(fee * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Cost: "
                + (str(format(cost * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Absolute difference: "
                + (str(format(a_abs * 1e-18, ".5f")) + " ETH")
                + "\t\t"
                + "Relative difference: "
                + (str(format(100 * a_rel, ".2f")) + "%")
            )

            if (abs(a_abs) > 1e15 or abs(a_rel) > 0.2) and len(orders) == len(
                partially_fillable_indices
            ):
                TemplateTest.logger.warning(log_output)
            else:
                TemplateTest.logger.info(log_output)

        return True
