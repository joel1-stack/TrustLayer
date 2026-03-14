from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MpesaPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=15)),
                ('checkout_request_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('merchant_request_id', models.CharField(blank=True, max_length=100, null=True)),
                ('mpesa_receipt_number', models.CharField(blank=True, max_length=50, null=True)),
                ('result_code', models.IntegerField(blank=True, null=True)),
                ('result_desc', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('transaction', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mpesa_payment', to='api.transaction')),
            ],
            options={
                'db_table': 'mpesa_payments',
                'ordering': ['-created_at'],
            },
        ),
    ]
