"""
Fee Monitoring
"""

from src.monitoring_tests.template_test import TemplateTest
from src.constants import (
    FEE_ABSOLUTE_DEVIATION_ETH_FLAG,
    FEE_RELATIVE_DEVIATION_FLAG,
)


class FeeMonitoring:
    """
    Class for fee monitoring.
    """

    def fee_test(self, tx_hash) -> bool:
        # pylint: disable=too-many-locals, too-many-branches
        """
        Given a transaction hash, check if there is a partially-fillable order in the settlement.
        If this is the case, perform multiple tests on the execution of those orders to check if
        the fee was set correctly.
        TODO: add more explanations
        """
        # get trades via api
        orders = TemplateTest.get_endpoint_order_data(tx_hash)

        partially_fillable_indices = []
        for i, order in enumerate(orders):
            if order["partiallyFillable"]:
                partially_fillable_indices.append(i)
                log_output = (
                    "Partially fillable order found.\t"
                    + "Tx hash:"
                    + tx_hash
                    + "\t\t"
                    + "Order uid: "
                    + order["uid"]
                )
                TemplateTest.logger.debug(log_output)

        if len(partially_fillable_indices) > 0:
            # get additional data for the batch
            encoded_transaction = TemplateTest.get_encoded_transaction(tx_hash)
            decoded_settlement = TemplateTest.get_decoded_settlement_raw(
                encoded_transaction
            )
            receipt = TemplateTest.get_encoded_receipt(tx_hash)

            # get batch costs
            gas_amount, gas_price = TemplateTest.get_gas_costs(
                encoded_transaction, receipt
            )

            for i in partially_fillable_indices:
                # get additional data for the trade
                (
                    _,
                    _,
                    fee_amount,
                ) = TemplateTest.get_order_execution(decoded_settlement, i)

                try:
                    (
                        quote_buy_amount,
                        quote_sell_amount,
                        quote_fee_amount,
                    ) = TemplateTest.get_quote(decoded_settlement, i)
                except ConnectionError as err:
                    TemplateTest.logger.error("ConnectionError fetching quote: %s", err)
                    return False
                except ValueError as err:
                    TemplateTest.logger.error("ValueError fetching quote: %s.", err)
                    return True
                try:
                    gas_price_quote = TemplateTest.get_current_gas_price()
                except ValueError as err:
                    TemplateTest.logger.error(
                        "Error fetching current gas price: %s", err
                    )
                    return False
                (
                    _,
                    _,
                    quote_fee_amount,  # updates the fee to the old gas price
                ) = TemplateTest.adapt_execution_to_gas_price(
                    quote_buy_amount,
                    quote_sell_amount,
                    quote_fee_amount,
                    gas_price_quote,
                    gas_price,
                )

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
                    + encoded_transaction["from"]
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
                if abs(diff_fee_rel) > FEE_RELATIVE_DEVIATION_FLAG:
                    TemplateTest.logger.warning(log_output)
                else:
                    TemplateTest.logger.debug(log_output)

            cost = gas_amount * gas_price
            # get batch fees (not correct if some orders are market orders)

            competition_data_list = TemplateTest.get_solver_competition_data([tx_hash])
            if len(competition_data_list) == 0:
                TemplateTest.logger.debug("No competition data found. Skipping hash.")
                return False
            competition_data = competition_data_list[0]

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
                + encoded_transaction["from"]
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

            if (
                abs(a_abs) > 1e18 * FEE_ABSOLUTE_DEVIATION_ETH_FLAG
                or abs(a_rel) > FEE_RELATIVE_DEVIATION_FLAG
            ) and len(orders) == len(partially_fillable_indices):
                TemplateTest.logger.warning(log_output)
            else:
                TemplateTest.logger.info(log_output)
        else:
            TemplateTest.logger.debug("No partially fillable order found.")
        return True
