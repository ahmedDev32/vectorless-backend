from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AskView, ChunkViewSet, DocumentIngestView, DocumentViewSet

router = DefaultRouter()
router.register('documents', DocumentViewSet)
router.register('chunks', ChunkViewSet)

urlpatterns = [
    path('ask/', AskView.as_view(), name='ask'),
    path('documents/ingest/', DocumentIngestView.as_view(), name='document-ingest'),
] + router.urls
