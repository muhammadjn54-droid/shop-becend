import base64
import binascii
import logging
import uuid
from contextlib import contextmanager
from decimal import Decimal

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import FileExtensionValidator
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import Product, ProductImage, validate_image_size

logger = logging.getLogger(__name__)


class ImageStorageError(APIException):
    status_code = 503
    default_detail = "Не удалось сохранить фотографии. Попробуйте ещё раз."


@contextmanager
def product_write():
    """Roll back records and remove new uploads if a product write fails."""
    uploaded_files = []
    try:
        with transaction.atomic():
            yield uploaded_files
    except Exception as exc:
        for uploaded in uploaded_files:
            if uploaded.name and uploaded._committed:
                try:
                    uploaded.storage.delete(uploaded.name)
                except Exception:
                    logger.exception("Could not remove an abandoned product image")
        if isinstance(exc, IntegrityError):
            # A concurrent request may win the barcode uniqueness race.
            if "unique_barcode_per_user" in str(exc) or (
                "products_product.user_id" in str(exc)
                and "products_product.barcode" in str(exc)
            ):
                raise serializers.ValidationError(
                    {"barcode": "Товар с таким штрихкодом уже существует"}
                ) from exc
        raise


def save_image_record(instance, uploaded_files):
    uploaded_files.append(instance.image)
    try:
        # Separate storage failures from database errors.
        if instance.image and not instance.image._committed:
            instance.image.save(instance.image.name, instance.image.file, save=False)
    except Exception as exc:
        logger.exception("Product image storage failed")
        raise ImageStorageError() from exc
    instance.save()


class FlexibleImageField(serializers.ImageField):
    """Accept uploads/base64 and exact references to the current main image."""

    def __init__(self, **kwargs):
        validators = list(kwargs.pop("validators", []))
        validators.extend([
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_image_size,
        ])
        super().__init__(validators=validators, **kwargs)

    def to_internal_value(self, data):
        instance = getattr(self.parent, "instance", None)
        current = getattr(instance, "image", None)
        if isinstance(data, str):
            data = data.strip()
            if data in ("", "null", "undefined"):
                if current:
                    raise serializers.SkipField()
                if self.allow_null:
                    raise serializers.SkipField()
                raise serializers.ValidationError("Передайте изображение.")

            if current:
                references = {current.name, current.url}
                request = self.context.get("request")
                if request is not None:
                    references.add(request.build_absolute_uri(current.url))
                if data in references:
                    # Keep the fresh image on the locked row, not a stale copy.
                    raise serializers.SkipField()

            if data.startswith("data:image/"):
                try:
                    header, encoded = data.split(";base64,", 1)
                    extension = header.removeprefix("data:image/").lower()
                    if extension not in {"jpg", "jpeg", "png", "webp"}:
                        raise ValueError("Unsupported image type")
                    max_size = settings.MAX_IMAGE_SIZE_MB * 1024 * 1024
                    if len(encoded) > 4 * ((max_size + 2) // 3):
                        raise serializers.ValidationError(
                            f"Размер изображения не должен превышать {settings.MAX_IMAGE_SIZE_MB} MB"
                        )
                    data = ContentFile(
                        base64.b64decode(encoded, validate=True),
                        name=f"{uuid.uuid4().hex}.{extension}",
                    )
                except (ValueError, binascii.Error) as exc:
                    raise serializers.ValidationError("Некорректное base64 изображение.") from exc
            else:
                raise serializers.ValidationError(
                    "Загрузите файл изображения. Загрузка по внешней ссылке не поддерживается."
                )

        # Check size before Pillow parses the supplied file.
        if hasattr(data, "size"):
            self.run_validators(data)
        return super().to_internal_value(data)


class ProductImageSerializer(serializers.ModelSerializer):
    image = FlexibleImageField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "created_at")
        read_only_fields = fields


class ProductSerializer(serializers.ModelSerializer):
    image = FlexibleImageField(required=False, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)
    expected_updated_at = serializers.DateTimeField(required=False, write_only=True)
    barcode = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True,
        trim_whitespace=True,
        help_text="Штрихкод товара (строка). Уникален в пределах пользователя.",
    )
    remaining_quantity = serializers.IntegerField(read_only=True)
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    sold_cost = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    loss = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    profit_per_item = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "name", "barcode", "image", "images", "arrival_date",
            "quantity_received", "quantity_sold", "remaining_quantity",
            "purchase_price", "selling_price", "revenue", "sold_cost", "profit",
            "loss", "profit_per_item", "is_archived", "created_at", "updated_at",
            "expected_updated_at",
        )
        read_only_fields = (
            "id", "images", "quantity_sold", "remaining_quantity", "revenue",
            "sold_cost", "profit", "loss", "profit_per_item", "is_archived",
            "created_at", "updated_at",
        )

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)
        # Responses contain gallery objects; requests accept JSON arrays or
        # repeated multipart files under either established input key.
        for key in ("images", "uploaded_images"):
            if key not in data:
                continue
            images = data.getlist(key) if hasattr(data, "getlist") else data[key]
            if not isinstance(images, list):
                images = [images]
            try:
                validated_data["uploaded_images"] = serializers.ListField(
                    child=FlexibleImageField(),
                ).run_validation(images)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({"images": exc.detail}) from exc
            break
        return validated_data

    @staticmethod
    def _save_multiple_images(product, images, uploaded_files):
        for image in images:
            save_image_record(ProductImage(product=product, image=image), uploaded_files)
        if not product.image:
            first = product.images.first()
            if first:
                product.image = first.image
                product.save(update_fields=["image"])

    def create(self, validated_data):
        images = validated_data.pop("uploaded_images", [])
        validated_data.pop("expected_updated_at", None)
        with product_write() as uploaded_files:
            product = Product(**validated_data)
            if product.image:
                save_image_record(product, uploaded_files)
            else:
                product.save()
            self._save_multiple_images(product, images, uploaded_files)
        return product

    def update(self, instance, validated_data):
        images = validated_data.pop("uploaded_images", [])
        expected = validated_data.pop("expected_updated_at", None)
        with product_write() as uploaded_files:
            product = Product.objects.select_for_update().get(pk=instance.pk)
            if product.is_archived:
                raise serializers.ValidationError("Товар находится в архиве.")
            if expected is not None and product.updated_at != expected:
                raise serializers.ValidationError(
                    "Товар изменился. Обновите страницу и повторите изменения."
                )
            if validated_data.get("quantity_received", product.quantity_received) < product.quantity_sold:
                raise serializers.ValidationError({
                    "quantity_received": "Количество поступившего товара не может быть меньше уже проданного"
                })
            for key, value in validated_data.items():
                setattr(product, key, value)
            if validated_data.get("image"):
                save_image_record(product, uploaded_files)
            else:
                product.save()
            self._save_multiple_images(product, images, uploaded_files)
        return product

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not ret["images"] and ret.get("image"):
            ret["images"] = [{"id": 0, "image": ret["image"]}]
        return ret

    def _resolve_owner(self):
        if self.instance is not None and getattr(self.instance, "user_id", None):
            return self.instance.user
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is not None and not getattr(user, "is_authenticated", False):
            return None
        return user

    def validate_barcode(self, value):
        barcode = (value or "").strip()
        if not barcode:
            return None
        user = self._resolve_owner()
        if user is None:
            return barcode
        duplicates = Product.objects.filter(user=user, barcode=barcode, is_archived=False)
        if self.instance is not None and self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError("Товар с таким штрихкодом уже существует")
        return barcode

    def validate_quantity_received(self, value):
        if value < 0:
            raise serializers.ValidationError("Количество не может быть отрицательным")
        if self.instance and value < self.instance.quantity_sold:
            raise serializers.ValidationError(
                "Количество поступившего товара не может быть меньше уже проданного"
            )
        return value

    def validate_purchase_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Закупочная цена не может быть отрицательной")
        return value

    def validate_selling_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Цена продажи не может быть отрицательной")
        return value


class SellSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    price_per_item = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class AddStockSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, min_value=Decimal("0")
    )


class ReturnSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
    sale_id = serializers.IntegerField(min_value=1, required=False)
