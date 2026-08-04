from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    LoginAPIView, RegisterUserAPI,
    AdminUserListAPI, AdminUserCreateAPI, AdminUserDetailAPI,
    AdminCorpusListAPI, AdminCorpusDeleteAPI, AdminTextDeleteAPI,
    AdminSubcorpusListAPI, AdminSubcorpusDeleteAPI,
    UserProfileView
)

urlpatterns = [
    path('register/', RegisterUserAPI.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('profile/', UserProfileView.as_view(), name='user-profile'),

    path('admin/users/', AdminUserListAPI.as_view(), name='admin_user_list'),
    path('admin/users/create/', AdminUserCreateAPI.as_view(), name='admin_user_create'),
    path('admin/users/<int:pk>/', AdminUserDetailAPI.as_view(), name='admin_user_detail'),
    path('admin/corpora/', AdminCorpusListAPI.as_view(), name='admin_corpus_list'),
    path('admin/corpora/<int:pk>/', AdminCorpusDeleteAPI.as_view(), name='admin_corpus_delete'),
    path('admin/corpora/<int:corpus_id>/subcorpora/', AdminSubcorpusListAPI.as_view(), name='admin_subcorpus_list'),
    path('admin/subcorpora/<int:pk>/', AdminSubcorpusDeleteAPI.as_view(), name='admin_subcorpus_delete'),
    path('admin/texts/<int:pk>/', AdminTextDeleteAPI.as_view(), name='admin_text_delete'),
]