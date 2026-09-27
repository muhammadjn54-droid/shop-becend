from rest_framework import generics

from .models import Sale
from .serializers import SaleSerializer


class SaleListView(generics.ListAPIView):
    """
    GET /api/sales/

    Список всех продаж текущего пользователя (по всем товарам).
    """

    serializer_class = SaleSerializer
    ordering_fields = ["sold_at", "total_amount", "profit", "loss"]

    def get_queryset(self):
        return Sale.objects.filter(user=self.request.user)


class SaleDetailView(generics.RetrieveAPIView):
    """
    GET /api/sales/{id}/

    Одна конкретная продажа.
    """

    serializer_class = SaleSerializer

    def get_queryset(self):
        return Sale.objects.filter(user=self.request.user)
