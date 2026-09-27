from django.contrib import admin

from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "user",
        "quantity",
        "price_per_item",
        "total_amount",
        "profit",
        "loss",
        "sold_at",
    )
    list_filter = ("sold_at",)
