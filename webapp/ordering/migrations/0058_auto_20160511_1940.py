# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-05-11 17:40


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0057_auto_20160315_1106'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='order_round',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='ordering.OrderRound'),
        ),
    ]
