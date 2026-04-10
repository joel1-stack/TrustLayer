from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_escrow_webhooklog'),
    ]

    operations = [
        migrations.AddField(
            model_name='escrow',
            name='sender_phone',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
        migrations.AddField(
            model_name='escrow',
            name='receiver_phone',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
