from django.contrib import admin

from .models import Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline]
    list_display = (
        "id",
        "name",
        "barcode",
        "user",
        "quantity_received",
        "quantity_sold",
        "remaining_quantity",
        "purchase_price",
        "selling_price",
    )
    search_fields = ("name", "barcode")
    list_filter = ("arrival_date",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image", "created_at")
