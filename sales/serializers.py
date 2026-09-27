from rest_framework import serializers

from .models import Sale


class SaleSerializer(serializers.ModelSerializer):
    """
    Сериализатор продажи. product_name добавлен для удобства,
    чтобы фронтенду не приходилось делать отдельный запрос за
    названием товара.
    """

    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "product",
            "product_name",
            "quantity",
            "price_per_item",
            "total_amount",
            "profit",
            "loss",
            "sold_at",
        )
        read_only_fields = (
            "id",
            "product_name",
            "total_amount",
            "profit",
            "loss",
            "sold_at",
        )
