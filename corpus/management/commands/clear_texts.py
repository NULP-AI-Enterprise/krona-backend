from django.core.management.base import BaseCommand
from corpus.models import Text

# docker compose exec backend python manage.py clear_texts

class Command(BaseCommand):
    help = 'Completely deletes all texts from the database. Thanks to signals, this will automatically clean Elasticsearch as well'

    def handle(self, *args, **kwargs):
        texts = Text.objects.all()
        count = texts.count()

        if count == 0:
            self.stdout.write(self.style.WARNING('The database is already empty, there is nothing to delete'))
            return

        self.stdout.write(f"Starting deletion...")

        texts.delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} texts from the database and their sentences from Elasticsearch!'))
