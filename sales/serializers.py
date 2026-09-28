from rest_framework import serializers

from .models import Sale, SaleReturn


class SaleReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleReturn
        fields = (
            "id",
            "sale",
            "product",
            "quantity",
            "refund_amount",
            "returned_cost",
            "profit_reversal",
            "loss_reversal",
            "returned_at",
        )
        read_only_fields = fields


class SaleSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    returned_quantity = serializers.IntegerField(read_only=True)
    net_quantity = serializers.IntegerField(read_only=True)
    net_total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = Sale
        fields = (
            "id",
            "product",
            "product_name",
            "quantity",
            "returned_quantity",
            "net_quantity",
            "price_per_item",
            "purchase_price_per_item",
            "total_amount",
            "net_total_amount",
            "cost_amount",
            "profit",
            "loss",
            "sold_at",
        )
        read_only_fields = (
            "id",
            "product_name",
            "purchase_price_per_item",
            "total_amount",
            "cost_amount",
            "profit",
            "loss",
            "returned_quantity",
            "net_quantity",
            "net_total_amount",
            "sold_at",
        )
