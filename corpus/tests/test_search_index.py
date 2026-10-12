from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError

from corpus.documents import SentenceDocument
from corpus.management.commands.ensure_search_index import Command, mapping_matches


class SearchIndexTests(TestCase):
    def test_dynamic_object_mapping_is_rejected(self):
        expected = SentenceDocument._index.to_dict()['mappings']
        self.assertFalse(mapping_matches({'properties': {
            'tokens': {'properties': {'form': {'type': 'text'}}}
        }}, expected))

    def test_keyword_types_are_required_inside_nested_tokens(self):
        expected = {'properties': {'tokens': {'type': 'nested', 'properties': {
            'form': {'type': 'keyword'}
        }}}}
        actual = {'properties': {'tokens': {'type': 'nested', 'properties': {
            'form': {'type': 'text'}
        }}}}
        self.assertFalse(mapping_matches(actual, expected))
        self.assertTrue(mapping_matches(expected, expected))

    @patch('corpus.management.commands.ensure_search_index.connections.get_connection')
    def test_bootstrap_creates_explicit_mapping(self, connection):
        es = connection.return_value.options.return_value
        es.indices.exists.return_value = False
        Command(stdout=StringIO()).handle(repair=False)
        es.indices.put_index_template.assert_called_once()
        definition = es.indices.create.call_args.kwargs
        self.assertEqual(definition['mappings']['properties']['tokens']['type'], 'nested')
        self.assertEqual(definition['mappings']['properties']['tokens']['properties']['form']['type'], 'keyword')

    @patch('corpus.management.commands.ensure_search_index.connections.get_connection')
    def test_bootstrap_refuses_destructive_rebuild(self, connection):
        es = connection.return_value.options.return_value
        es.indices.get_mapping.return_value = {'sentence_index': {'mappings': {}}}
        with self.assertRaises(CommandError):
            Command(stdout=StringIO()).handle(repair=False)
        es.indices.add_block.assert_not_called()
        es.indices.update_aliases.assert_not_called()

    def test_incomplete_copy_is_rejected(self):
        es = MagicMock()
        es.reindex.return_value = {'created': 1, 'failures': []}
        es.count.return_value = {'count': 1}
        with self.assertRaises(CommandError):
            Command.copy(es, 'source', 'target', 2)

    @patch('corpus.management.commands.ensure_search_index.connections.get_connection')
    def test_failed_repair_unblocks_source_without_cutover(self, connection):
        es = connection.return_value.options.return_value
        es.indices.get_mapping.return_value = {'sentence_index': {'mappings': {}}}
        es.indices.get_settings.return_value = {'sentence_index': {'settings': {'index': {}}}}
        es.count.return_value = {'count': 2}
        es.reindex.return_value = {'created': 1, 'failures': []}
        with self.assertRaises(CommandError):
            Command(stdout=StringIO()).handle(repair=True)
        es.indices.update_aliases.assert_not_called()
        es.indices.put_settings.assert_called_once_with(
            index='sentence_index', settings={'index.blocks.write': False})
