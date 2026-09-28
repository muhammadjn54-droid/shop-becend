from rest_framework import generics

from .models import Sale
from .serializers import SaleSerializer


class SaleListView(generics.ListAPIView):
    serializer_class = SaleSerializer
    ordering_fields = ["sold_at", "total_amount", "profit", "loss"]

    def get_queryset(self):
        return (
            Sale.objects.filter(user=self.request.user)
            .select_related("product")
            .prefetch_related("returns")
        )


class SaleDetailView(generics.RetrieveAPIView):
    serializer_class = SaleSerializer

    def get_queryset(self):
        return (
            Sale.objects.filter(user=self.request.user)
            .select_related("product")
            .prefetch_related("returns")
        )
