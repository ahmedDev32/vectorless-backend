from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('knowledge', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX IF NOT EXISTS knowledge_chunk_content_fts_idx "
                "ON knowledge_chunk USING GIN (to_tsvector('english', content));"
            ),
            reverse_sql="DROP INDEX IF EXISTS knowledge_chunk_content_fts_idx;",
        ),
    ]
