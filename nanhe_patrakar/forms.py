from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import ParentProfile, District
import re


class ParentRegistrationForm(forms.Form):
    """Parent registration form"""
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'अपना नाम दर्ज करें / Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'अपना उपनाम दर्ज करें / Enter your last name'
        })
    )
    mobile = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'मोबाइल नंबर / 10-digit mobile number'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ईमेल पता / Email address'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'शहर / City'
        })
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.filter(is_active=True),
        required=True,
        empty_label="जिला चुनें / Select District",
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        error_messages={
            'required': 'आपको नियम और शर्तें स्वीकार करनी होंगी / You must accept the terms and conditions'
        }
    )

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        
        # Remove spaces and special characters
        mobile = re.sub(r'[^\d+]', '', mobile)
        
        # Validate Indian mobile number format
        if not re.match(r'^[6-9]\d{9}$', mobile):
            raise ValidationError('कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें / Please enter a valid 10-digit Indian mobile number')
        
        # Check if mobile already exists
        if ParentProfile.objects.filter(mobile=mobile).exists():
            raise ValidationError('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
        
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError('यह ईमेल पहले से पंजीकृत है / This email is already registered')
        
        return email.lower()


class OTPVerificationForm(forms.Form):
    """OTP verification form"""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '000000',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'autocomplete': 'off'
        })
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if not otp.isdigit():
            raise ValidationError('OTP में केवल संख्याएं होनी चाहिए / OTP must contain only numbers')
        return otp