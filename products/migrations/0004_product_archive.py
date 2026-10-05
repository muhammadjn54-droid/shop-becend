from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0003_product_barcode_product_unique_barcode_per_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_archived",
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.RemoveConstraint(
            model_name="product", name="unique_barcode_per_user",
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(
                fields=("user", "barcode"),
                condition=(
                    models.Q(barcode__isnull=False, is_archived=False)
                    & ~models.Q(barcode="")
                ),
                name="unique_barcode_per_user",
            ),
        ),
    ]
