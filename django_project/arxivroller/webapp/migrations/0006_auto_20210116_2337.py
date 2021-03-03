# Generated by Django 3.1.5 on 2021-01-17 04:37

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('webapp', '0005_auto_20210115_2250'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userpreference',
            name='id',
        ),
        migrations.AlterField(
            model_name='userpreference',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='UserPaper',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read', models.BooleanField(default=False)),
                ('paper', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='webapp.paper')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
