from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
from .models import CustomUser
from .permissions import IsAdminOrHigher
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    AdminUserListSerializer,
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    AdminCorpusListSerializer,
)
from corpus.models import Corpus, Text


class LoginAPIView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RegisterUserAPI(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens for the new user
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "User was successfully created!",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user_full_name": user.full_name,
                "user_email": user.email,
                "user_role": user.role,
            }, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


ROLE_HIERARCHY = [CustomUser.Role.USER, CustomUser.Role.COMPILER, CustomUser.Role.ADMIN, CustomUser.Role.SUPER_ADMIN]


def _can_manage_target(request_user, target_user):
    requester_level = ROLE_HIERARCHY.index(request_user.role)
    target_level = ROLE_HIERARCHY.index(target_user.role)
    return requester_level > target_level


class AdminUserListAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def get(self, request):
        queryset = CustomUser.objects.all().order_by('-date_joined')
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(full_name__icontains=search) |
                Q(phone_number__icontains=search)
            )
        serializer = AdminUserListSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminUserCreateAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def post(self, request):
        role = request.data.get('role', CustomUser.Role.USER)
        if request.user.role == CustomUser.Role.ADMIN and role in [CustomUser.Role.ADMIN, CustomUser.Role.SUPER_ADMIN]:
            return Response(
                {"error": "Ви не маєте права створювати користувачів з такою роллю."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AdminUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDetailAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def get(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        serializer = AdminUserListSerializer(user)
        return Response(serializer.data)

    def patch(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        if not _can_manage_target(request.user, user):
            return Response(
                {"error": "Ви не маєте права змінювати цього користувача."},
                status=status.HTTP_403_FORBIDDEN
            )

        new_role = request.data.get('role')
        if new_role and request.user.role == CustomUser.Role.ADMIN and new_role in [CustomUser.Role.ADMIN, CustomUser.Role.SUPER_ADMIN]:
            return Response(
                {"error": "Ви не можете призначити цю роль."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(AdminUserListSerializer(user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = get_object_or_404(CustomUser, pk=pk)
        if user.pk == request.user.pk:
            return Response(
                {"error": "Ви не можете видалити себе."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not _can_manage_target(request.user, user):
            return Response(
                {"error": "Ви не маєте права видаляти цього користувача."},
                status=status.HTTP_403_FORBIDDEN
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCorpusListAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def get(self, request):
        queryset = Corpus.objects.annotate(text_count=Count('text')).order_by('-update_time')
        serializer = AdminCorpusListSerializer(queryset, many=True)
        return Response(serializer.data)


class AdminCorpusDeleteAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def delete(self, request, pk):
        corpus = get_object_or_404(Corpus, pk=pk)
        corpus.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTextDeleteAPI(APIView):
    permission_classes = [IsAdminOrHigher]

    def delete(self, request, pk):
        text = get_object_or_404(Text, pk=pk)
        text.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)