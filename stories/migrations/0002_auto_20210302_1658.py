# Generated by Django 3.1.4 on 2021-03-02 07:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
        ('stories', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='storyread',
            name='user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user'),
        ),
        migrations.AddField(
            model_name='storyattachfiles',
            name='story_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='story_attach_files', to='stories.story'),
        ),
        migrations.AddField(
            model_name='story',
            name='user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.user'),
        ),
    ]
