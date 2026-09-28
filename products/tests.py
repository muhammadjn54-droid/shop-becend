from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Product
from sales.models import Sale

import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class BaseTestCase(APITestCase):
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

    def generate_image_file(self, name="test.png"):
        file_obj = io.BytesIO()
        image = Image.new("RGBA", size=(50, 50), color=(255, 0, 0))
        image.save(file_obj, "png")
        file_obj.seek(0)
        return SimpleUploadedFile(name, file_obj.read(), content_type="image/png")


class ProductCreationTests(BaseTestCase):
    def test_create_product(self):
        response = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Fanta",
                "arrival_date": "2026-09-27",
                "quantity_received": 15,
                "purchase_price": "5.00",
                "selling_price": "7.00",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["remaining_quantity"], 15)

    def test_create_product_with_image_file(self):
        img = self.generate_image_file("sample.png")
        response = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Sprite",
                "arrival_date": "2026-09-27",
                "quantity_received": 10,
                "purchase_price": "6.00",
                "selling_price": "8.00",
                "image": img,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["image"])
        media_response = self.client.get(response.data["image"])
        self.assertEqual(media_response.status_code, status.HTTP_200_OK)

    def test_create_product_with_base64_image(self):
        base64_png = (
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        response = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Pepsi",
                "arrival_date": "2026-09-27",
                "quantity_received": 10,
                "purchase_price": "5.00",
                "selling_price": "7.00",
                "image": base64_png,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["image"])

    def test_create_product_with_empty_image_string(self):
        response = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Mirinda",
                "arrival_date": "2026-09-27",
                "quantity_received": 10,
                "purchase_price": "5.00",
                "selling_price": "7.00",
                "image": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["image"])

    def test_patch_product_preserves_existing_image_when_string_or_empty_passed(self):
        img = self.generate_image_file("photo.png")
        create_resp = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Water",
                "arrival_date": "2026-09-27",
                "quantity_received": 10,
                "purchase_price": "2.00",
                "selling_price": "3.00",
                "image": img,
            },
            format="multipart",
        )
        prod_id = create_resp.data["id"]
        original_image = create_resp.data["image"]

        # 1. PATCH с передачей того же URL не падает
        patch_resp = self.client.patch(
            reverse("product-detail", args=[prod_id]),
            {"name": "Water Sparkling", "image": original_image},
            format="json",
        )
        # 2. PATCH с пустой строкой не удаляет фото
        patch_resp2 = self.client.patch(
            reverse("product-detail", args=[prod_id]),
            {"image": ""},
            format="json",
        )
        self.assertEqual(patch_resp2.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(patch_resp2.data["image"])

    def test_create_product_with_more_than_five_images(self):
        # Проверяем загрузку 6 фотографий (> 5 фото)
        images = [self.generate_image_file(f"img_{i}.png") for i in range(6)]
        response = self.client.post(
            reverse("product-list-create"),
            {
                "name": "Nike Air Max",
                "arrival_date": "2026-09-27",
                "quantity_received": 10,
                "purchase_price": "50.00",
                "selling_price": "100.00",
                "images": images,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["image"])
        self.assertEqual(len(response.data["images"]), 6)

    def test_upload_and_delete_product_images(self):
        # 1. Загрузка дополнительных 3 фото к существующему товару
        extra_images = [self.generate_image_file(f"extra_{i}.png") for i in range(3)]
        upload_resp = self.client.post(
            reverse("product-images-upload", args=[self.product.id]),
            {"images": extra_images},
            format="multipart",
        )
        self.assertEqual(upload_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(upload_resp.data["images"]), 3)

        image_id = upload_resp.data["images"][0]["id"]

        # 2. Удаление конкретного фото
        del_resp = self.client.delete(
            reverse("product-images-delete", args=[self.product.id, image_id])
        )
        self.assertEqual(del_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(del_resp.data["images"]), 2)

    def test_cannot_reduce_received_below_sold(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 5},
            format="json",
        )
        response = self.client.patch(
            reverse("product-detail", args=[self.product.id]),
            {"quantity_received": 4},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductSaleTests(BaseTestCase):
    def test_sell_product_reduces_stock_and_calculates_profit(self):
        response = self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_sold, 3)
        self.assertEqual(self.product.remaining_quantity, 17)
        self.assertEqual(self.product.revenue, Decimal("30.00"))
        self.assertEqual(self.product.sold_cost, Decimal("24.00"))
        self.assertEqual(self.product.profit, Decimal("6.00"))
        self.assertEqual(self.product.loss, Decimal("0.00"))

    def test_custom_sale_price_is_used_in_product_totals(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 3, "price_per_item": "9.00"},
            format="json",
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.revenue, Decimal("27.00"))
        self.assertEqual(self.product.sold_cost, Decimal("24.00"))
        self.assertEqual(self.product.profit, Decimal("3.00"))

    def test_sale_snapshot_does_not_change_after_purchase_price_update(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 3},
            format="json",
        )
        sale = Sale.objects.get(product=self.product)
        self.assertEqual(sale.purchase_price_per_item, Decimal("8.00"))
        self.assertEqual(sale.cost_amount, Decimal("24.00"))

        self.client.post(
            reverse("product-add-stock", args=[self.product.id]),
            {"quantity": 10, "purchase_price": "12.00"},
            format="json",
        )

        sale.refresh_from_db()
        self.assertEqual(sale.purchase_price_per_item, Decimal("8.00"))
        self.assertEqual(sale.cost_amount, Decimal("24.00"))
        self.assertEqual(sale.profit, Decimal("6.00"))

    def test_cannot_sell_more_than_available(self):
        response = self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_loss_calculation(self):
        loss_product = Product.objects.create(
            user=self.user,
            name="Loss product",
            arrival_date="2026-09-27",
            quantity_received=10,
            purchase_price=Decimal("10.00"),
            selling_price=Decimal("8.00"),
        )
        self.client.post(
            reverse("product-sell", args=[loss_product.id]),
            {"quantity": 3},
            format="json",
        )
        loss_product.refresh_from_db()
        self.assertEqual(loss_product.revenue, Decimal("24.00"))
        self.assertEqual(loss_product.sold_cost, Decimal("30.00"))
        self.assertEqual(loss_product.profit, Decimal("0.00"))
        self.assertEqual(loss_product.loss, Decimal("6.00"))


class ProductReturnTests(BaseTestCase):
    def test_return_updates_stock_and_financial_totals(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 3},
            format="json",
        )
        response = self.client.post(
            reverse("product-return", args=[self.product.id]),
            {"quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_sold, 2)
        self.assertEqual(self.product.remaining_quantity, 18)
        self.assertEqual(self.product.revenue, Decimal("20.00"))
        self.assertEqual(self.product.sold_cost, Decimal("16.00"))
        self.assertEqual(self.product.profit, Decimal("4.00"))

    def test_cannot_return_more_than_available(self):
        self.client.post(
            reverse("product-sell", args=[self.product.id]),
            {"quantity": 2},
            format="json",
        )
        response = self.client.post(
            reverse("product-return", args=[self.product.id]),
            {"quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductOwnershipTests(BaseTestCase):
    def test_other_user_cannot_access_product(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(reverse("product-detail", args=[self.product.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_product_list_only_shows_own_products(self):
        Product.objects.create(
            user=self.other_user,
            name="Other product",
            arrival_date="2026-09-27",
            quantity_received=5,
            purchase_price=Decimal("1.00"),
            selling_price=Decimal("2.00"),
        )
        response = self.client.get(reverse("product-list-create"))
        names = [item["name"] for item in response.data["results"]]
        self.assertIn("Coca-Cola", names)
        self.assertNotIn("Other product", names)
