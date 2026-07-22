import os
import json
import tempfile

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.db import transaction

from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import connections

from corpus.processors.file_processor import parse_uploaded_file
from corpus.processors.linguistic_processor import lingustic_processor_instance as lp
from ..documents import SentenceDocument
from ..models import Corpus, Text, Style, Genre, TextMetadata, FilteredSubcorpus, UserSubcorpus
from ..serializers import (CorpusSerializer, CorpusListSerializer, TextSerializer, TextListSerializer,
                           FilteredSubcorpusSerializer, UserSubcorpusSerializer, StyleWithGenresSerializer)




class CorpusMetadataOptionsAPI(APIView):
    # Returns all available options for corpus metadata fields.
    def get(self, request):
        # 1. All corpus types (static)
        corpus_type = [
            {"value": key, "label": label} for key, label in Corpus.CorpusType.choices
        ]

        # 2. All text origins (static)
        corpus_language = [
            {"value": key, "label": label} for key, label in Corpus.CorpusLanguage.choices
        ]

        return Response({
            "corpus_type": corpus_type,
            "corpus_language": corpus_language
        })


class CreateCorpusAPI(APIView):
    permission_classes = [IsAuthenticated]

    # Creates a new corpus with metadata
    def post(self, request):
        serializer = CorpusSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CorpusAPI(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    # Returns corpus metadata
    def get(self, request, pk):
        corpus = get_object_or_404(Corpus, pk=pk)
        serializer = CorpusSerializer(corpus)

        return Response(serializer.data)

    # Updates corpus metadata
    def patch(self, request, pk):
        corpus = get_object_or_404(Corpus, pk=pk)
        if corpus.creator != request.user:
            return Response({"error": "You can only edit your own corpus"}, status=status.HTTP_403_FORBIDDEN)
        serializer = CorpusSerializer(corpus, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Deletes corpus and all subcorpora/texts in it
    def delete(self, request, pk):
        corpus = get_object_or_404(Corpus, pk=pk)
        if corpus.creator != request.user:
            return Response({"error": "You can only delete your own corpus"}, status=status.HTTP_403_FORBIDDEN)
        corpus.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CorpusListAPI(APIView):
    # Returns list of corpora
    def get(self, request):
        include_subcorpora = request.query_params.get('include_subcorpora', '').lower() == 'true'
        include_timestamps = request.query_params.get('include_timestamps', '').lower() == 'true'

        corpora = Corpus.objects.all().order_by('id')

        if include_subcorpora:
            # Uploads only user's subcorpora
            if request.user.is_authenticated:
                user_sub_prefetch = Prefetch(
                    'usersubcorpus_set', 
                    queryset=UserSubcorpus.objects.filter(creator=request.user)
                )
                filtered_sub_prefetch = Prefetch(
                    'filteredsubcorpus_set', 
                    queryset=FilteredSubcorpus.objects.filter(creator=request.user)
                )
                corpora = corpora.prefetch_related(user_sub_prefetch, filtered_sub_prefetch)
            else:
                user_sub_prefetch = Prefetch('usersubcorpus_set', queryset=UserSubcorpus.objects.none())
                filtered_sub_prefetch = Prefetch('filteredsubcorpus_set', queryset=FilteredSubcorpus.objects.none())
                corpora = corpora.prefetch_related(user_sub_prefetch, filtered_sub_prefetch)

        serializer = CorpusListSerializer(
            corpora,
            many=True,
            context={
                'request': request,
                'include_subcorpora': include_subcorpora,
                'include_timestamps': include_timestamps
            }
        )

        return Response(serializer.data)


class TextMetadataOptionsAPI(APIView):
    # Returns all available options for text metadata fields.
    def get(self, request):
        # 1. All corpora (dynamic)
        corpuses = Corpus.objects.values('id', 'name') # Make it for concrete user

        # 2. All styles with their genres (static)
        styles = Style.objects.prefetch_related('genres').all()
        styles_data = StyleWithGenresSerializer(styles, many=True).data

        # 3. All author genders (static)
        genders_data = [
            {"value": key, "label": label} for key, label in TextMetadata.Gender.choices
        ]

        # 4. All text origins (static)
        origins_data = [
            {"value": key, "label": label} for key, label in TextMetadata.TextOrigin.choices
        ]

        return Response({
            "corpuses": corpuses,
            "styles_with_genres": styles_data,
            "authors_genders": genders_data,
            "text_origins": origins_data
        })


class CreateTextAPI(APIView):
    permission_classes = [IsAuthenticated]

    # Creates a new text, saves metadata, parses file, and indexes into Elasticsearch.
    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "File not provided"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.dict()

        metadata_str = data.get('metadata')
        if metadata_str:
            try:
                data['metadata'] = json.loads(metadata_str)
            except json.JSONDecodeError:
                return Response({"error": "Incorrect JSON format in metadata field"},
                                status=status.HTTP_400_BAD_REQUEST)

        serializer = TextSerializer(data=data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    text_instance = serializer.save(creator=request.user)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                        for chunk in uploaded_file.chunks():
                            tmp_file.write(chunk)

                        tmp_file_path = tmp_file.name

                    try:
                        content, parsed_meta = parse_uploaded_file(tmp_file_path, uploaded_file.name)

                    finally:
                        if os.path.exists(tmp_file_path):
                            os.remove(tmp_file_path)

                    processed_docs = lp.process_input_content(content)

                    es = connections.get_connection()
                    batch_size = 500
                    total_indexed = 0

                    for i in range(0, len(processed_docs), batch_size):
                        actions = []
                        for doc in processed_docs[i:i + batch_size]:
                            es_doc = SentenceDocument(
                                text_id=text_instance.id,
                                original_sentence_text=doc['original_sentence_text'],
                                tokens=doc['tokens']
                            )
                            actions.append(es_doc.to_dict(include_meta=True))

                        if actions:
                            success, _ = bulk(es, actions, stats_only=True)
                            total_indexed += success

                    print(f"Successfully indexed {total_indexed} sentences")



                    return Response(serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                print(f"Error while processing text: {e}")
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TextAPI(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Returns text metadata
    def get(self, request, pk):
        text = get_object_or_404(Text.objects.select_related('metadata'), id=pk)
        serializer = TextSerializer(text)

        return Response(serializer.data)

    # Updates text metadata
    def patch(self, request, pk):
        text = get_object_or_404(Text.objects.select_related('metadata', 'corpus'), id=pk)
        if text.creator != request.user:
            return Response({"error": "You can only edit metadata of texts you uploaded"}, status=status.HTTP_403_FORBIDDEN)
        serializer = TextSerializer(text, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Deletes text and its metadata
    def delete(self, request, pk):
        text = get_object_or_404(Text, id=pk)
        if text.creator != request.user:
            return Response({"error": "You can only delete texts you uploaded"}, status=status.HTTP_403_FORBIDDEN)
        text.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TextListAPI(APIView):
    # Returns list of texts
    def get(self, request):
        corpus_id = request.query_params.get('corpus_id')
        user_subcorpus_id = request.query_params.get('user_subcorpus_id')
        filtered_subcorpus_id = request.query_params.get('filtered_subcorpus_id')

        # 1. Corpus
        if corpus_id:
            corpus = get_object_or_404(Corpus, id=corpus_id)
            texts = Text.objects.select_related('metadata').filter(corpus=corpus)
            collection_name = corpus.name
            collection_type = "corpus"

        # 2. User Subcorpus
        elif user_subcorpus_id:
            if not request.user.is_authenticated:
                return Response({"error": "Need Authorization"}, status=status.HTTP_401_UNAUTHORIZED)
            subcorpus = get_object_or_404(UserSubcorpus, id=user_subcorpus_id)
            if getattr(subcorpus, 'creator', getattr(subcorpus, 'user', None)) != request.user:
                return Response({"error": "You do not have a permission"}, status=status.HTTP_403_FORBIDDEN)
            texts = Text.objects.select_related('metadata').filter(user_subcorpus=subcorpus)
            collection_name = subcorpus.name
            collection_type = "user_subcorpus"

        # 3. Filtered Subcorpus
        elif filtered_subcorpus_id:
            if not request.user.is_authenticated:
                return Response({"error": "Need Authorization"}, status=status.HTTP_401_UNAUTHORIZED)
            subcorpus = get_object_or_404(FilteredSubcorpus, id=filtered_subcorpus_id)
            if subcorpus.creator != request.user:
                return Response({"error": "You do not have a permission"}, status=status.HTTP_403_FORBIDDEN)
            texts = subcorpus.texts.select_related('metadata').all()
            collection_name = subcorpus.name
            collection_type = "filtered_subcorpus"

        else:
            return Response(
                {"error": "Please provide corpus_id, user_subcorpus_id, or filtered_subcorpus_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = TextListSerializer(texts, many=True)

        return Response({
            "collection_info": {
                "type": collection_type,
                "name": collection_name,
                "total_texts": texts.count()
            },
            "texts": serializer.data
        })


class FilteredSubcorpusMetadataOptionsAPI(APIView):
    # Returns all available options for filtered subcorpus metadata fields.
    # Strictly limited to the values actually present in the given corpus.
    def get(self, request, corpus_id):
        corpus = get_object_or_404(Corpus, id=corpus_id)

        # 1. Styles and genres (dynamic)
        existing_genres = Genre.objects.filter(
            textmetadata__text__corpus=corpus
        ).distinct()

        styles = Style.objects.filter(
            textmetadata__text__corpus=corpus
        ).prefetch_related(
            Prefetch('genres', queryset=existing_genres)
        ).distinct()

        styles_data = StyleWithGenresSerializer(styles, many=True).data

        # 2. Authors (dynamic)
        authors = TextMetadata.objects.filter(
            text__corpus=corpus
        ).exclude(
            author__isnull=True
        ).exclude(
            author__exact=''
        ).values_list('author', flat=True).distinct()

        # 3. Author genders (dynamic)
        existing_genders = TextMetadata.objects.filter(
            text__corpus=corpus
        ).exclude(
            authors_gender__isnull=True
        ).exclude(
            authors_gender__exact=''
        ).values_list('authors_gender', flat=True).distinct()

        gender_dict = dict(TextMetadata.Gender.choices)
        genders_data = [
            {"value": val, "label": gender_dict[val]}
            for val in existing_genders if val in gender_dict
        ]

        # 4. Sources (dynamic)
        sources = TextMetadata.objects.filter(
            text__corpus=corpus
        ).exclude(
            source__isnull=True
        ).exclude(
            source__exact=''
        ).values_list('source', flat=True).distinct()

        # 5. Text origins (dynamic)
        existing_origins = TextMetadata.objects.filter(
            text__corpus=corpus
        ).exclude(
            text_origin__isnull=True
        ).exclude(
            text_origin__exact=''
        ).values_list('text_origin', flat=True).distinct()

        origin_dict = dict(TextMetadata.TextOrigin.choices)
        origins_data = [
            {"value": val, "label": origin_dict[val]}
            for val in existing_origins if val in origin_dict
        ]

        return Response({
            "styles_with_genres": styles_data,
            "authors": list(authors),
            "authors_genders": genders_data,
            "sources": list(sources),
            "text_origins": origins_data
        })


class CreateFilteredSubcorpusAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    # Creates a new filtered subcorpus based on provided filters.
    def post(self, request):
        data = request.data

        corpus_id = data.get('corpus_id')
        name = data.get('name')
        filters = data.get('filters', {})

        corpus = get_object_or_404(Corpus, id=corpus_id)
        texts = Text.objects.filter(corpus=corpus)

        styles = filters.get('styles')
        if styles:
            texts = texts.filter(metadata__style__in=styles)

        genres = filters.get('genres')
        if genres:
            texts = texts.filter(metadata__genres__in=genres)

        authors = filters.get('authors')
        if authors:
            texts = texts.filter(metadata__author__in=authors)

        sources = filters.get('sources')
        if sources:
            texts = texts.filter(metadata__source__in=sources)

        authors_gender = filters.get('authors_genders')
        if authors_gender:
            texts = texts.filter(metadata__authors_gender__in=authors_gender)

        text_origin = filters.get('text_origins')
        if text_origin:
            texts = texts.filter(metadata__text_origin__in=text_origin)

        year_of_creation = filters.get('years_of_creation')
        if year_of_creation and isinstance(year_of_creation, list):
            if len(year_of_creation) == 1:
                texts = texts.filter(metadata__year_of_creation=year_of_creation[0])
            elif len(year_of_creation) == 2:
                start_year, end_year = sorted(year_of_creation)
                texts = texts.filter(metadata__year_of_creation__range=(start_year, end_year))

        years_of_publication = filters.get('years_of_publication')
        if years_of_publication and isinstance(years_of_publication, list):
            if len(years_of_publication) == 1:
                texts = texts.filter(metadata__years_of_publication__contains=[years_of_publication[0]])
            elif len(years_of_publication) == 2:
                start_year, end_year = sorted(years_of_publication)
                years_range = list(range(start_year, end_year + 1))
                texts = texts.filter(metadata__years_of_publication__overlap=years_range)

        texts = texts.distinct()
        matched_count = texts.count()

        if matched_count == 0:
            return Response(
                {
                    "created": False,
                    "matched_texts_count": 0,
                    "error": "No texts found matching the provided filters"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            subcorpus = FilteredSubcorpus.objects.create(
                name=name,
                corpus=corpus,
                creator=request.user
            )

            subcorpus.texts.set(texts)

        except Exception as e:
            return Response(
                {
                    "created": False,
                    "matched_texts_count": matched_count,
                    "error": f"Error while subcorpus creation: {str(e)}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = FilteredSubcorpusSerializer(subcorpus)

        return Response(
            {
                "created": True,
                "matched_texts_count": matched_count,
                "subcorpus": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


class FilteredSubcorpusAPI(APIView):
    permission_classes = [IsAuthenticated]

    # Deletes a filtered subcorpus.
    def delete(self, request, pk):
        subcorpus = get_object_or_404(FilteredSubcorpus, id=pk)
        if subcorpus.creator != request.user:
            return Response({"error": "You cannot delete this subcorpus"}, status=status.HTTP_403_FORBIDDEN)
        subcorpus.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateUserSubcorpusAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    # Creates a new user subcorpus.
    def post(self, request):
        serializer = UserSubcorpusSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(creator=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserSubcorpusAPI(APIView):
    permission_classes = [IsAuthenticated]

    # Deletes a user subcorpus.
    def delete(self, request, pk):
        subcorpus = get_object_or_404(UserSubcorpus, id=pk)
        if subcorpus.creator != request.user:
            return Response({"error": "You cannot delete this subcorpus"}, status=status.HTTP_403_FORBIDDEN)
        subcorpus.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
