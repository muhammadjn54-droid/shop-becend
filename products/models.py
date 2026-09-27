from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


def validate_image_size(file):
    """Ограничивает размер загружаемого изображения (см. settings.MAX_IMAGE_SIZE_MB)."""
    from django.core.exceptions import ValidationError
    from django.conf import settings as dj_settings

    max_size = dj_settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file.size > max_size:
        raise ValidationError(
            f"Размер изображения не должен превышать {dj_settings.MAX_IMAGE_SIZE_MB} MB"
        )


class Product(models.Model):
    """
    Товар на складе.

    Остаток, выручка, себестоимость, прибыль и убыток — это не поля,
    а вычисляемые свойства, чтобы они всегда были в актуальном
    состоянии и не могли быть испорчены случайным PATCH запросом.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
    )

    name = models.CharField(max_length=255, verbose_name="Название товара")

    # ImageField без upload_to — файлы сохраняются прямо в MEDIA_ROOT.
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

    # ---------------------------------------------------------------
    # ВЫЧИСЛЯЕМЫЕ СВОЙСТВА
    # ---------------------------------------------------------------

    @property
    def remaining_quantity(self):
        """Сколько товара осталось на складе: пришло - продано."""
        return self.quantity_received - self.quantity_sold

    @property
    def revenue(self):
        """Выручка: сколько денег получено с продаж этого товара."""
        return self.quantity_sold * self.selling_price

    @property
    def sold_cost(self):
        """Себестоимость проданного товара: сколько стоила закупка проданного количества."""
        return self.quantity_sold * self.purchase_price

    @property
    def profit(self):
        """Чистая прибыль. Если выручка меньше себестоимости — прибыли нет (0)."""
        diff = self.revenue - self.sold_cost
        return diff if diff > 0 else Decimal("0.00")

    @property
    def loss(self):
        """Убыток. Если себестоимость меньше выручки — убытка нет (0)."""
        diff = self.sold_cost - self.revenue
        return diff if diff > 0 else Decimal("0.00")

    @property
    def profit_per_item(self):
        """Прибыль с одной единицы товара (может быть отрицательной)."""
        return self.selling_price - self.purchase_price

    @property
    def loss_per_item(self):
        """Убыток с одной единицы товара, если цена продажи ниже закупочной."""
        diff = self.purchase_price - self.selling_price
        return diff if diff > 0 else Decimal("0.00")
