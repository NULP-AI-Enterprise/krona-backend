"""Install the sentence mapping before uploads; explicitly repair legacy indexes."""
from datetime import datetime, timezone
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from elasticsearch_dsl import connections

from corpus.documents import SentenceDocument


def mapping_matches(actual, expected):
    """Allow additional fields, but require the declared types recursively."""
    if expected.get('type') and actual.get('type', 'object') != expected['type']:
        return False
    return all(
        name in actual.get('properties', {})
        and mapping_matches(actual['properties'][name], definition)
        for name, definition in expected.get('properties', {}).items()
    )


class Command(BaseCommand):
    help = 'Create/validate the sentence index. --repair preserves legacy documents.'

    def add_arguments(self, parser):
        parser.add_argument('--repair', action='store_true')

    def handle(self, *args, **options):
        es = connections.get_connection().options(request_timeout=120)
        name = SentenceDocument._index._name
        definition = SentenceDocument._index.to_dict()
        # Also protect automatic creation if the index is ever missing.
        es.indices.put_index_template(
            name=f'{name}_schema', index_patterns=[name, f'{name}_v*'],
            priority=100, template=definition,
        )
        if not es.indices.exists(index=name):
            es.indices.create(index=name, **definition)
            self.stdout.write(self.style.SUCCESS(f'Created {name}'))
            return

        mappings = es.indices.get_mapping(index=name)
        if all(mapping_matches(value['mappings'], definition['mappings'])
               for value in mappings.values()):
            self.stdout.write(self.style.SUCCESS(f'{name}: mapping is valid'))
            return
        if not options['repair']:
            raise CommandError(
                f'{name} has incompatible mappings. Back up Elasticsearch, then '
                'run ensure_search_index --repair. Do not use search_index --rebuild: '
                'Postgres does not store sentence content.'
            )
        if len(mappings) != 1:
            raise CommandError('Repair requires exactly one source index')

        source = next(iter(mappings))
        suffix = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') + '_' + uuid4().hex[:8]
        backup = f'{name}_backup_{suffix}'
        target = f'{name}_v{suffix}'
        # Block writes while copying so uploads cannot be silently lost at cutover.
        # The block API waits for in-flight writes to finish.
        old_settings = es.indices.get_settings(index=source)
        was_blocked = old_settings[source]['settings']['index'].get('blocks', {}).get('write') == 'true'
        es.indices.add_block(index=source, block='write')
        try:
            es.indices.refresh(index=source)
            count = es.count(index=source)['count']
            es.indices.create(index=backup, mappings=mappings[source]['mappings'],
                              settings={'number_of_shards': 1, 'number_of_replicas': 0})
            self.copy(es, source, backup, count)
            self.stdout.write(f'Backup: {backup} ({count} documents)')
            es.indices.create(index=target, **definition)
            self.copy(es, source, target, count)
            # Exercise both nested lookup and keyword aggregation before cutover.
            es.search(index=target, size=0, aggs={
                'tokens': {'nested': {'path': 'tokens'}, 'aggs': {
                    'forms': {'terms': {'field': 'tokens.form', 'size': 1}}
                }}
            })
            if source == name:
                actions = [{'remove_index': {'index': source}}]
            else:
                actions = [{'remove': {'index': source, 'alias': name}}]
            actions.append({'add': {'index': target, 'alias': name, 'is_write_index': True}})
            es.indices.update_aliases(actions=actions)
            self.stdout.write(self.style.SUCCESS(
                f'{name} now points to {target}; all {count} documents preserved. '
                f'Backup retained: {backup}'
            ))
        finally:
            if not was_blocked and es.indices.exists(index=source):
                # After replacing a concrete index, its name is now an alias;
                # clearing the block is harmless for that new target too.
                es.indices.put_settings(index=source, settings={'index.blocks.write': False})

    @staticmethod
    def copy(es, source, target, expected_count):
        result = es.reindex(source={'index': source}, dest={'index': target, 'op_type': 'create'},
                            refresh=True, wait_for_completion=True)
        if (result.get('failures') or result.get('timed_out')
                or result.get('created') != expected_count
                or es.count(index=target)['count'] != expected_count):
            raise CommandError(f'Copy to {target} failed validation; source retained')
