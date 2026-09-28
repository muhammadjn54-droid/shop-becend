from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill_sale_snapshots(apps, schema_editor):
    Sale = apps.get_model("sales", "Sale")

    for sale in Sale.objects.all().iterator():
        cost_amount = sale.total_amount - sale.profit + sale.loss

        if sale.quantity:
            purchase_price = (cost_amount / sale.quantity).quantize(
                Decimal("0.01")
            )
        else:
            purchase_price = Decimal("0.00")

        sale.cost_amount = cost_amount
        sale.purchase_price_per_item = purchase_price
        sale.save(
            update_fields=[
                "cost_amount",
                "purchase_price_per_item",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("sales", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="purchase_price_per_item",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=12,
                verbose_name="Закупочная цена за 1 шт. на момент продажи",
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="cost_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=14,
                verbose_name="Себестоимость продажи",
            ),
        ),
        migrations.RunPython(
            backfill_sale_snapshots,
            migrations.RunPython.noop,
        ),
        migrations.CreateModel(
            name="SaleReturn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "quantity",
                    models.PositiveIntegerField(
                        verbose_name="Возвращено штук"
                    ),
                ),
                (
                    "refund_amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                    ),
                ),
                (
                    "returned_cost",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=14,
                    ),
                ),
                (
                    "profit_reversal",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=14,
                    ),
                ),
                (
                    "loss_reversal",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=14,
                    ),
                ),
                (
                    "returned_at",
                    models.DateTimeField(
                        auto_now_add=True
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sale_returns",
                        to="products.product",
                    ),
                ),
                (
                    "sale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="returns",
                        to="sales.sale",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sale_returns",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-returned_at"],
            },
        ),
    ]
