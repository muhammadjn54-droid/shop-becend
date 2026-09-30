from django.db import migrations, models


def normalise_emails(apps, schema_editor):
    """
    Prepare existing rows before the unique constraint is applied.

    Two things would break a unique index on a nullable email:
      * empty strings - several users may have '' which collides;
      * duplicates      - two accounts may share one address.
    Empty becomes NULL (SQL allows many NULLs), and for duplicates the
    oldest account keeps the address while the others are cleared, so no
    real owner loses access to their own account.
    """
    User = apps.get_model("accounts", "CustomUser")

    User.objects.filter(email="").update(email=None)

    seen = set()
    duplicates = []
    for pk, email in User.objects.exclude(email=None).order_by("pk").values_list(
        "pk", "email"
    ):
        key = email.strip().lower()
        if key in seen:
            duplicates.append(pk)
        else:
            seen.add(key)

    if duplicates:
        User.objects.filter(pk__in=duplicates).update(email=None)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalise_emails, noop_reverse),
        migrations.AlterField(
            model_name="customuser",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
    ]
