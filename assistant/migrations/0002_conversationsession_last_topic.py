from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversationsession",
            name="last_topic",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Most recent 'tell me about X' topic, for follow-up "
                    "questions like 'what about the brain?' or 'tell me more'."
                ),
                max_length=120,
            ),
        ),
    ]
