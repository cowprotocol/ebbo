"""
Definition of trades, orders, and executions.
"""

from fractions import Fraction


class Trade:
    """
    Class for executed orders.
    """

    def __init__(self, data, execution):
        self.data = data
        self.execution = execution

    def adapt_execution_to_gas_price(self, gas_price, gas_price_adapted):
        """
        Given an executed order which was executed ata time with gas price `gas_price`, adapt the
        execution to what it would have been with gas price `gas_price_adapted`.
        """
        self.execution.adapt_execution_to_gas_price(gas_price, gas_price_adapted)


class OrderData:
    """
    Class for order data.
    """

    def __init__(
        self,
        limit_buy_amount,
        limit_sell_amount,
        precomputed_fee_amount,
        buy_token,
        sell_token,
        is_sell_order,
        is_partially_fillable,
    ):
        self.limit_buy_amount = limit_buy_amount
        self.limit_sell_amount = limit_sell_amount
        self.precomputed_fee_amount = precomputed_fee_amount
        self.buy_token = buy_token
        self.sell_token = sell_token
        self.is_sell_order = is_sell_order
        self.is_partially_fillable = is_partially_fillable


class OrderExecution:
    """
    Class for how an order was executed.
    """

    def __init__(
        self,
        buy_amount,
        sell_amount,
        fee_amount,
    ):
        self.buy_amount = buy_amount
        self.sell_amount = sell_amount
        self.fee_amount = fee_amount

    def adapt_execution_to_gas_price(self, gas_price, gas_price_adapted):
        """
        Given an order execution created at a time with gas price `gas_price`, computes what the
        execution would have been with gas price `gas_price_adapted`.
        """

        fee_amount_adapted = int(
            self.fee_amount * Fraction(gas_price_adapted, gas_price)
        )
        self.sell_amount = self.sell_amount + self.fee_amount - fee_amount_adapted
        self.fee_amount = fee_amount_adapted
