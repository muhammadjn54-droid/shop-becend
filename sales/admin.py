from django.contrib import admin

from .models import Sale, SaleReturn


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "user",
        "quantity",
        "price_per_item",
        "purchase_price_per_item",
        "total_amount",
        "profit",
        "loss",
        "sold_at",
    )
    list_filter = ("sold_at",)
    search_fields = ("product__name", "user__username")


@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "sale",
        "quantity",
        "refund_amount",
        "returned_at",
    )
    list_filter = ("returned_at",)
    search_fields = ("product__name", "user__username")
