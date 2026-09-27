from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "quantity_received",
        "quantity_sold",
        "remaining_quantity",
        "purchase_price",
        "selling_price",
    )
    search_fields = ("name",)
    list_filter = ("arrival_date",)
