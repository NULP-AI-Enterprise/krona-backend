from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from corpus.models import Corpus, Subcorpus
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch

User = get_user_model()

class TestCorpusViews(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('test', 'pass')
        self.corpus = Corpus.objects.create(name='C1', creator=self.user)
        self.sub = Subcorpus.objects.create(name='S1', corpus=self.corpus)
        self.list_url = reverse('corpus_list')

    def test_list_view(self):
        """Checks status, template, and content inclusion for the corpus list page."""
        response = self.client.get(self.list_url) # use built in self.client
        # to imitate HTTP GET request

        self.assertEqual(response.status_code, 200)  # Check code
        self.assertTemplateUsed(response, 'corpus/corpus_list.html')  # Check template
        self.assertIn(self.corpus, response.context['corpora'])  # Check object presence

    def test_upload_fail(self):
        """Ensures that the view returns an error (200 OK) if no file is provided."""
        response = self.client.post(reverse('upload'), {'subcorpus': self.sub.id})
        # we take only id of corpus - {'subcorpus': self.sub.id}

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Будь ласка, оберіть файл")  # Check error message

    @patch('corpus.views.parse_uploaded_file')  # Mock for the parser function
    @patch('corpus.views.tp')  # Mock for the TextProcessor instance
    def test_upload_success(self, mock_parse, mock_tp):

        file = SimpleUploadedFile("test.txt", b"file_content", content_type="text/plain") # fake file
        mock_tp.return_value = ("dummy_path", {})

        # POST - response
        response = self.client.post(reverse('upload'), {
            'subcorpus': self.sub.id,
            'file': file
        })

        mock_tp.assert_called_once() # check that parse_uploaded_file was
        #executed only once

        self.assertRedirects(response, self.list_url) # Check the success redirect
