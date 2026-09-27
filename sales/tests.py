from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product

User = get_user_model()


class SaleListTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="Str0ngPass!123")
        self.client.force_authenticate(user=self.user)
        self.product = Product.objects.create(
            user=self.user,
            name="Coca-Cola",
            arrival_date="2026-09-27",
            quantity_received=20,
            purchase_price=Decimal("8.00"),
            selling_price=Decimal("10.00"),
        )

    def test_sale_appears_in_sales_list(self):
        sell_url = reverse("product-sell", args=[self.product.id])
        self.client.post(sell_url, {"quantity": 2}, format="json")

        list_url = reverse("sale-list")
        response = self.client.get(list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
