from django.db import migrations


class Migration(migrations.Migration):
    # Retain the migration name for databases that already applied it. New
    # installations must never create or rename an administrator account.
    # Existing administrators are repaired explicitly with changepassword;
    # a migration must not delete their data or silently lock them out.
    dependencies = [("accounts", "0003_alter_customuser_managers")]
    operations = []