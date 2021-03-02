# Generated by Django 3.1.4 on 2021-02-27 06:39

from django.db import migrations, models
import django.db.models.deletion
import imagekit.models.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Story',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('story_profile', models.BooleanField(default=0)),
                ('title', models.CharField(max_length=200, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'stories',
            },
        ),
        migrations.CreateModel(
            name='StoryAttachFiles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_type', models.CharField(max_length=100)),
                ('path', models.ImageField(upload_to='files/%Y%m%d')),
                ('thumbnail_path', imagekit.models.fields.ProcessedImageField(upload_to='thumbnail')),
            ],
            options={
                'db_table': 'story_attach_files',
            },
        ),
        migrations.CreateModel(
            name='StoryRead',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('story_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='stories.story')),
            ],
            options={
                'db_table': 'story_reads',
            },
        ),
    ]
