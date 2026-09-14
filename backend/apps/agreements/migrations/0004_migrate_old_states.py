from django.db import migrations


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('agreements', '0003_alter_agreement_status'),
    ]

    operations = [
        migrations.RunPython(noop, noop),
    ]
