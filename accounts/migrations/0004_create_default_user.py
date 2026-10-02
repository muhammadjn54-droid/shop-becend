from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_default_user(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    user = CustomUser.objects.filter(username='Maktabiman').first()
    if not user:
        old_user = CustomUser.objects.first()
        if old_user:
            old_user.username = 'Maktabiman'
            old_user.password = make_password('Mactab_2211')
            old_user.is_staff = True
            old_user.is_superuser = True
            old_user.save()
        else:
            CustomUser.objects.create(
                username='Maktabiman',
                password=make_password('Mactab_2211'),
                is_staff=True,
                is_superuser=True,
            )
    else:
        user.password = make_password('Mactab_2211')
        user.is_staff = True
        user.is_superuser = True
        user.save()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_customuser_managers'),
    ]

    operations = [
        migrations.RunPython(create_default_user, backwards),
    ]
