from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from correctionApp.views import *

router = DefaultRouter()
router.register(r'audiofiles', AudioFileViewSet)
router.register(r'audiosearchfiles', AudioSearchFileViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('user/', UserDetailByEmailView.as_view(), name='user-detail-by-email'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('hisb60/', Hisb60View.as_view(), name='hisb60'),
]
