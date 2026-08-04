from rest_framework import serializers
from django.utils import timezone

from .models import SubcorpusShare, SubcorpusAccessGrant, CorpusShare, CorpusUserAccess


class SubcorpusShareCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubcorpusShare
        fields = ['permission_level', 'expires_at', 'max_uses']

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Термін дії має бути в майбутньому.")
        return value

    def validate_max_uses(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Кількість використань має бути більше 0.")
        return value


class SubcorpusShareReadSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = SubcorpusShare
        fields = [
            'id', 'access_code', 'link_token', 'permission_level',
            'is_active', 'expires_at', 'max_uses', 'use_count',
            'created_at', 'is_valid',
        ]


class ShareRedeemSerializer(serializers.Serializer):
    access_code = serializers.CharField(max_length=8, required=False, allow_blank=True)
    link_token = serializers.UUIDField(required=False)

    def validate(self, attrs):
        code = attrs.get('access_code', '').strip()
        token = attrs.get('link_token')
        if not code and not token:
            raise serializers.ValidationError(
                "Надайте access_code або link_token."
            )
        if code:
            attrs['access_code'] = code
        return attrs


class SubcorpusAccessGrantSerializer(serializers.ModelSerializer):
    subcorpus_name = serializers.CharField(source='subcorpus.name', read_only=True)
    subcorpus_id = serializers.IntegerField(source='subcorpus.id', read_only=True)
    corpus_name = serializers.CharField(source='subcorpus.corpus.name', read_only=True)
    corpus_id = serializers.IntegerField(source='subcorpus.corpus.id', read_only=True)
    owner_name = serializers.CharField(source='subcorpus.creator.full_name', read_only=True)

    class Meta:
        model = SubcorpusAccessGrant
        fields = [
            'id', 'subcorpus_id', 'subcorpus_name', 'corpus_name',
            'corpus_id', 'permission_level', 'granted_at', 'owner_name',
        ]


class DeriveSubcorpusSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)


class CorpusShareCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorpusShare
        fields = ['permission_level', 'expires_at', 'max_uses']

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Термін дії має бути в майбутньому.")
        return value

    def validate_max_uses(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Кількість використань має бути більше 0.")
        return value


class CorpusShareReadSerializer(serializers.ModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = CorpusShare
        fields = [
            'id', 'access_code', 'link_token', 'permission_level',
            'is_active', 'expires_at', 'max_uses', 'use_count',
            'created_at', 'is_valid',
        ]


class CorpusAccessGrantSerializer(serializers.ModelSerializer):
    corpus_name = serializers.CharField(source='corpus.name', read_only=True)
    corpus_id = serializers.IntegerField(source='corpus.id', read_only=True)
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = CorpusUserAccess
        fields = ['id', 'corpus_id', 'corpus_name', 'access_level', 'owner_name']

    def get_owner_name(self, obj):
        return obj.corpus.creator.full_name if hasattr(obj.corpus.creator, 'full_name') else str(obj.corpus.creator)
