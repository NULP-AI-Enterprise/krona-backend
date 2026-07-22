from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Text, Corpus
from .documents import SentenceDocument


@receiver(post_save, sender=Text)
def handle_text_creation(sender, instance, created, **kwargs):
    """
    Update the 'update_time' field of Corpus when a new Text is added to it.
    """
    if created and getattr(instance, 'corpus', None):
        try:
            corpus = instance.corpus
            corpus.update_time = timezone.now()
            corpus.save(update_fields=['update_time'])
        except Exception as e:
            print(f"Error updating corpus time on text creation: {e}")


@receiver(post_delete, sender=Text)
def handle_text_deletion(sender, instance, **kwargs):
    """
    Update the 'update_time' field of Corpus when a Text is deleted safely.
    Remove related sentences from Elasticsearch when a Text is deleted.
    """
    if instance.corpus_id:
        try:
            Corpus.objects.filter(id=instance.corpus_id).update(update_time=timezone.now())
        except Exception as e:
            print(f"Error updating corpus time on text deletion: {e}")

    try:
        s = SentenceDocument.search().query("match", text_id=instance.id)
        s.delete()
    except Exception as e:
        print(f"Error deleting sentences from Elasticsearch: {e}")
