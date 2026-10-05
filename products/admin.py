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
        "is_archived",
    )
    search_fields = ("name", "barcode")
    list_filter = ("arrival_date", "is_archived")
    readonly_fields = ("quantity_sold",)
    actions = ("archive_products",)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Архивировать выбранные товары")
    def archive_products(self, request, queryset):
        from django.utils import timezone

        queryset.update(is_archived=True, updated_at=timezone.now())


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "image", "created_at")
