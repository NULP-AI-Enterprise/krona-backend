from django.urls import path
from . import views

urlpatterns = [
    path('concordance/', views.ConcordanceAPI.as_view(), name='api_concordance'),
    path('word-list/', views.WordListAPI.as_view(), name='api_word_list'),

    path('metadata-options/corpus/', views.CorpusMetadataOptionsAPI.as_view(), name='api_corpus_metadata_options'),
    path('metadata-options/text/', views.TextMetadataOptionsAPI.as_view(), name='api_text_metadata_options'),
    path('metadata-options/filtered-subcorpus/<int:corpus_id>/', views.FilteredSubcorpusMetadataOptionsAPI.as_view(), name='api_filtered_subcorpus_metadata_options'),

    path('corpus/', views.CreateCorpusAPI.as_view(), name='api_corpus_create'),
    path('corpus/list/', views.CorpusListAPI.as_view(), name='api_corpus_list'),
    path('corpus/<int:pk>/', views.CorpusAPI.as_view(), name='api_corpus_detail'),

    path('text/', views.CreateTextAPI.as_view(), name='api_text_create'),
    path('text/list/', views.TextListAPI.as_view(), name='api_text_list'),
    path('text/<int:pk>/', views.TextAPI.as_view(), name='api_text_detail'),

    path('filtered-subcorpus/', views.CreateFilteredSubcorpusAPI.as_view(), name='api_filtered_subcorpus_create'),
    path('filtered-subcorpus/<int:pk>/', views.FilteredSubcorpusAPI.as_view(), name='api_filtered_subcorpus_delete'),

    path('user-subcorpus/', views.CreateUserSubcorpusAPI.as_view(), name='api_user_subcorpus_create'),
    path('user-subcorpus/<int:pk>/', views.UserSubcorpusAPI.as_view(), name='api_user_subcorpus_delete'),
]
