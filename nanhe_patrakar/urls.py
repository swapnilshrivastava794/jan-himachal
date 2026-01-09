from django.urls import path
from .views import (
    LandingPageView,
    ParentRegistrationView,
    OTPVerificationView,
    ResendOTPView,
)

app_name = 'nanhe_patrakar'

urlpatterns = [
    # Landing and Registration
    path('landing/', LandingPageView.as_view(), name='landing'),
    path('register/', ParentRegistrationView.as_view(), name='register'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend_otp'),
    
    # Payment (to be implemented)
    # path('payment/', PaymentView.as_view(), name='payment'),
    # path('payment/callback/', PaymentCallbackView.as_view(), name='payment_callback'),
    # path('payment/success/', PaymentSuccessView.as_view(), name='payment_success'),
]