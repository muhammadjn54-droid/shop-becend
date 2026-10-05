import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0004_product_archive"),
        ("sales", "0002_sale_snapshots_and_returns"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sale",
            name="product",
            field=models.ForeignKey(
                to="products.product",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sales",
            ),
        ),
        migrations.AlterField(
            model_name="salereturn",
            name="product",
            field=models.ForeignKey(
                to="products.product",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="sale_returns",
            ),
        ),
    ]
