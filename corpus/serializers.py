from rest_framework import serializers
from .models import Corpus, FilteredSubcorpus, UserSubcorpus, Text, TextMetadata, Style, Genre


class CorpusSerializer(serializers.ModelSerializer):
    """
    Serializer for creation and metadata updating of Corpus.
    """
    class Meta:
        model = Corpus
        fields = '__all__'
        read_only_fields = ('creator',)


class FilteredSubcorpusSerializer(serializers.ModelSerializer):
    """
    Serializer for creation new FilteredSubcorpus.
    """
    class Meta:
        model = FilteredSubcorpus
        fields = '__all__'
        read_only_fields = ('creator',)


class UserSubcorpusSerializer(serializers.ModelSerializer):
    """
    Serializer for creation new UserSubcorpus.
    """
    class Meta:
        model = UserSubcorpus
        fields = '__all__'
        read_only_fields = ('creator',)


class TextMetadataSerializer(serializers.ModelSerializer):
    """
    Serializer for reading and creation TextMetadata.
    """
    class Meta:
        model = TextMetadata
        fields = '__all__'
        read_only_fields = ('text',)


class TextSerializer(serializers.ModelSerializer):
    """
    Serializer for reading and creation Text with its related TextMetadata.
    """
    metadata = TextMetadataSerializer(required=True, allow_null=False)

    class Meta:
        model = Text
        fields = '__all__'
        read_only_fields = ('creator',)

    def create(self, validated_data):
        metadata_data = validated_data.pop('metadata', None)
        text = Text.objects.create(**validated_data)

        if metadata_data:
            genres_data = metadata_data.pop('genres', [])
            metadata = TextMetadata.objects.create(text=text, **metadata_data)
            if genres_data:
                metadata.genres.set(genres_data)

        return text

    def validate(self, attrs):
        """
        Prevents creation or update of Text with metadata that has genres not matching the specified style.
        """
        metadata_data = attrs.get('metadata')
        if not metadata_data:
            return attrs

        instance = getattr(self, 'instance', None)
        metadata_instance = getattr(instance, 'metadata', None) if instance else None
        final_style = metadata_data.get('style', getattr(metadata_instance, 'style', None))

        if 'genres' in metadata_data:
            final_genres = metadata_data['genres']
        else:
            final_genres = metadata_instance.genres.all() if metadata_instance else []

        if final_style and final_genres:
            invalid_genres = []
            for genre in final_genres:
                if genre.style_id != final_style.id:
                    invalid_genres.append(genre.name)

            if invalid_genres:
                raise serializers.ValidationError({
                    "metadata": f"Genres {invalid_genres} don't depend to style '{final_style.name}'"
                })

        return attrs

    def update(self, instance, validated_data):
        metadata_data = validated_data.pop('metadata', None)
        instance.name = validated_data.get('name', instance.name)
        instance.save()

        if metadata_data:
            metadata_instance = instance.metadata
            genres_data = metadata_data.pop('genres', None)

            for attr, value in metadata_data.items():
                setattr(metadata_instance, attr, value)
            metadata_instance.save()

            if genres_data is not None:
                metadata_instance.genres.set(genres_data)

        return instance


class GenreSerializer(serializers.ModelSerializer):
    """
    Serializer for Genre.
    """
    class Meta:
        model = Genre
        fields = ('id', 'name')


class StyleWithGenresSerializer(serializers.ModelSerializer):
    """
    Serializer for Style with its related Genres (read-only).
    """
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Style
        fields = '__all__'


class CorpusListSerializer(serializers.ModelSerializer):
    """
    Serializer for getting list of Corpora.
    Dynamically includes subcorpora and timestamps based on context.
    """
    subcorpora = serializers.SerializerMethodField()
    creator_id = serializers.IntegerField(source='creator.id', read_only=True)
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)

    class Meta:
        model = Corpus
        fields = ['id', 'name', 'subcorpora', 'creator_id', 'creator_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        include_subcorpora = self.context.get('include_subcorpora', False)
        include_timestamps = self.context.get('include_timestamps', False)

        if not include_subcorpora:
            self.fields.pop('subcorpora', None)

        if include_timestamps:
            self.fields['update_time'] = serializers.DateTimeField(read_only=True)

    def get_subcorpora(self, obj):
        """
        Returns a combined list of UserSubcorpus and FilteredSubcorpus for the given Corpus.
        """
        include_timestamps = self.context.get('include_timestamps', False)
        subcorpora_list = []

        for uc in obj.usersubcorpus_set.all():
            item = {
                "id": uc.id,
                "name": uc.name,
                "type": "user",
                "creator_id": uc.creator_id,
                "creator_name": getattr(uc.creator, 'full_name', None),
            }
            if include_timestamps:
                # UserSubcorpus has no timestamp field on the model yet.
                item["creation_time"] = None
            subcorpora_list.append(item)

        for fc in obj.filteredsubcorpus_set.all():
            item = {
                "id": fc.id,
                "name": fc.name,
                "type": "filtered",
                "creator_id": fc.creator_id,
                "creator_name": getattr(fc.creator, 'full_name', None),
                "filters": fc.filters,
            }
            if include_timestamps:
                item["creation_time"] = fc.creation_time
                item["update_time"] = fc.update_time
            subcorpora_list.append(item)

        return subcorpora_list


class TextListSerializer(serializers.ModelSerializer):
    """
    Serializer for getting list of Texts.
    """
    metadata = TextMetadataSerializer(read_only=True)

    class Meta:
        model = Text
        fields = ['id', 'name', 'metadata']