from decimal import Decimal

from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор товара.

    Вычисляемые поля (remaining_quantity, revenue, sold_cost, profit, loss)
    доступны только для чтения — их нельзя изменить напрямую через API,
    они всегда рассчитываются "на лету" из модели.
    """

    remaining_quantity = serializers.IntegerField(read_only=True)
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    sold_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    loss = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    profit_per_item = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "image",
            "arrival_date",
            "quantity_received",
            "quantity_sold",
            "remaining_quantity",
            "purchase_price",
            "selling_price",
            "revenue",
            "sold_cost",
            "profit",
            "loss",
            "profit_per_item",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "quantity_sold",
            "remaining_quantity",
            "revenue",
            "sold_cost",
            "profit",
            "loss",
            "profit_per_item",
            "created_at",
            "updated_at",
        )

    def validate_quantity_received(self, value):
        if value < 0:
            raise serializers.ValidationError("Количество не может быть отрицательным")
        return value

    def validate_purchase_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Закупочная цена не может быть отрицательной")
        return value

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Цена продажи не может быть отрицательной")
        return value


class SellSerializer(serializers.Serializer):
    """Тело запроса для продажи товара: POST /api/products/{id}/sell/"""

    quantity = serializers.IntegerField(min_value=1)
    price_per_item = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class AddStockSerializer(serializers.Serializer):
    """Тело запроса для поступления новой партии: POST /api/products/{id}/add-stock/"""

    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class ReturnSerializer(serializers.Serializer):
    """Тело запроса для возврата товара: POST /api/products/{id}/return/"""

    quantity = serializers.IntegerField(min_value=1)
