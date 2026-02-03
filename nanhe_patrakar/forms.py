# forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from nanhe_patrakar.models import District, ParentProfile

User = get_user_model()

class ParentRegistrationForm(forms.Form):
    """Simplified parent registration form - mobile number becomes username"""
    
    full_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'पूरा नाम / Full Name'
        }),
        error_messages={
            'required': 'कृपया अपना पूरा नाम दर्ज करें / Please enter your full name'
        }
    )

    child_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'बच्चे का नाम (वैकल्पिक) / Child Name (Optional)'
        })
    )
    
    mobile = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'मोबाइल नंबर / 10-digit mobile number',
            'maxlength': '10'
        }),
        error_messages={
            'required': 'कृपया मोबाइल नंबर दर्ज करें / Please enter mobile number'
        }
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ईमेल पता / Email address'
        }),
        error_messages={
            'required': 'कृपया ईमेल पता दर्ज करें / Please enter email address',
            'invalid': 'कृपया वैध ईमेल पता दर्ज करें / Please enter valid email address'
        }
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
        """Validate mobile number"""
        mobile = self.cleaned_data.get('mobile')
        
        # Remove any non-digit characters
        mobile = re.sub(r'\D', '', mobile)
        
        # Check if exactly 10 digits
        if len(mobile) != 10:
            raise ValidationError('मोबाइल नंबर 10 अंकों का होना चाहिए / Mobile number must be 10 digits')
        
        # Check if starts with valid digit (6-9 for Indian numbers)
        if not re.match(r'^[6-9]\d{9}$', mobile):
            raise ValidationError('कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें / Please enter a valid 10-digit mobile number')
        
        # Check if mobile already exists as username
        if User.objects.filter(username=mobile).exists():
            raise ValidationError('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
        
        # Check if mobile already exists in ParentProfile
        if ParentProfile.objects.filter(mobile=mobile).exists():
            raise ValidationError('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
        
        return mobile

    def clean_email(self):
        """Validate email"""
        email = self.cleaned_data.get('email')
        
        # Convert to lowercase
        email = email.lower().strip()
        
        # Check if email already exists
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('यह ईमेल पहले से पंजीकृत है / This email is already registered')
        
        return email
