from django.urls import path

from .views import (
    ProductListCreateView,
    ProductDetailView,
    ProductLowStockView,
    ProductSalesHistoryView,
    ProductSellView,
    ProductAddStockView,
    ProductReturnView,
    StatisticsView,
    DashboardView,
)

urlpatterns = [
    path("products/low-stock/", ProductLowStockView.as_view(), name="product-low-stock"),
    path("products/", ProductListCreateView.as_view(), name="product-list-create"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:pk>/sell/", ProductSellView.as_view(), name="product-sell"),
    path("products/<int:pk>/add-stock/", ProductAddStockView.as_view(), name="product-add-stock"),
    path("products/<int:pk>/return/", ProductReturnView.as_view(), name="product-return"),
    path("products/<int:pk>/sales/", ProductSalesHistoryView.as_view(), name="product-sales-history"),
    path("statistics/", StatisticsView.as_view(), name="statistics"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
