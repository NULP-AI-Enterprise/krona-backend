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

    # Sharing endpoints (subcorpus)
    path('subcorpora/<int:subcorpus_id>/share/', views.CreateShareAPI.as_view(), name='api_create_share'),
    path('subcorpora/<int:subcorpus_id>/shares/', views.ListSharesAPI.as_view(), name='api_list_shares'),
    path('shares/<int:share_id>/', views.RevokeShareAPI.as_view(), name='api_revoke_share'),
    path('shares/redeem/', views.RedeemShareAPI.as_view(), name='api_redeem_share'),
    path('subcorpora/shared-with-me/', views.SharedWithMeAPI.as_view(), name='api_shared_with_me'),
    path('subcorpora/<int:subcorpus_id>/derive/', views.DeriveSubcorpusAPI.as_view(), name='api_derive_subcorpus'),

    # Sharing endpoints (corpus)
    path('corpus/<int:corpus_id>/share/', views.CreateCorpusShareAPI.as_view(), name='api_create_corpus_share'),
    path('corpus/<int:corpus_id>/shares/', views.ListCorpusSharesAPI.as_view(), name='api_list_corpus_shares'),
    path('corpus-shares/<int:share_id>/', views.RevokeCorpusShareAPI.as_view(), name='api_revoke_corpus_share'),
    path('corpus/shared-with-me/', views.SharedCorporaWithMeAPI.as_view(), name='api_shared_corpora_with_me'),
]
