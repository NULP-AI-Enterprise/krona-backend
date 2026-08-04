import re
import math

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from elasticsearch_dsl import Search, Q, A
from elasticsearch_dsl.query import Match, Nested

from corpus.processors.text_processor import text_processor_instance as tp
from ..models import Text, FilteredSubcorpus, UserSubcorpus
from ..documents import SentenceDocument


class ConcordanceAPI(APIView):
    """
    API endpoint for concordance searching with server-side pagination
    """
    def post(self, request):
        # Data extraction
        collection_id = request.data.get('collection_id')
        collection_type = request.data.get('collection_type')

        query = request.data.get('query', '').strip()
        searching_type = request.data.get('searching_type', 'form_match')
        left_context_size = request.data.get('left_context_size', None)
        right_context_size = request.data.get('right_context_size', None)

        page = int(request.data.get('page', 1))
        page_size = int(request.data.get('page_size', 25))
        export_all = request.data.get('export', False)

        # Text ids retrieval
        try:
            if collection_type == "user_subcorpus":
                text_ids = list(Text.objects
                                .filter(user_subcorpus_id=collection_id)
                                .values_list("id", flat=True))

            elif collection_type == "filtered_subcorpus":
                filtered_subcorpus = get_object_or_404(FilteredSubcorpus, id=collection_id)
                text_ids = list(filtered_subcorpus.texts.values_list("id", flat=True))

            elif collection_type == "corpus":
                corpus_text_ids = list(Text.objects
                                       .filter(corpus_id=collection_id)
                                       .values_list("id", flat=True))
                subcorpus_ids = list(UserSubcorpus.objects
                                     .filter(corpus_id=collection_id)
                                     .values_list("id", flat=True))
                subcorpus_text_ids = list(Text.objects
                                          .filter(user_subcorpus_id__in=subcorpus_ids)
                                          .values_list("id", flat=True)) if subcorpus_ids else []
                text_ids = corpus_text_ids + subcorpus_text_ids
            else:
                return Response({"error": "Невідомий тип колекції"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error while texts extraction: {e}")
            return Response({"error": "Помилка при отриманні текстів"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not text_ids:
            return Response({'error': "У цій колекції немає текстів", 'results': []}, status=status.HTTP_404_NOT_FOUND)

        text_names_map = dict(Text.objects.filter(id__in=text_ids).values_list('id', 'name'))

        # Query processing
        clean_query = re.findall(r"(?u)[\w'ʼ‘’]+", query.lower())
        if not clean_query and searching_type != 'cql_match':
            return Response({'error': "Введіть коректний запит", 'results': []}, status=status.HTTP_400_BAD_REQUEST)

        elastic_query = SentenceDocument.search().filter("terms", text_id=text_ids)

        if searching_type == 'form_match':
            if len(clean_query) != 1:
                return Response({'error': "Введіть одне слово", 'results': []},
                                status=status.HTTP_400_BAD_REQUEST)

            elastic_query = elastic_query.query(
                'nested',
                path='tokens',
                query=Q('term', tokens__form=clean_query[0])
            )
            query_rules = [{'form': clean_query[0]}]

        elif searching_type == 'lemma_match':
            if len(clean_query) != 1:
                return Response({'error': "Введіть одне слово", 'results': []},
                                status=status.HTTP_400_BAD_REQUEST)

            elastic_query = elastic_query.query(
                'nested',
                path='tokens',
                query=Q('term', tokens__lemma=clean_query[0].lower())
            )
            query_rules = [{'lemma': clean_query[0].lower()}]

        elif searching_type == 'phrase_match':
            phrase_words = re.findall(r"(?u)[\w'ʼ‘’]+", query.lower())

            if not phrase_words:
                return Response({'error': "Введіть фразу"}, status=status.HTTP_400_BAD_REQUEST)

            query_rules = [{'form': word} for word in phrase_words]

            must_queries = []
            for word in phrase_words:
                must_queries.append(
                    Q("nested",
                      path="tokens",
                      query=Q("term", tokens__form=word))
                )

            elastic_query = elastic_query.query("bool", must=must_queries)

        elif searching_type == 'cql_match':
            query_rules = tp.parse_cql(query)
            if not query_rules:
                return Response({'error': "Некоректний CQL", 'results': []}, status=status.HTTP_400_BAD_REQUEST)

            must_queries = []
            for rule in query_rules:
                if 'distance' in rule:
                    continue
                token_clauses = []
                for k, v in rule.items():
                    field = f"tokens.{k}"
                    if isinstance(v, list):
                        token_clauses.append(Q("terms", **{field: v}))
                    else:
                        token_clauses.append(Q("term", **{field: v}))
                must_queries.append(Q("nested", path="tokens", query=Q("bool", must=token_clauses)))

            elastic_query = elastic_query.query("bool", must=must_queries)

        else:
            return Response({'error': "Невідомий тип пошуку", 'results': []}, status=status.HTTP_400_BAD_REQUEST)

        # Count total matching sentences in ES
        count_query = elastic_query.extra(size=0)
        try:
            total_hits = count_query.count()
        except Exception as e:
            print(f"Elasticsearch count error: {e}")
            total_hits = 0

        if export_all:
            export_limit = 10000
            elastic_query = elastic_query.extra(from_=0, size=min(total_hits, export_limit))
        else:
            es_from = (page - 1) * page_size
            es_size = page_size * 3
            elastic_query = elastic_query.extra(from_=es_from, size=es_size)

        try:
            response = elastic_query.execute()
        except Exception as e:
            print(f"Elasticsearch error: {e}")
            return Response({"error": "Помилка Elasticsearch"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        results = []

        for hit in response:
            try:
                kwic_list = tp.build_kwic(
                    original_sentence_text=str(hit.original_sentence_text),
                    left_context_size=left_context_size,
                    right_context_size=right_context_size,
                    query_rules=query_rules,
                    es_tokens=hit.tokens
                )
            except Exception as e:
                print(f"Error while building KWIC: {e}")
                return Response({"error": "Помилка при побудові KWIC"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            text_name = text_names_map.get(hit.text_id, "Невідомий текст")

            for variant in kwic_list:
                results.append({
                    'left_context': variant['left_context'],
                    'searched_sentence': variant['searched_sentence'],
                    'right_context': variant['right_context'],
                    'document_name': text_name
                })

        total_items = total_hits

        if export_all:
            return Response({
                'results': results,
                'total_items': total_items
            }, status=status.HTTP_200_OK)

        paginated_results = results[:page_size]

        # Statistics calculation
        total_tokens_in_scope = 0

        try:
            count_search = SentenceDocument.search().filter("terms", text_id=text_ids)
            count_search.aggs.bucket('all_tokens', 'nested', path='tokens')
            count_search = count_search.extra(size=0)
            count_res = count_search.execute()
            total_tokens_in_scope = count_res.aggregations.all_tokens.doc_count
        except Exception as e:
            print(f"Error while statistics calculation: {e}")

        if total_tokens_in_scope > 0:
            relative_freq = (total_items / total_tokens_in_scope) * 1_000_000
            percent_val = (total_items / total_tokens_in_scope) * 100
            percent_str = f"{percent_val:.4f}%"
        else:
            relative_freq = 0
            percent_str = "0%"

        # Response formation
        type_labels = {
            'form_match': 'Словоформа',
            'lemma_match': 'Лема',
            'phrase_match': 'Словосполучення',
            'cql_match': 'CQL'
        }

        search_type = type_labels.get(searching_type, searching_type)
        return Response({
            'results': paginated_results,
            'error': None if paginated_results else "Нічого не знайдено",
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_items': total_items,
                'total_pages': math.ceil(total_items / page_size) if total_items > 0 else 1
            },
            'stats': {
                'query': query,
                'search_type': search_type,
                'absolute_count': total_items,
                'total_tokens': total_tokens_in_scope,
                'relative_freq': round(relative_freq),
                'percent_str': percent_str
            }
        }, status=status.HTTP_200_OK)


class WordListAPI(APIView):
    """
    API endpoint for generating word frequency lists
    """
    def post(self, request):
        collection_id = request.data.get('collection_id')
        collection_type = request.data.get('collection_type')

        if not collection_id or not collection_type:
            return Response(
                {"error": "Оберіть колекцію для аналізу"},
                status=status.HTTP_400_BAD_REQUEST
            )

        field_to_count = request.data.get('field_to_count', 'tokens.form')
        pos_filter = request.data.get('pos')
        pattern_text = request.data.get('pattern_text')
        pattern_mode = request.data.get('pattern_mode')

        try:
            if collection_type == "user_subcorpus":
                text_ids = list(Text.objects
                                .filter(user_subcorpus_id=collection_id)
                                .values_list("id", flat=True))

            elif collection_type == "filtered_subcorpus":
                filtered_subcorpus = get_object_or_404(FilteredSubcorpus, id=collection_id)
                text_ids = list(filtered_subcorpus.texts.values_list("id", flat=True))

            elif collection_type == "corpus":
                corpus_text_ids = list(Text.objects
                                       .filter(corpus_id=collection_id)
                                       .values_list("id", flat=True))
                subcorpus_ids = list(UserSubcorpus.objects
                                     .filter(corpus_id=collection_id)
                                     .values_list("id", flat=True))
                subcorpus_text_ids = list(Text.objects
                                          .filter(user_subcorpus_id__in=subcorpus_ids)
                                          .values_list("id", flat=True)) if subcorpus_ids else []
                text_ids = corpus_text_ids + subcorpus_text_ids
            else:
                return Response({"error": "Невідомий тип колекції"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error while texts extraction: {e}")
            return Response({"error": "Помилка при отриманні текстів"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not text_ids:
            return Response({"error": "У цій колекції немає текстів"}, status=status.HTTP_404_NOT_FOUND)

        s = SentenceDocument.search().filter('terms', text_id=text_ids)
        token_filters = []

        if pos_filter and pos_filter != 'all':
            internal_pos = tp.pos_mapping.get(pos_filter.lower(), pos_filter)
            token_filters.append(Q('term', **{'tokens.pos': internal_pos}))

        if pattern_text:
            search_val = pattern_text.strip().lower()
            query = f"{search_val}*" if pattern_mode == 'starts_with' else (
                f"*{search_val}" if pattern_mode == 'ends_with' else f"*{search_val}*")
            token_filters.append(Q('wildcard', **{field_to_count: query}))

        nested_agg = A('nested', path='tokens')
        terms_agg = A('terms', field=field_to_count, size=100000, order={'_count': 'desc'})

        if token_filters:
            filter_agg = A('filter', filter=Q('bool', filter=token_filters))
            filter_agg.bucket('top_words', terms_agg)
            nested_agg.bucket('filtered_pos', filter_agg)
        else:
            nested_agg.bucket('top_words', terms_agg)

        s.aggs.bucket('tokens_nested', nested_agg)
        s = s.extra(size=0)

        try:
            response = s.execute()
        except Exception as e:
            print(f"Elasticsearch error: {e}")
            return Response({"error": "Помилка Elasticsearch"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        results = []

        try:
            agg_result = response.aggregations.tokens_nested

            if hasattr(agg_result, 'filtered_pos'):
                buckets = agg_result.filtered_pos.top_words.buckets
            else:
                buckets = agg_result.top_words.buckets

            total_tokens_in_scope = agg_result.doc_count

            if total_tokens_in_scope == 0:
                return Response([], status=status.HTTP_200_OK)

            for bucket in buckets:
                absolute_count = bucket.doc_count
                relative_freq = (absolute_count / total_tokens_in_scope) * 1_000_000
                percent_val = (absolute_count / total_tokens_in_scope) * 100
                percent_str = f"{percent_val:.4f}%"

                results.append({
                    'word': bucket.key,
                    'absolute_count': absolute_count,
                    'relative_freq': round(relative_freq),
                    'percent_val': round(percent_val, 4),
                    'percent_str': percent_str
                })

        except Exception as e:
            print(f"Error while results formatting: {e}")
            return Response({"error": "Помилка при формуванні результатів"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(results, status=status.HTTP_200_OK)
