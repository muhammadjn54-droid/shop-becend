from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Product

User = get_user_model()


class BaseTestCase(APITestCase):
    """Общая настройка: создаём двух пользователей и авторизуем первого."""

    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="Str0ngPass!123")
        self.other_user = User.objects.create_user(username="bob", password="Str0ngPass!123")

        self.client.force_authenticate(user=self.user)

        self.product = Product.objects.create(
            user=self.user,
            name="Coca-Cola",
            arrival_date="2026-09-27",
            quantity_received=20,
            purchase_price=Decimal("8.00"),
            selling_price=Decimal("10.00"),
        )


class ProductCreationTests(BaseTestCase):
    def test_create_product(self):
        """1. Создание товара работает и возвращает верные вычисляемые поля."""
        url = reverse("product-list-create")
        data = {
            "name": "Fanta",
            "arrival_date": "2026-09-27",
            "quantity_received": 15,
            "purchase_price": "5.00",
            "selling_price": "7.00",
        }
        response = self.client.post(url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["remaining_quantity"], 15)
        self.assertEqual(Decimal(response.data["revenue"]), Decimal("0.00"))


class ProductSaleTests(BaseTestCase):
    def test_sell_product_reduces_stock(self):
        """2 и 3. Продажа товара уменьшает остаток автоматически."""
        url = reverse("product-sell", args=[self.product.id])
        response = self.client.post(url, {"quantity": 3}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_sold, 3)
        self.assertEqual(self.product.remaining_quantity, 17)

    def test_cannot_sell_more_than_available(self):
        """4. Продажа большего количества, чем есть на складе, запрещена."""
        url = reverse("product-sell", args=[self.product.id])
        response = self.client.post(url, {"quantity": 999}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_profit_calculation(self):
        """5. Прибыль рассчитывается верно: (10-8)*3 = 6."""
        url = reverse("product-sell", args=[self.product.id])
        response = self.client.post(url, {"quantity": 3}, format="json")

        self.product.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.profit, Decimal("6.00"))
        self.assertEqual(self.product.loss, Decimal("0.00"))

    def test_loss_calculation(self):
        """6. Убыток рассчитывается верно, если цена продажи ниже закупочной."""
        loss_product = Product.objects.create(
            user=self.user,
            name="Товар с убытком",
            arrival_date="2026-09-27",
            quantity_received=10,
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("8.00"),
        )
        url = reverse("product-sell", args=[loss_product.id])
        self.client.post(url, {"quantity": 3}, format="json")

        loss_product.refresh_from_db()
        self.assertEqual(loss_product.profit, Decimal("0.00"))
        self.assertEqual(loss_product.loss, Decimal("6.00"))

    def test_cannot_sell_zero_or_negative_quantity(self):
        url = reverse("product-sell", args=[self.product.id])
        response = self.client.post(url, {"quantity": 0}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductOwnershipTests(BaseTestCase):
    def test_cannot_access_other_users_product(self):
        """7. Пользователь не должен видеть или изменять чужой товар."""
        self.client.force_authenticate(user=self.other_user)

        detail_url = reverse("product-detail", args=[self.product.id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        sell_url = reverse("product-sell", args=[self.product.id])
        response = self.client.post(sell_url, {"quantity": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_list_only_shows_own_products(self):
        Product.objects.create(
            user=self.other_user,
            name="Чужой товар",
            arrival_date="2026-09-27",
            quantity_received=5,
            purchase_price=Decimal("1.00"),
            selling_price=Decimal("2.00"),
        )
        url = reverse("product-list-create")
        response = self.client.get(url)
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Coca-Cola", names)
        self.assertNotIn("Чужой товар", names)


class ProductStockAndReturnTests(BaseTestCase):
    def test_add_stock_increases_quantity_received(self):
        url = reverse("product-add-stock", args=[self.product.id])
        response = self.client.post(url, {"quantity": 10}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_received, 30)

    def test_return_reduces_quantity_sold(self):
        sell_url = reverse("product-sell", args=[self.product.id])
        self.client.post(sell_url, {"quantity": 5}, format="json")

        return_url = reverse("product-return", args=[self.product.id])
        response = self.client.post(return_url, {"quantity": 1}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_sold, 4)

    def test_cannot_return_more_than_sold(self):
        return_url = reverse("product-return", args=[self.product.id])
        response = self.client.post(return_url, {"quantity": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
