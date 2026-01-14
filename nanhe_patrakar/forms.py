# forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from nanhe_patrakar.models import District, ParentProfile

User = get_user_model()


# class ParentRegistrationForm(forms.Form):
#     """Parent registration form with username and password"""
    
#     first_name = forms.CharField(
#         max_length=150,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'अपना नाम दर्ज करें / Enter your first name'
#         })
#     )
    
#     last_name = forms.CharField(
#         max_length=150,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'अपना उपनाम दर्ज करें / Enter your last name'
#         })
#     )
    
#     username = forms.CharField(
#         max_length=150,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'यूजरनेम / Username (for login)'
#         }),
#         help_text='लॉगिन के लिए उपयोग किया जाएगा / Will be used for login'
#     )
    
#     mobile = forms.CharField(
#         max_length=15,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'मोबाइल नंबर / 10-digit mobile number'
#         })
#     )
    
#     email = forms.EmailField(
#         required=True,
#         widget=forms.EmailInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'ईमेल पता / Email address'
#         })
#     )
    
#     password = forms.CharField(
#         required=True,
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'पासवर्ड / Password'
#         }),
#         help_text='कम से कम 6 अक्षर / Minimum 6 characters'
#     )
    
#     confirm_password = forms.CharField(
#         required=True,
#         widget=forms.PasswordInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'पासवर्ड पुष्टि करें / Confirm Password'
#         })
#     )
    
#     city = forms.CharField(
#         max_length=100,
#         required=True,
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'placeholder': 'शहर / City'
#         })
#     )
    
#     district = forms.ModelChoiceField(
#         queryset=District.objects.filter(is_active=True),
#         required=True,
#         empty_label="जिला चुनें / Select District",
#         widget=forms.Select(attrs={
#             'class': 'form-control'
#         })
#     )
    
#     terms_accepted = forms.BooleanField(
#         required=True,
#         widget=forms.CheckboxInput(attrs={
#             'class': 'form-check-input'
#         }),
#         error_messages={
#             'required': 'आपको नियम और शर्तें स्वीकार करनी होंगी / You must accept the terms and conditions'
#         }
#     )

#     def clean_username(self):
#         username = self.cleaned_data.get('username')
        
#         # Remove leading/trailing spaces
#         username = username.strip()
        
#         # Check minimum length
#         if len(username) < 3:
#             raise ValidationError('यूजरनेम कम से कम 3 अक्षरों का होना चाहिए / Username must be at least 3 characters')
        
#         # Check for valid characters (alphanumeric, underscore, hyphen)
#         if not re.match(r'^[a-zA-Z0-9_-]+$', username):
#             raise ValidationError('यूजरनेम में केवल अक्षर, संख्या, अंडरस्कोर और हाइफन हो सकते हैं / Username can only contain letters, numbers, underscore and hyphen')
        
#         # Check if username already exists
#         if User.objects.filter(username__iexact=username).exists():
#             raise ValidationError('यह यूजरनेम पहले से उपयोग में है / This username is already taken')
        
#         return username.lower()

#     def clean_mobile(self):
#         mobile = self.cleaned_data.get('mobile')
        
#         # Remove spaces and special characters
#         mobile = re.sub(r'[^\d+]', '', mobile)
        
#         # Validate Indian mobile number format
#         if not re.match(r'^[6-9]\d{9}$', mobile):
#             raise ValidationError('कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें / Please enter a valid 10-digit Indian mobile number')
        
#         # Check if mobile already exists
#         if ParentProfile.objects.filter(mobile=mobile).exists():
#             raise ValidationError('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
        
#         return mobile

#     def clean_email(self):
#         email = self.cleaned_data.get('email')
        
#         # Check if email already exists
#         if User.objects.filter(email__iexact=email).exists():
#             raise ValidationError('यह ईमेल पहले से पंजीकृत है / This email is already registered')
        
#         return email.lower()

#     def clean_password(self):
#         password = self.cleaned_data.get('password')
        
#         # Check minimum length
#         if len(password) < 6:
#             raise ValidationError('पासवर्ड कम से कम 6 अक्षरों का होना चाहिए / Password must be at least 6 characters')
        
#         return password

#     def clean(self):
#         cleaned_data = super().clean()
#         password = cleaned_data.get('password')
#         confirm_password = cleaned_data.get('confirm_password')
        
#         # Check if passwords match
#         if password and confirm_password:
#             if password != confirm_password:
#                 raise ValidationError({
#                     'confirm_password': 'पासवर्ड मेल नहीं खाते / Passwords do not match'
#                 })
        
#         return cleaned_data


# # views.py
# from django.shortcuts import render, redirect
# from django.contrib.auth import login, get_user_model
# from django.contrib import messages
# from django.utils import timezone
# from django.views import View
# from nanhe_patrakar.models import Program, ParentProfile, ParticipationOrder

# User = get_user_model()


class ParentRegistrationForm(forms.Form):
    """Parent registration form - add username and password fields"""
    
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
    
    # NEW FIELD - Username
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'यूजरनेम / Username'
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
    
    # NEW FIELD - Password
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'पासवर्ड / Password'
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

    # Validation for username
    def clean_username(self):
        username = self.cleaned_data.get('username')
        username = username.strip()
        
        if len(username) < 3:
            raise ValidationError('यूजरनेम कम से कम 3 अक्षरों का होना चाहिए / Username must be at least 3 characters')
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('यह यूजरनेम पहले से उपयोग में है / This username is already taken')
        
        return username

    # Validation for password
    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        if len(password) < 6:
            raise ValidationError('पासवर्ड कम से कम 6 अक्षरों का होना चाहिए / Password must be at least 6 characters')
        
        return password

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        mobile = re.sub(r'[^\d+]', '', mobile)
        
        if not re.match(r'^[6-9]\d{9}$', mobile):
            raise ValidationError('कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें / Please enter a valid 10-digit Indian mobile number')
        
        if ParentProfile.objects.filter(mobile=mobile).exists():
            raise ValidationError('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
        
        return mobile

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('यह ईमेल पहले से पंजीकृत है / This email is already registered')
        
        return email.lower()
    