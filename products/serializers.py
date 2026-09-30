import base64
import os
import uuid
import urllib.request
from decimal import Decimal
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from rest_framework import serializers

from .models import Product, ProductImage


class FlexibleImageField(serializers.ImageField):
    """
    Универсальное поле для изображения товара.
    Поддерживает:
    - Загрузку файла (multipart/form-data)
    - Base64 строку (data:image/...)
    - Ссылку на фото из интернета (http://... или https://...)
    - Пустую строку ("" / "null" / "undefined")
    - Сохранение существующего фото при обновлении товара (PUT / PATCH)
    """

    def to_internal_value(self, data):
        # 1. Пустые значения
        if data in ("", "null", "undefined", None):
            if (
                self.parent
                and getattr(self.parent, "instance", None)
                and self.parent.instance.image
            ):
                return self.parent.instance.image
            return None

        # 2. Строковые данные (Base64, URL, имя существующего файла)
        if isinstance(data, str):
            clean_str = data.strip()
            if not clean_str or clean_str in ("", "null", "undefined"):
                if (
                    self.parent
                    and getattr(self.parent, "instance", None)
                    and self.parent.instance.image
                ):
                    return self.parent.instance.image
                return None

            # Проверяем, не является ли строка текущим изображением товара
            if (
                self.parent
                and getattr(self.parent, "instance", None)
                and self.parent.instance.image
            ):
                current = self.parent.instance.image
                try:
                    if (
                        clean_str == current.name
                        or (hasattr(current, "url") and current.url in clean_str)
                        or (current.name and current.name in clean_str)
                    ):
                        return current
                except Exception:
                    pass

            # Base64 изображение
            if clean_str.startswith("data:image"):
                try:
                    header, img_b64 = clean_str.split(";base64,")
                    raw_ext = header.split("/")[-1].lower()
                    if raw_ext in ("jpeg", "pjpeg"):
                        ext = "jpg"
                    elif raw_ext in ("png", "webp", "jpg"):
                        ext = raw_ext
                    else:
                        ext = "jpg"

                    file_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                    decoded = base64.b64decode(img_b64)
                    file_obj = ContentFile(decoded, name=file_name)
                    return super().to_internal_value(file_obj)
                except Exception as exc:
                    raise serializers.ValidationError(
                        f"Не удалось распознать base64 изображение: {exc}"
                    )

            # URL из интернета (http / https)
            parsed = urlparse(clean_str)
            if parsed.scheme in ("http", "https"):
                try:
                    req = urllib.request.Request(
                        clean_str, headers={"User-Agent": "Mozilla/5.0"}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        content_type = resp.headers.get("content-type", "").lower()
                        ext = "jpg"
                        if "png" in content_type:
                            ext = "png"
                        elif "webp" in content_type:
                            ext = "webp"
                        elif "jpeg" in content_type or "jpg" in content_type:
                            ext = "jpg"
                        else:
                            path_ext = os.path.splitext(parsed.path)[1].lstrip(".").lower()
                            if path_ext in ("jpg", "jpeg", "png", "webp"):
                                ext = "jpg" if path_ext == "jpeg" else path_ext

                        file_name = f"{uuid.uuid4().hex[:12]}.{ext}"
                        file_obj = ContentFile(resp.read(), name=file_name)
                        return super().to_internal_value(file_obj)
                except Exception as exc:
                    if (
                        self.parent
                        and getattr(self.parent, "instance", None)
                        and self.parent.instance.image
                    ):
                        return self.parent.instance.image
                    raise serializers.ValidationError(
                        f"Не удалось загрузить изображение по ссылке: {exc}"
                    )

        # 3. Обычный загруженный файл через форму
        return super().to_internal_value(data)


class ProductImageSerializer(serializers.ModelSerializer):
    """Сериализатор отдельной фотографии товара."""

    image = FlexibleImageField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "created_at")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.image:
            request = self.context.get("request")
            if request is not None:
                ret["image"] = request.build_absolute_uri(instance.image.url)
            else:
                try:
                    ret["image"] = instance.image.url
                except Exception:
                    pass
        return ret


class ProductSerializer(serializers.ModelSerializer):
    image = FlexibleImageField(required=False, allow_null=True)
    images = ProductImageSerializer(many=True, read_only=True)
    barcode = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
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
            "id",
            "name",
            "barcode",
            "image",
            "images",
            "arrival_date",
            "quantity_received",
            "quantity_sold",
            "remaining_quantity",
            "purchase_price",
            "selling_price",
            "revenue",
            "sold_cost",
            "profit",
            "loss",
            "profit_per_item",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "images",
            "quantity_sold",
            "remaining_quantity",
            "revenue",
            "sold_cost",
            "profit",
            "loss",
            "profit_per_item",
            "created_at",
            "updated_at",
        )

    def _save_multiple_images(self, product, images_list):
        if not images_list:
            return
        field = FlexibleImageField()
        field.bind(field_name="image", parent=self)
        for img_item in images_list:
            if not img_item:
                continue
            try:
                processed_file = field.to_internal_value(img_item)
                if processed_file:
                    ProductImage.objects.create(product=product, image=processed_file)
            except Exception:
                pass

        if not product.image and product.images.exists():
            product.image = product.images.first().image
            product.save(update_fields=["image"])

    def create(self, validated_data):
        product = super().create(validated_data)
        request = self.context.get("request")
        images_list = []
        if request is not None:
            if hasattr(request.data, "getlist"):
                images_list = (
                    request.data.getlist("images")
                    or request.data.getlist("uploaded_images")
                )
            if not images_list and "images" in request.data:
                val = request.data.get("images")
                if isinstance(val, list):
                    images_list = val
                elif val:
                    images_list = [val]
            if not images_list and hasattr(request, "FILES"):
                images_list = (
                    request.FILES.getlist("images")
                    or request.FILES.getlist("uploaded_images")
                )

        self._save_multiple_images(product, images_list)
        return product

    def update(self, instance, validated_data):
        product = super().update(instance, validated_data)
        request = self.context.get("request")
        images_list = []
        if request is not None:
            if hasattr(request.data, "getlist"):
                images_list = (
                    request.data.getlist("images")
                    or request.data.getlist("uploaded_images")
                )
            if not images_list and "images" in request.data:
                val = request.data.get("images")
                if isinstance(val, list):
                    images_list = val
                elif val:
                    images_list = [val]
            if not images_list and hasattr(request, "FILES"):
                images_list = (
                    request.FILES.getlist("images")
                    or request.FILES.getlist("uploaded_images")
                )

        if images_list:
            self._save_multiple_images(product, images_list)
        return product

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get("request")
        if instance.image:
            if request is not None:
                ret["image"] = request.build_absolute_uri(instance.image.url)
            else:
                try:
                    ret["image"] = instance.image.url
                except Exception:
                    pass

        images_qs = instance.images.all()
        if images_qs.exists():
            ret["images"] = ProductImageSerializer(
                images_qs, many=True, context=self.context
            ).data
        elif ret.get("image"):
            ret["images"] = [{"id": 0, "image": ret["image"]}]
        else:
            ret["images"] = []

        return ret

    def _resolve_owner(self):
        """Определяет владельца товара: request.user при create, instance.user при update."""
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

        duplicates = Product.objects.filter(user=user, barcode=barcode)
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
