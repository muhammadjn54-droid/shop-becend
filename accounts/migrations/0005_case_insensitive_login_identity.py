from django.db import migrations, models
from django.db.models.functions import Lower


def check_existing_identifiers(apps, schema_editor):
    User = apps.get_model("accounts", "CustomUser")
    owners = {}
    for user_id, username, email in User.objects.using(schema_editor.connection.alias).values_list(
        "pk", "username", "email"
    ).iterator():
        for value in (username, email):
            if not value:
                continue
            normalized = value.lower()
            if normalized in owners and owners[normalized] != user_id:
                raise RuntimeError(
                    "Conflicting login identifiers exist. Review account IDs "
                    f"{owners[normalized]} and {user_id}, assign distinct usernames/emails, "
                    "then rerun migrate. No account data has been changed."
                )
            owners[normalized] = user_id


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_create_default_user")]
    operations = [
        migrations.RunPython(check_existing_identifiers, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="customuser",
            constraint=models.UniqueConstraint(Lower("username"), name="accounts_username_ci_unique"),
        ),
        migrations.AddConstraint(
            model_name="customuser",
            constraint=models.UniqueConstraint(Lower("email"), name="accounts_email_ci_unique"),
        ),
    ]
