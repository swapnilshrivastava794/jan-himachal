from django.urls import path
from .views import (
    LandingPageView,
    ParentRegistrationView,
    PaymentView,
    DownloadAppView,
)

app_name = 'nanhe_patrakar'

urlpatterns = [
    # Landing and Registration
    path('landing/', LandingPageView.as_view(), name='landing'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    
    # Payment
    path('payment/', PaymentView.as_view(), name='payment'),
    
    # App Download
    path('download-app/', DownloadAppView.as_view(), name='download_app'),
]