from django_elasticsearch_dsl import Document, fields
from .models import Text
from django_elasticsearch_dsl.registries import registry

@registry.register_document
class SentenceDocument(Document):
    """
    Class that describes how Django model will be indexed in ES
    """

    text_id = fields.IntegerField()
    original_sentence_text = fields.TextField()

    tokens = fields.NestedField(properties={
        'form': fields.KeywordField(),
        'lemma': fields.KeywordField(),
        'pos': fields.KeywordField(),
        'morph': fields.ObjectField(properties={
            # Nominal features
            'case': fields.KeywordField(),
            'gender': fields.KeywordField(),
            'number': fields.KeywordField(),
            'animacy': fields.KeywordField(),

            # Verbal features
            'verbform': fields.KeywordField(),
            'mood': fields.KeywordField(),
            'tense': fields.KeywordField(),
            'aspect': fields.KeywordField(),
            'person': fields.KeywordField(),
            'voice': fields.KeywordField(),

            # Modifiers & pronouns
            'degree': fields.KeywordField(),
            'prontype': fields.KeywordField(),
            'numtype': fields.KeywordField(),
            'poss': fields.KeywordField(),
            'reflex': fields.KeywordField(),
            'polarity': fields.KeywordField(),
        })
    })

    class Index:
        name = 'sentence_index'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Text
