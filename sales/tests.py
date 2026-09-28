from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product
from .models import Sale

User = get_user_model()


class SaleTests(APITestCase):
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

    def test_sale_appears_in_sales_list_with_snapshot(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 2, "price_per_item": "9.00"},
            format="json",
        )

        sale = Sale.objects.get(product=self.product)

        self.assertEqual(sale.purchase_price_per_item, Decimal("8.00"))
        self.assertEqual(sale.total_amount, Decimal("18.00"))
        self.assertEqual(sale.cost_amount, Decimal("16.00"))
        self.assertEqual(sale.profit, Decimal("2.00"))

        response = self.client.get(reverse("sale-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["returned_quantity"], 0)
