# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-05-20 10:08


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0060_auto_20160517_2023'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderproduct',
            name='base_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text=b'The price the product was bought for', max_digits=6, null=True),
        ),
    ]
