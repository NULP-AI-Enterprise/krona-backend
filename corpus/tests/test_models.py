from django.test import TestCase, Client
from corpus.models import Corpus, Subcorpus, Text, TextMetadata
from django.contrib.auth import get_user_model

User = get_user_model()

class BaseTestModel(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')

        self.corpus = Corpus.objects.create(
            name='Test Corpus',
            creator=self.user,
            description='Base description'
        )

        self.subcorpus = Subcorpus.objects.create(
            name='Test Subcorpus',
            corpus=self.corpus,
            filter_criteria={"year": 2023}
        )

        self.text = Text.objects.create(
            name='Test Text',
            subcorpus=self.subcorpus,
            text_id_user="unique_id_001"
        )

class TestCorpusModel(BaseTestModel):

    def test_corpus_str(self):
        self.assertEqual(str(self.corpus), 'Test Corpus')

    def test_creator_set_null_when_delete(self):
        """Checks if the creator set to null when deleting"""
        self.user.delete()
        self.corpus.refresh_from_db()
        self.assertIsNone(self.corpus.creator)


class TestSubcorpusModel(BaseTestModel):

    def test_subcorpus_str(self):
        expected_str = "Test Corpus - Test Subcorpus"
        self.assertEqual(str(self.subcorpus), expected_str)

    def test_cascade_delete_corpus(self):
        """Checks if the subcorpus deletion on cascade works correctly"""
        self.corpus.delete()
        self.assertEqual(Subcorpus.objects.count(), 0)


class TestTextModel(BaseTestModel):

    def test_text_str(self):
        self.assertEqual(str(self.text), 'Test Text')

    def test_cascade_delete_subcorpus(self):
        self.subcorpus.delete()
        self.assertEqual(Text.objects.count(), 0)

class TestTextMetadata(BaseTestModel):

   # if you want to change smth exactly in this test class:
   def setUp(self):
       super().setUp()

       # Integration OneToOne takes some data from DB
       self.text_metadata = TextMetadata.objects.create(
           text=self.text,
       )

    # Checks __str__ - Unit test
   def test_text_metadata_str(self):
       expected_str = "Metadata for Test Text"
       self.assertEqual(str(self.text_metadata), expected_str)
