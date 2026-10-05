from django.contrib import admin

from .models import Sale, SaleReturn


class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    """Stock counters must change through the transactional sale/return API."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sale)
class SaleAdmin(ReadOnlyLedgerAdmin):
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
class SaleReturnAdmin(ReadOnlyLedgerAdmin):
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
