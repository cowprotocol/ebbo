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

    def adapt_execution_to_gas_price(
        self, gas_price: int, gas_price_adapted: int
    ) -> None:
        """
        Given an executed order which was executed at a time with gas price `gas_price`, adapt the
        execution to what it would have been with gas price `gas_price_adapted`.
        """
        self.execution.adapt_execution_to_gas_price(gas_price, gas_price_adapted)

    def get_surplus(self) -> int:
        """Compute surplus in the surplus token (i.e. buy token for sell orders and sell token for
        buy orders).
        """
        if self.data.is_sell_order:
            surplus = int(
                self.execution.buy_amount
                - Fraction(
                    self.data.limit_buy_amount,
                    self.data.limit_sell_amount + self.data.precomputed_fee_amount,
                )
                * (self.execution.sell_amount + self.execution.fee_amount)
            )
        else:
            surplus = int(
                Fraction(
                    self.data.limit_sell_amount + self.data.precomputed_fee_amount,
                    self.data.limit_buy_amount,
                )
                * self.execution.buy_amount
                - (self.execution.sell_amount + self.execution.fee_amount)
            )
        return surplus

    def get_price(self) -> Fraction:
        """Compute price as sell amount + fee amount divided by buy amount."""

        return Fraction(
            self.execution.sell_amount + self.execution.fee_amount,
            self.execution.buy_amount,
        )

    def get_surplus_token(self) -> str:
        """Get the token which is used to compute surplus.
        Buy token for sell orders and sell token for buy orders.
        """
        return self.data.get_surplus_token()

    def compare_surplus(self, trade: Trade) -> int:
        """Compute absolute difference in executed surplus.
        The result is negative if trade provides more surplus than self.
        """
        return self.get_surplus() - trade.get_surplus()

    def compare_price(self, trade: Trade) -> Fraction:
        """Compute relative difference in executed prices.
        The result is negative if trade provides a better price than self.
        """
        return trade.get_price() / self.get_price() - 1


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

    def get_surplus_token(self) -> str:
        """Get the token which is used to compute surplus.
        Buy token for sell orders and sell token for buy orders.
        """
        if self.is_sell_order:
            token = self.buy_token
        else:
            token = self.sell_token
        return token


@dataclass
class OrderExecution:
    """Class for how an order was executed."""

    buy_amount: int
    sell_amount: int
    fee_amount: int

    def adapt_execution_to_gas_price(
        self, gas_price: int, gas_price_adapted: int
    ) -> None:
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
