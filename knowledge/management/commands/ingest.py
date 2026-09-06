from django.core.management.base import BaseCommand, CommandError

from ingestion.extractor import UnsupportedFileType
from ingestion.pipeline import IngestionPipeline


class Command(BaseCommand):
    help = 'Ingest one or more files into the knowledge base (Document + Chunk rows).'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+', help='File paths to ingest.')

    def handle(self, *paths, **options):
        pipeline = IngestionPipeline()
        for path in options['paths']:
            try:
                document = pipeline.ingest_file(path)
            except (UnsupportedFileType, FileNotFoundError) as exc:
                raise CommandError(f'{path}: {exc}')
            self.stdout.write(
                self.style.SUCCESS(
                    f'Ingested "{path}" as Document #{document.id} '
                    f'({document.chunks.count()} chunks).'
                )
            )
