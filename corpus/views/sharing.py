from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from users.permissions import IsRegisteredUser
from ..models import (UserSubcorpus, SubcorpusShare, SubcorpusAccessGrant, Text,
                      Corpus, CorpusShare, CorpusUserAccess)
from ..serializers_sharing import (
    SubcorpusShareCreateSerializer,
    SubcorpusShareReadSerializer,
    ShareRedeemSerializer,
    SubcorpusAccessGrantSerializer,
    DeriveSubcorpusSerializer,
    CorpusShareCreateSerializer,
    CorpusShareReadSerializer,
    CorpusAccessGrantSerializer,
)
from ..serializers import UserSubcorpusSerializer


class CreateShareAPI(APIView):
    """POST /subcorpora/<id>/share/ — owner creates a share link/code."""
    permission_classes = [IsAuthenticated]

    def post(self, request, subcorpus_id):
        subcorpus = get_object_or_404(UserSubcorpus, id=subcorpus_id)
        if subcorpus.creator != request.user:
            return Response(
                {"error": "Тільки власник може створювати посилання для доступу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SubcorpusShareCreateSerializer(data=request.data)
        if serializer.is_valid():
            share = serializer.save(
                subcorpus=subcorpus,
                created_by=request.user,
            )
            return Response(
                SubcorpusShareReadSerializer(share).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListSharesAPI(APIView):
    """GET /subcorpora/<id>/shares/ — owner lists shares for a subcorpus."""
    permission_classes = [IsAuthenticated]

    def get(self, request, subcorpus_id):
        subcorpus = get_object_or_404(UserSubcorpus, id=subcorpus_id)

        is_owner = subcorpus.creator == request.user
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')
        if not (is_owner or is_admin):
            return Response(
                {"error": "Доступ заборонено."},
                status=status.HTTP_403_FORBIDDEN,
            )

        shares = subcorpus.shares.all()
        serializer = SubcorpusShareReadSerializer(shares, many=True)
        return Response(serializer.data)


class RevokeShareAPI(APIView):
    """DELETE /shares/<id>/ — owner or admin deactivates a share."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, share_id):
        share = get_object_or_404(SubcorpusShare, id=share_id)

        is_owner = share.created_by == request.user
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')
        if not (is_owner or is_admin):
            return Response(
                {"error": "Доступ заборонено."},
                status=status.HTTP_403_FORBIDDEN,
            )

        share.is_active = False
        share.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RedeemShareAPI(APIView):
    """POST /shares/redeem/ — authenticated user redeems a code or link token."""
    permission_classes = [IsRegisteredUser]

    def post(self, request):
        serializer = ShareRedeemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        subcorpus_share = None
        corpus_share = None

        if data.get('access_code'):
            code = data['access_code'].upper()
            subcorpus_share = SubcorpusShare.objects.filter(access_code=code).first()
            if not subcorpus_share:
                corpus_share = CorpusShare.objects.filter(access_code=code).first()
        elif data.get('link_token'):
            token = data['link_token']
            subcorpus_share = SubcorpusShare.objects.filter(link_token=token).first()
            if not subcorpus_share:
                corpus_share = CorpusShare.objects.filter(link_token=token).first()

        if subcorpus_share:
            return self._redeem_subcorpus(request, subcorpus_share)
        elif corpus_share:
            return self._redeem_corpus(request, corpus_share)
        else:
            return Response(
                {"error": "Невірний код доступу або посилання."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def _redeem_subcorpus(self, request, share):
        if not share.is_valid:
            return Response(
                {"error": "Це посилання вже недійсне або вичерпало ліміт використань."},
                status=status.HTTP_410_GONE,
            )

        if share.subcorpus.creator == request.user:
            return Response(
                {"error": "Ви вже є власником цього підкорпусу."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grant, created = SubcorpusAccessGrant.objects.get_or_create(
            subcorpus=share.subcorpus,
            user=request.user,
            defaults={
                'share': share,
                'permission_level': share.permission_level,
            },
        )

        if not created:
            if share.permission_level == 'EDIT' and grant.permission_level == 'VIEW':
                grant.permission_level = 'EDIT'
                grant.share = share
                grant.save()

        share.use_count += 1
        share.save()

        resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        data = SubcorpusAccessGrantSerializer(grant).data
        data['type'] = 'subcorpus'
        return Response(data, status=resp_status)

    def _redeem_corpus(self, request, share):
        if not share.is_valid:
            return Response(
                {"error": "Це посилання вже недійсне або вичерпало ліміт використань."},
                status=status.HTTP_410_GONE,
            )

        if share.corpus.creator == request.user:
            return Response(
                {"error": "Ви вже є власником цього корпусу."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access_level = (
            CorpusUserAccess.AccessLevel.EDITOR
            if share.permission_level == 'EDIT'
            else CorpusUserAccess.AccessLevel.VIEWER
        )

        grant, created = CorpusUserAccess.objects.get_or_create(
            corpus=share.corpus,
            user=request.user,
            defaults={'access_level': access_level},
        )

        if not created:
            if access_level == CorpusUserAccess.AccessLevel.EDITOR and \
               grant.access_level == CorpusUserAccess.AccessLevel.VIEWER:
                grant.access_level = access_level
                grant.save()

        share.use_count += 1
        share.save()

        resp_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({
            'corpus_id': share.corpus.id,
            'corpus_name': share.corpus.name,
            'access_level': grant.get_access_level_display(),
            'type': 'corpus',
        }, status=resp_status)


class SharedWithMeAPI(APIView):
    """GET /subcorpora/shared-with-me/ — list subcorpora the user has access to."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grants = SubcorpusAccessGrant.objects.filter(
            user=request.user
        ).select_related(
            'subcorpus', 'subcorpus__corpus', 'subcorpus__creator'
        ).order_by('-granted_at')

        serializer = SubcorpusAccessGrantSerializer(grants, many=True)
        return Response(serializer.data)


class DeriveSubcorpusAPI(APIView):
    """POST /subcorpora/<id>/derive/ — create a nested subcorpus from a shared one."""
    permission_classes = [IsAuthenticated]

    def post(self, request, subcorpus_id):
        parent = get_object_or_404(UserSubcorpus, id=subcorpus_id)

        is_owner = parent.creator == request.user
        has_grant = SubcorpusAccessGrant.objects.filter(
            subcorpus=parent, user=request.user
        ).exists()
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')

        if not (is_owner or has_grant or is_admin):
            return Response(
                {"error": "Доступ заборонено."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DeriveSubcorpusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        derived = UserSubcorpus.objects.create(
            name=serializer.validated_data['name'],
            creator=request.user,
            corpus=parent.corpus,
            parent_subcorpus=parent,
        )

        return Response(
            UserSubcorpusSerializer(derived).data,
            status=status.HTTP_201_CREATED,
        )


class CreateCorpusShareAPI(APIView):
    """POST /corpus/<id>/share/ — corpus owner/editor/admin creates a share code."""
    permission_classes = [IsAuthenticated]

    def post(self, request, corpus_id):
        corpus = get_object_or_404(Corpus, id=corpus_id)

        is_creator = corpus.creator == request.user
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')
        is_editor = CorpusUserAccess.objects.filter(
            corpus=corpus, user=request.user, access_level=CorpusUserAccess.AccessLevel.EDITOR
        ).exists()

        if not (is_creator or is_admin or is_editor):
            return Response(
                {"error": "Тільки власник, редактор або адміністратор може створювати посилання для доступу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CorpusShareCreateSerializer(data=request.data)
        if serializer.is_valid():
            share = serializer.save(corpus=corpus, created_by=request.user)
            return Response(
                CorpusShareReadSerializer(share).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListCorpusSharesAPI(APIView):
    """GET /corpus/<id>/shares/ — corpus owner/editor/admin lists shares."""
    permission_classes = [IsAuthenticated]

    def get(self, request, corpus_id):
        corpus = get_object_or_404(Corpus, id=corpus_id)

        is_creator = corpus.creator == request.user
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')
        is_editor = CorpusUserAccess.objects.filter(
            corpus=corpus, user=request.user, access_level=CorpusUserAccess.AccessLevel.EDITOR
        ).exists()

        if not (is_creator or is_admin or is_editor):
            return Response(
                {"error": "Доступ заборонено."},
                status=status.HTTP_403_FORBIDDEN,
            )

        shares = corpus.shares.all()
        return Response(CorpusShareReadSerializer(shares, many=True).data)


class RevokeCorpusShareAPI(APIView):
    """DELETE /corpus-shares/<id>/ — share creator or admin deactivates a corpus share."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, share_id):
        share = get_object_or_404(CorpusShare, id=share_id)

        is_owner = share.created_by == request.user
        is_admin = request.user.role in ('SUPER_ADMIN', 'ADMIN')
        if not (is_owner or is_admin):
            return Response(
                {"error": "Доступ заборонено."},
                status=status.HTTP_403_FORBIDDEN,
            )

        share.is_active = False
        share.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SharedCorporaWithMeAPI(APIView):
    """GET /corpus/shared-with-me/ — list corpora the user has access to via sharing."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        grants = CorpusUserAccess.objects.filter(
            user=request.user
        ).select_related('corpus', 'corpus__creator').order_by('-id')
        return Response(CorpusAccessGrantSerializer(grants, many=True).data)
