from django.urls import path

from .views import SaleListView, SaleDetailView

urlpatterns = [
    path("sales/", SaleListView.as_view(), name="sale-list"),
    path("sales/<int:pk>/", SaleDetailView.as_view(), name="sale-detail"),
]
