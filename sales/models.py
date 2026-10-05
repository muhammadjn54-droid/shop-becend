from decimal import Decimal

from django.conf import settings
from django.db import models

from products.models import Product


class Sale(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="sales"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales"
    )
    quantity = models.PositiveIntegerField(verbose_name="Продано штук")
    price_per_item = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Цена продажи за 1 шт."
    )
    purchase_price_per_item = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Закупочная цена за 1 шт. на момент продажи",
    )
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Сумма продажи"
    )
    cost_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        verbose_name="Себестоимость продажи",
    )
    profit = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="Прибыль с продажи"
    )
    loss = models.DecimalField(
        max_digits=14, decimal_places=2, default=0, verbose_name="Убыток с продажи"
    )
    sold_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sold_at"]

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def returned_quantity(self):
        return sum(item.quantity for item in self.returns.all())

    @property
    def net_quantity(self):
        return max(self.quantity - self.returned_quantity, 0)

    @property
    def net_total_amount(self):
        refunded = sum(
            (item.refund_amount for item in self.returns.all()),
            Decimal("0.00"),
        )
        return self.total_amount - refunded

    @property
    def net_cost_amount(self):
        return self.cost_amount - sum(
            (item.returned_cost for item in self.returns.all()), Decimal("0.00")
        )

    @property
    def net_profit(self):
        return self.profit - sum(
            (item.profit_reversal for item in self.returns.all()), Decimal("0.00")
        )

    @property
    def net_loss(self):
        return self.loss - sum(
            (item.loss_reversal for item in self.returns.all()), Decimal("0.00")
        )


class SaleReturn(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sale_returns",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="sale_returns",
    )
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name="returns",
    )
    quantity = models.PositiveIntegerField(verbose_name="Возвращено штук")
    refund_amount = models.DecimalField(max_digits=14, decimal_places=2)
    returned_cost = models.DecimalField(max_digits=14, decimal_places=2)
    profit_reversal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    loss_reversal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    returned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-returned_at"]

    def __str__(self):
        return f"Return {self.product.name} x{self.quantity}"
