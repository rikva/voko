# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-05-02 08:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ordering', '0072_orderround_reminder_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderround',
            name='reminder_hours_before_close',
            field=models.IntegerField(default=12, help_text='Number of hours before closing time when order reminder mail will be sent'),
        ),
        migrations.AlterField(
            model_name='orderround',
            name='closed_for_orders',
            field=models.DateTimeField(help_text='When this order round will close'),
        ),
        migrations.AlterField(
            model_name='orderround',
            name='collect_datetime',
            field=models.DateTimeField(help_text='When the products can be collected'),
        ),
        migrations.AlterField(
            model_name='orderround',
            name='open_for_orders',
            field=models.DateTimeField(help_text='When this order round will open'),
        ),
        migrations.AlterField(
            model_name='orderround',
            name='order_placed',
            field=models.BooleanField(default=False, editable=False, help_text='Whether the order was placed at our suppliers'),
        ),
        migrations.AlterField(
            model_name='orderround',
            name='reminder_sent',
            field=models.BooleanField(default=False, editable=False, help_text="Whether we've sent order reminders to our members"),
        ),
    ]
