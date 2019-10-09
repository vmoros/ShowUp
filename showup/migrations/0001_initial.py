# Generated by Django 2.2.5 on 2019-10-09 13:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Concert',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('datetime', models.DateTimeField()),
                ('venue_name', models.CharField(max_length=100)),
                ('borough', models.CharField(choices=[('BK', 'Brooklyn'), ('MN', 'Manhattan'), ('BX', 'The Bronx'), ('QN', 'Queens'), ('SI', 'Staten Island')], max_length=2)),
                ('performer_names', models.CharField(max_length=200)),
                ('genres', models.CharField(max_length=200)),
                ('event_url', models.URLField()),
                ('performer_image_url', models.URLField(null=True)),
            ],
        ),
    ]
