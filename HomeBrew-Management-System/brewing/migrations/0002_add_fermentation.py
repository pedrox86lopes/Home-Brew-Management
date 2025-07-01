# Generated migration for fermentation models

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('brewing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FermentationNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('note_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('is_public', models.BooleanField(default=False)),
                ('krausen_activity', models.CharField(blank=True, choices=[('none', 'No Activity'), ('light', 'Light Activity'), ('moderate', 'Moderate Activity'), ('vigorous', 'Vigorous Activity'), ('peaked', 'Peaked'), ('falling', 'Falling')], max_length=50, null=True)),
                ('aroma_notes', models.TextField(blank=True, help_text='Aroma observations')),
                ('color_notes', models.TextField(blank=True, help_text='Color/appearance notes')),
                ('brew_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='brewing.brewsession')),
            ],
            options={
                'ordering': ['-note_date'],
            },
        ),
        migrations.CreateModel(
            name='FermentationPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('photo', models.ImageField(upload_to='fermentation_photos/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('photo_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('brew_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='brewing.brewsession')),
                ('fermentation_note', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='brewing.fermentationnote')),
            ],
            options={
                'ordering': ['-photo_date'],
            },
        ),
        migrations.CreateModel(
            name='FermentationAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('alert_type', models.CharField(choices=[('temperature', 'Temperature Alert'), ('gravity', 'Gravity Reading Due'), ('fermentation_complete', 'Fermentation Complete'), ('secondary', 'Secondary Fermentation'), ('dry_hop', 'Dry Hop Addition'), ('packaging', 'Ready for Packaging'), ('custom', 'Custom Reminder')], max_length=30)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('alert_date', models.DateTimeField()),
                ('is_sent', models.BooleanField(default=False)),
                ('is_dismissed', models.BooleanField(default=False)),
                ('brew_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='brewing.brewsession')),
            ],
            options={
                'ordering': ['alert_date'],
            },
        ),
    ]