from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Product
from .serializers import (
    ProductSerializer,
    SellSerializer,
    AddStockSerializer,
    ReturnSerializer,
)
from sales.models import Sale
from sales.serializers import SaleSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/products/        - список товаров текущего пользователя
    POST /api/products/        - добавить новый товар (multipart/form-data для фото)
    """

    serializer_class = ProductSerializer
    search_fields = ["name"]
    ordering_fields = [
        "name",
        "arrival_date",
        "purchase_price",
        "selling_price",
        "created_at",
    ]
    filterset_fields = ["arrival_date", "name"]

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/products/{id}/  - получить один товар
    PUT    /api/products/{id}/  - полностью изменить товар
    PATCH  /api/products/{id}/  - частично изменить товар
    DELETE /api/products/{id}/  - удалить товар
    """

    serializer_class = ProductSerializer

    def get_queryset(self):
        # Пользователь видит и может менять только свои товары.
        return Product.objects.filter(user=self.request.user)


class ProductLowStockView(generics.ListAPIView):
    """
    GET /api/products/low-stock/

    Товары, остаток которых <= 5 штук.
    """

    serializer_class = ProductSerializer

    def get_queryset(self):
        ids = [
            p.id
            for p in Product.objects.filter(user=self.request.user)
            if p.remaining_quantity <= 5
        ]
        return Product.objects.filter(id__in=ids)


class ProductSalesHistoryView(generics.ListAPIView):
    """
    GET /api/products/{id}/sales/

    История продаж конкретного товара.
    """

    serializer_class = SaleSerializer

    def get_queryset(self):
        product = generics.get_object_or_404(
            Product, id=self.kwargs["pk"], user=self.request.user
        )
        return Sale.objects.filter(product=product, user=self.request.user)


class ProductSellView(APIView):
    """
    POST /api/products/{id}/sell/

    Продать товар. Если price_per_item не передан — берётся
    из Product.selling_price. Операция выполняется атомарно:
    либо и продажа, и обновление остатка выполняются вместе,
    либо не выполняется ничего.
    """

    @swagger_auto_schema(request_body=SellSerializer)
    def post(self, request, pk):
        product = generics.get_object_or_404(Product, id=pk, user=request.user)

        serializer = SellSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]
        price_per_item = serializer.validated_data.get(
            "price_per_item", product.selling_price
        )

        if quantity > product.remaining_quantity:
            return Response(
                {"detail": "Недостаточно товара на складе"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            total_amount = quantity * price_per_item
            cost = quantity * product.purchase_price

            if total_amount > cost:
                profit = total_amount - cost
                loss = Decimal("0.00")
            elif total_amount < cost:
                loss = cost - total_amount
                profit = Decimal("0.00")
            else:
                profit = Decimal("0.00")
                loss = Decimal("0.00")

            sale = Sale.objects.create(
                product=product,
                user=request.user,
                quantity=quantity,
                price_per_item=price_per_item,
                total_amount=total_amount,
                profit=profit,
                loss=loss,
            )

            product.quantity_sold += quantity
            product.save()

        return Response(
            {
                "message": "Товар успешно продан",
                "sale": SaleSerializer(sale).data,
                "product": ProductSerializer(product).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProductAddStockView(APIView):
    """
    POST /api/products/{id}/add-stock/

    Зарегистрировать поступление новой партии товара.
    Увеличивает quantity_received. Опционально можно передать
    новую purchase_price, если партия закуплена по другой цене.
    """

    @swagger_auto_schema(request_body=AddStockSerializer)
    def post(self, request, pk):
        product = generics.get_object_or_404(Product, id=pk, user=request.user)

        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]
        new_purchase_price = serializer.validated_data.get("purchase_price")

        with transaction.atomic():
            product.quantity_received += quantity
            if new_purchase_price is not None:
                product.purchase_price = new_purchase_price
            product.save()

        return Response(
            {
                "message": "Количество товара увеличено",
                "product": ProductSerializer(product).data,
            },
            status=status.HTTP_200_OK,
        )


class ProductReturnView(APIView):
    """
    POST /api/products/{id}/return/

    Оформить возврат товара. Уменьшает quantity_sold,
    но нельзя вернуть больше, чем было продано.
    """

    @swagger_auto_schema(request_body=ReturnSerializer)
    def post(self, request, pk):
        product = generics.get_object_or_404(Product, id=pk, user=request.user)

        serializer = ReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        if quantity > product.quantity_sold:
            return Response(
                {"detail": "Нельзя вернуть больше товара, чем было продано"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            product.quantity_sold -= quantity
            product.save()

        return Response(
            {
                "message": "Возврат товара успешно оформлен",
                "product": ProductSerializer(product).data,
            },
            status=status.HTTP_200_OK,
        )


class StatisticsView(APIView):
    """
    GET /api/statistics/

    Общая статистика магазина текущего пользователя.
    """

    def get(self, request):
        products = Product.objects.filter(user=request.user)

        products_count = products.count()
        total_items_received = sum(p.quantity_received for p in products)
        total_items_sold = sum(p.quantity_sold for p in products)
        total_items_remaining = sum(p.remaining_quantity for p in products)
        total_revenue = sum(p.revenue for p in products) or Decimal("0.00")
        total_cost_of_sold_goods = sum(p.sold_cost for p in products) or Decimal("0.00")
        total_profit = sum(p.profit for p in products) or Decimal("0.00")
        total_loss = sum(p.loss for p in products) or Decimal("0.00")

        return Response(
            {
                "products_count": products_count,
                "total_items_received": total_items_received,
                "total_items_sold": total_items_sold,
                "total_items_remaining": total_items_remaining,
                "total_revenue": total_revenue,
                "total_cost_of_sold_goods": total_cost_of_sold_goods,
                "total_profit": total_profit,
                "total_loss": total_loss,
            }
        )


class DashboardView(APIView):
    """
    GET /api/dashboard/

    Сводная панель: основные показатели + последние продажи +
    самые продаваемые товары.
    """

    def get(self, request):
        products = Product.objects.filter(user=request.user)

        total_products = products.count()
        total_remaining = sum(p.remaining_quantity for p in products)
        total_sold = sum(p.quantity_sold for p in products)
        total_revenue = sum(p.revenue for p in products) or Decimal("0.00")
        total_profit = sum(p.profit for p in products) or Decimal("0.00")
        total_loss = sum(p.loss for p in products) or Decimal("0.00")

        recent_sales = Sale.objects.filter(user=request.user).order_by("-sold_at")[:5]
        top_products = sorted(products, key=lambda p: p.quantity_sold, reverse=True)[:5]

        return Response(
            {
                "total_products": total_products,
                "total_remaining": total_remaining,
                "total_sold": total_sold,
                "total_revenue": total_revenue,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "recent_sales": SaleSerializer(recent_sales, many=True).data,
                "top_products": ProductSerializer(top_products, many=True).data,
            }
        )
