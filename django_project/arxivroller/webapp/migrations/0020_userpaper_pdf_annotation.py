# Generated by Django 3.1.5 on 2021-02-21 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0019_auto_20210220_1656'),
    ]

    operations = [
        migrations.AddField(
            model_name='userpaper',
            name='pdf_annotation',
            field=models.JSONField(null=True),
        ),
    ]
