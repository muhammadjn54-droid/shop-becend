from django.conf import settings
from django.db import models

from products.models import Product


class Sale(models.Model):
    """
    Отдельная запись о продаже. Каждая продажа регистрируется
    отдельно, чтобы можно было видеть полную историю продаж
    каждого товара.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sales"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sales"
    )

    quantity = models.PositiveIntegerField(verbose_name="Продано штук")
    price_per_item = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Цена продажи за 1 шт."
    )
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, verbose_name="Сумма продажи"
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
