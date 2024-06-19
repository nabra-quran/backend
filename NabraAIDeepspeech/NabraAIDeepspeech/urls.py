from django.urls import path
from correctionApp.views import *

urlpatterns = [
    path('transcribe/', TranscriptionViewSet.as_view({'post': 'transcribe'}), name='transcribe'),
]