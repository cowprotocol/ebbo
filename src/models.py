"""
Definition of trades, orders, and executions.
"""
from __future__ import annotations
from fractions import Fraction
from dataclasses import dataclass


@dataclass
class Trade:
    """
    Class for executed orders.
    """

    data: OrderData
    execution: OrderExecution

    def adapt_execution_to_gas_price(self, gas_price, gas_price_adapted):
        """
        Given an executed order which was executed ata time with gas price `gas_price`, adapt the
        execution to what it would have been with gas price `gas_price_adapted`.
        """
        self.execution.adapt_execution_to_gas_price(gas_price, gas_price_adapted)


@dataclass
class OrderData:
    """
    Class for order data.
    """

    limit_buy_amount: int
    limit_sell_amount: int
    precomputed_fee_amount: int
    buy_token: str
    sell_token: str
    is_sell_order: bool
    is_partially_fillable: bool


@dataclass
class OrderExecution:
    """
    Class for how an order was executed.
    """

    buy_amount: int
    sell_amount: int
    fee_amount: int

    def adapt_execution_to_gas_price(self, gas_price: int, gas_price_adapted: int):
        """
        Given an order execution created at a time with gas price `gas_price`, computes what the
        execution would have been with gas price `gas_price_adapted`.
        """

        fee_amount_adapted = int(
            self.fee_amount * Fraction(gas_price_adapted, gas_price)
        )
        self.sell_amount = self.sell_amount + self.fee_amount - fee_amount_adapted
        self.fee_amount = fee_amount_adapted


def find_partially_fillable(trades: list[Trade]) -> list[int]:
    """
    Go through a list of trades and output a list of indices corresponding to all partially
    fillable orders.
    """
    partially_fillable_indices = []
    for i, trade in enumerate(trades):
        if trade.data.is_partially_fillable:
            partially_fillable_indices.append(i)

    return partially_fillable_indices
