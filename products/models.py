from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_image_size(file):
    """Ограничивает размер загружаемого изображения."""
    from django.core.exceptions import ValidationError
    from django.conf import settings as dj_settings

    max_size = dj_settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(
            f"Размер изображения не должен превышать {dj_settings.MAX_IMAGE_SIZE_MB} MB"
        )


class Product(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
    )
    name = models.CharField(max_length=255, verbose_name="Название товара")
    image = models.ImageField(
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ],
        verbose_name="Фото товара",
    )
    arrival_date = models.DateField(verbose_name="Дата поступления")
    quantity_received = models.PositiveIntegerField(
        default=0, verbose_name="Поступило (шт.)"
    )
    quantity_sold = models.PositiveIntegerField(
        default=0, verbose_name="Продано (шт.)"
    )
    purchase_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Закупочная цена за 1 шт."
    )
    selling_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Цена продажи за 1 шт."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def remaining_quantity(self):
        return self.quantity_received - self.quantity_sold

    def _financial_totals(self):
        """Считает финансовые итоги по реальным продажам с учётом возвратов."""
        cached = getattr(self, "_financial_totals_cache", None)
        if cached is not None:
            return cached

        revenue = Decimal("0.00")
        sold_cost = Decimal("0.00")
        profit = Decimal("0.00")
        loss = Decimal("0.00")

        for sale in self.sales.all():
            revenue += sale.total_amount
            sold_cost += sale.cost_amount
            profit += sale.profit
            loss += sale.loss

            for returned in sale.returns.all():
                revenue -= returned.refund_amount
                sold_cost -= returned.returned_cost
                profit -= returned.profit_reversal
                loss -= returned.loss_reversal

        totals = {
            "revenue": max(revenue, Decimal("0.00")),
            "sold_cost": max(sold_cost, Decimal("0.00")),
            "profit": max(profit, Decimal("0.00")),
            "loss": max(loss, Decimal("0.00")),
        }
        self._financial_totals_cache = totals
        return totals

    def clear_financial_cache(self):
        if hasattr(self, "_financial_totals_cache"):
            delattr(self, "_financial_totals_cache")

    @property
    def revenue(self):
        return self._financial_totals()["revenue"]

    @property
    def sold_cost(self):
        return self._financial_totals()["sold_cost"]

    @property
    def profit(self):
        return self._financial_totals()["profit"]

    @property
    def loss(self):
        return self._financial_totals()["loss"]

    @property
    def profit_per_item(self):
        return self.selling_price - self.purchase_price

    @property
    def loss_per_item(self):
        diff = self.purchase_price - self.selling_price
        return diff if diff > 0 else Decimal("0.00")


class ProductImage(models.Model):
    """Дополнительные фотографии товара (поддержка множественных изображений)."""

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Товар",
    )
    image = models.ImageField(
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ],
        verbose_name="Фото товара",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Фото товара"
        verbose_name_plural = "Фотографии товаров"

    def __str__(self):
        return f"Фото #{self.id} для {self.product.name}"

