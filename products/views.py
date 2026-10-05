from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from .models import Product, ProductImage
from .serializers import (
    ProductSerializer,
    ProductImageSerializer,
    SellSerializer,
    AddStockSerializer,
    ReturnSerializer,
)
from sales.models import Sale, SaleReturn
from sales.serializers import SaleSerializer, SaleReturnSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    search_fields = ["name", "barcode"]
    ordering_fields = [
        "name",
        "barcode",
        "arrival_date",
        "purchase_price",
        "selling_price",
        "created_at",
    ]
    filterset_fields = ["arrival_date", "name", "barcode"]

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user, is_archived=False).prefetch_related(
            "sales__returns", "images"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user).prefetch_related(
            "sales__returns", "images"
        )

    def perform_destroy(self, instance):
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=instance.pk)
            product.is_archived = True
            product.save(update_fields=["is_archived", "updated_at"])


class ProductLowStockView(generics.ListAPIView):
    serializer_class = ProductSerializer
    search_fields = ProductListCreateView.search_fields
    ordering_fields = ProductListCreateView.ordering_fields
    filterset_fields = ProductListCreateView.filterset_fields

    def get_queryset(self):
        return Product.objects.filter(
            user=self.request.user,
            is_archived=False,
            quantity_received__lte=F("quantity_sold") + 5,
        ).prefetch_related("sales__returns", "images")


class ProductSalesHistoryView(generics.ListAPIView):
    serializer_class = SaleSerializer

    def get_queryset(self):
        product = get_object_or_404(
            Product, id=self.kwargs["pk"], user=self.request.user
        )
        return (
            Sale.objects.filter(product=product, user=self.request.user)
            .select_related("product")
            .prefetch_related("returns")
        )


class ProductSellView(APIView):
    @swagger_auto_schema(request_body=SellSerializer)
    def post(self, request, pk):
        serializer = SellSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), id=pk, user=request.user,
                is_archived=False,
            )
            price_per_item = serializer.validated_data.get(
                "price_per_item", product.selling_price
            )

            if quantity > product.remaining_quantity:
                return Response(
                    {"detail": "Недостаточно товара на складе"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            purchase_price_per_item = product.purchase_price
            total_amount = quantity * price_per_item
            cost_amount = quantity * purchase_price_per_item

            if total_amount > cost_amount:
                profit = total_amount - cost_amount
                loss = Decimal("0.00")
            elif total_amount < cost_amount:
                profit = Decimal("0.00")
                loss = cost_amount - total_amount
            else:
                profit = Decimal("0.00")
                loss = Decimal("0.00")

            sale = Sale.objects.create(
                product=product,
                user=request.user,
                quantity=quantity,
                price_per_item=price_per_item,
                purchase_price_per_item=purchase_price_per_item,
                total_amount=total_amount,
                cost_amount=cost_amount,
                profit=profit,
                loss=loss,
            )

            product.quantity_sold += quantity
            product.save(update_fields=["quantity_sold", "updated_at"])
            product.clear_financial_cache()

        return Response(
            {
                "message": "Товар успешно продан",
                "sale": SaleSerializer(sale).data,
                "product": ProductSerializer(product, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProductAddStockView(APIView):
    @swagger_auto_schema(request_body=AddStockSerializer)
    def post(self, request, pk):
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity = serializer.validated_data["quantity"]
        new_purchase_price = serializer.validated_data.get("purchase_price")

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), id=pk, user=request.user,
                is_archived=False,
            )
            product.quantity_received += quantity
            update_fields = ["quantity_received", "updated_at"]

            if new_purchase_price is not None:
                product.purchase_price = new_purchase_price
                update_fields.append("purchase_price")

            product.save(update_fields=update_fields)

        return Response(
            {
                "message": "Количество товара увеличено",
                "product": ProductSerializer(product, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class ProductReturnView(APIView):
    @swagger_auto_schema(request_body=ReturnSerializer)
    def post(self, request, pk):
        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quantity_to_return = serializer.validated_data["quantity"]
        sale_id = serializer.validated_data.get("sale_id")

        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(), id=pk, user=request.user
            )

            if quantity_to_return > product.quantity_sold:
                return Response(
                    {"detail": "Нельзя вернуть больше товара, чем доступно для возврата"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sales = Sale.objects.select_for_update().filter(
                product=product,
                user=request.user,
            )

            if sale_id is not None:
                sales = sales.filter(id=sale_id)

            sales = sales.order_by("-sold_at")
            remaining = quantity_to_return
            created_returns = []

            for sale in sales:
                already_returned = (
                    sale.returns.aggregate(total=Sum("quantity"))["total"] or 0
                )
                available = sale.quantity - already_returned

                if available <= 0:
                    continue

                take = min(available, remaining)

                unit_profit = max(
                    sale.price_per_item - sale.purchase_price_per_item,
                    Decimal("0.00"),
                )
                unit_loss = max(
                    sale.purchase_price_per_item - sale.price_per_item,
                    Decimal("0.00"),
                )

                returned = SaleReturn.objects.create(
                    user=request.user,
                    product=product,
                    sale=sale,
                    quantity=take,
                    refund_amount=take * sale.price_per_item,
                    returned_cost=take * sale.purchase_price_per_item,
                    profit_reversal=take * unit_profit,
                    loss_reversal=take * unit_loss,
                )
                created_returns.append(returned)
                remaining -= take

                if remaining == 0:
                    break

            if remaining > 0:
                transaction.set_rollback(True)
                return Response(
                    {"detail": "Нельзя вернуть больше товара, чем доступно для возврата"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            product.quantity_sold -= quantity_to_return
            product.save(update_fields=["quantity_sold", "updated_at"])
            product.clear_financial_cache()

        return Response(
            {
                "message": "Возврат товара успешно оформлен",
                "returns": SaleReturnSerializer(created_returns, many=True).data,
                "product": ProductSerializer(product, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )


class StatisticsView(APIView):
    def get(self, request):
        products = list(
            Product.objects.filter(user=request.user).prefetch_related("sales__returns")
        )
        active_products = [product for product in products if not product.is_archived]

        return Response(
            {
                "products_count": len(active_products),
                "total_items_received": sum(p.quantity_received for p in products),
                "total_items_sold": sum(p.quantity_sold for p in products),
                "total_items_remaining": sum(p.remaining_quantity for p in active_products),
                "total_items_archived": sum(p.remaining_quantity for p in products if p.is_archived),
                "total_revenue": sum(
                    (p.revenue for p in products), Decimal("0.00")
                ),
                "total_cost_of_sold_goods": sum(
                    (p.sold_cost for p in products), Decimal("0.00")
                ),
                "total_profit": sum(
                    (p.profit for p in products), Decimal("0.00")
                ),
                "total_loss": sum(
                    (p.loss for p in products), Decimal("0.00")
                ),
            }
        )


class DashboardView(APIView):
    def get(self, request):
        products = list(
            Product.objects.filter(user=request.user).prefetch_related("sales__returns", "images")
        )
        active_products = [product for product in products if not product.is_archived]

        recent_sales = (
            Sale.objects.filter(user=request.user)
            .select_related("product")
            .prefetch_related("returns")
            .order_by("-sold_at")[:5]
        )

        top_products = sorted(
            active_products, key=lambda p: p.quantity_sold, reverse=True
        )[:5]

        return Response(
            {
                "total_products": len(active_products),
                "total_remaining": sum(p.remaining_quantity for p in active_products),
                "total_sold": sum(p.quantity_sold for p in products),
                "total_revenue": sum(
                    (p.revenue for p in products), Decimal("0.00")
                ),
                "total_profit": sum(
                    (p.profit for p in products), Decimal("0.00")
                ),
                "total_loss": sum(
                    (p.loss for p in products), Decimal("0.00")
                ),
                "recent_sales": SaleSerializer(recent_sales, many=True).data,
                "top_products": ProductSerializer(top_products, many=True, context={"request": request}).data,
            }
        )


class ProductImageUploadView(APIView):
    """Upload one or more gallery photos after validating the whole batch."""

    def post(self, request, pk):
        product = get_object_or_404(
            Product, id=pk, user=request.user, is_archived=False
        )
        images = []
        for key in ("images", "uploaded_images", "image"):
            if key in request.data:
                images = request.data.getlist(key) if hasattr(request.data, "getlist") else request.data[key]
                if not isinstance(images, list):
                    images = [images]
                break
        if not images:
            raise ValidationError({"images": "Не передано ни одного изображения"})

        serializer = ProductSerializer(
            product, data={"images": images}, partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(
            {
                "message": f"Успешно добавлено изображений: {len(images)}",
                "images": ProductImageSerializer(
                    product.images.all(), many=True, context={"request": request}
                ).data,
                "product": ProductSerializer(product, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProductImageDeleteView(APIView):
    """Delete a gallery photo without overwriting concurrent inventory changes."""

    def delete(self, request, pk, image_id):
        with transaction.atomic():
            product = get_object_or_404(
                Product.objects.select_for_update(),
                id=pk, user=request.user, is_archived=False,
            )
            # A legacy single main image is represented by gallery id 0.
            if image_id == 0 and product.image and not product.images.exists():
                product.image = None
            else:
                img_obj = get_object_or_404(ProductImage, id=image_id, product=product)
                was_main = bool(
                    product.image and img_obj.image.name == product.image.name
                )
                img_obj.delete()
                if was_main:
                    remaining = product.images.first()
                    product.image = remaining.image if remaining else None
            product.save(update_fields=["image", "updated_at"])

        return Response(
            {
                "message": "Изображение удалено",
                "images": ProductImageSerializer(
                    product.images.all(), many=True, context={"request": request}
                ).data,
                "product": ProductSerializer(product, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )
