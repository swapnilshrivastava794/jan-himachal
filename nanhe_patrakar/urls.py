# nanhe_patrakar/urls.py
from django.urls import path
from .views import (
    LandingPageView,
    ParentRegistrationView,
    PaymentView,
    PaymentVerifyView,
    PaymentFailedView,
    DownloadAppView,
    PaymentSuccessView,
    razorpay_webhook,
)

app_name = 'nanhe_patrakar'

urlpatterns = [
    # Landing and Registration
    path('', LandingPageView.as_view(), name='landing'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    
    # Payment Flow
    path('payment/', PaymentView.as_view(), name='payment'),
    path('payment/verify/', PaymentVerifyView.as_view(), name='payment_verify'),
    path('payment/failed/', PaymentFailedView.as_view(), name='payment_failed'),
    
    # App Download (only accessible after payment)
    path('download-app/', DownloadAppView.as_view(), name='download_app'),
    
    # Manual Payment Success Page (Redirect Target)
    path('payment/success/', PaymentSuccessView.as_view(), name='payment_success'),
    
    # Razorpay Webhook
    path('razorpay/webhook/', razorpay_webhook, name='razorpay_webhook'),
]