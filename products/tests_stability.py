import io
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.deletion import ProtectedError
from PIL import Image
from rest_framework import serializers
from rest_framework.test import APITestCase

from .models import Product
from .serializers import ProductSerializer
from sales.models import Sale


class InventoryStabilityTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="inventory-test", password="Strong-password123!")
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(user=self.user, name="Test product", barcode="123", arrival_date="2026-10-04", quantity_received=10, purchase_price=5, selling_price=10)
        self.url = f"/api/products/{self.product.pk}/"

    def image(self):
        data = io.BytesIO()
        Image.new("RGB", (2, 2)).save(data, format="PNG")
        return SimpleUploadedFile("test.png", data.getvalue(), content_type="image/png")

    def sell(self, quantity=2):
        response = self.client.post(self.url + "sell/", {"quantity": quantity})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["sale"]

    def test_stale_serializer_cannot_overwrite_concurrent_sale(self):
        edit = ProductSerializer(self.product, data={"name": "New name"}, partial=True)
        self.assertTrue(edit.is_valid(), edit.errors)
        self.sell()
        edit.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_sold, 2)
        self.assertEqual(self.product.remaining_quantity, 8)

    def test_stale_quantity_edit_revalidates_after_lock(self):
        edit = ProductSerializer(self.product, data={"quantity_received": 1}, partial=True)
        self.assertTrue(edit.is_valid(), edit.errors)
        self.sell()
        with self.assertRaises(serializers.ValidationError):
            edit.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_received, 10)

    def test_edit_version_conflict_preserves_stock(self):
        timestamp = (self.product.updated_at - timedelta(days=1)).isoformat()
        self.client.post(self.url + "add-stock/", {"quantity": 3})
        response = self.client.patch(self.url, {"quantity_received": 10, "expected_updated_at": timestamp})
        self.assertEqual(response.status_code, 400)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity_received, 13)

    def test_archival_preserves_history_and_totals_and_allows_returns(self):
        sale = self.sell()
        before = self.client.get("/api/statistics/").data
        self.assertEqual(self.client.delete(self.url).status_code, 204)
        self.assertEqual(self.client.get("/api/products/").data["count"], 0)
        self.assertTrue(Sale.objects.filter(pk=sale["id"]).exists())
        self.assertEqual(self.client.get("/api/statistics/").data["total_revenue"], before["total_revenue"])
        self.assertEqual(self.client.post(self.url + "sell/", {"quantity": 1}).status_code, 404)
        returned = self.client.post(self.url + "return/", {"quantity": 1, "sale_id": sale["id"]})
        self.assertEqual(returned.status_code, 200, returned.data)
        self.assertEqual(self.client.get("/api/statistics/").data["total_revenue"], Decimal("10.00"))
        with self.assertRaises(ProtectedError):
            self.product.delete()

    def test_sales_and_low_stock_search(self):
        self.sell(7)
        self.assertEqual(self.client.get("/api/sales/?search=missing").data["count"], 0)
        self.assertEqual(self.client.get("/api/sales/?search=Test").data["count"], 1)
        self.assertEqual(self.client.get("/api/products/low-stock/?search=missing").data["count"], 0)
        self.assertEqual(self.client.get("/api/products/low-stock/?search=123").data["count"], 1)

    def test_invalid_gallery_is_rejected_before_product_write(self):
        response = self.client.patch(self.url, {"name": "Should not save", "images": [self.image(), SimpleUploadedFile("bad.png", b"not an image")]}, format="multipart")
        self.assertEqual(response.status_code, 400, response.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Test product")
        self.assertEqual(self.product.images.count(), 0)

    def test_external_image_urls_do_not_make_network_requests(self):
        with patch("urllib.request.urlopen") as network:
            response = self.client.patch(self.url, {"image": "http://127.0.0.1/internal"})
        self.assertEqual(response.status_code, 400)
        network.assert_not_called()

    def test_oversize_gallery_image_is_rejected(self):
        file = SimpleUploadedFile("big.png", b"x" * (5 * 1024 * 1024 + 1), content_type="image/png")
        response = self.client.post(self.url + "images/", {"images": [file]}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.product.images.count(), 0)

    def test_storage_failure_does_not_partially_edit_product(self):
        with self.assertLogs("products.serializers", level="ERROR"), patch("django.core.files.storage.FileSystemStorage._save", side_effect=OSError("storage unavailable")):
            response = self.client.patch(self.url, {"name": "Should not save", "images": [self.image()]}, format="multipart")
        self.assertEqual(response.status_code, 503)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Test product")
        self.assertEqual(self.product.images.count(), 0)

    def test_returned_sale_exposes_net_financial_values(self):
        sale = self.sell()
        self.client.post(self.url + "return/", {"quantity": 1, "sale_id": sale["id"]})
        data = self.client.get(f"/api/sales/{sale['id']}/").data
        self.assertEqual(data["net_total_amount"], "10.00")
        self.assertEqual(data["net_cost_amount"], "5.00")
        self.assertEqual(data["net_profit"], "5.00")
