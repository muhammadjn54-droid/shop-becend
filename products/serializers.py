from decimal import Decimal

from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
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
        if self.instance and value < self.instance.quantity_sold:
            raise serializers.ValidationError(
                "Количество поступившего товара не может быть меньше уже проданного"
            )
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
    quantity = serializers.IntegerField(min_value=1)
    price_per_item = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class AddStockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class ReturnSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    sale_id = serializers.IntegerField(min_value=1, required=False)
