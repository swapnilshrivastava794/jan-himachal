from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.utils import timezone
from django.core.cache import cache
import random
from .forms import ParentRegistrationForm, OTPVerificationForm
from .models import ParentProfile


class LandingPageView(View):
    """Nanhe Patrakar landing page matching Jan Himachal design"""
    template_name = 'nanhe_patrakar/landing.html'

    def get(self, request):
        context = {
            'program_fee': 599,
            'age_groups': [
                {'name': 'Group A', 'name_hindi': 'समूह अ', 'range': '8-10 years', 'range_hindi': '8-10 वर्ष'},
                {'name': 'Group B', 'name_hindi': 'समूह ब', 'range': '11-13 years', 'range_hindi': '11-13 वर्ष'},
                {'name': 'Group C', 'name_hindi': 'समूह स', 'range': '14-16 years', 'range_hindi': '14-16 वर्ष'},
            ]
        }
        return render(request, self.template_name, context)


class ParentRegistrationView(View):
    """Parent registration view"""
    template_name = 'nanhe_patrakar/registration.html'
    form_class = ParentRegistrationForm

    def get(self, request):
        # Check if user is already logged in and has parent profile
        if request.user.is_authenticated:
            if hasattr(request.user, 'parent_profile'):
                return redirect('nanhe_patrakar:payment')
        
        form = self.form_class()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = self.form_class(request.POST)
        
        if form.is_valid():
            # Store form data in session temporarily
            request.session['registration_data'] = {
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'mobile': form.cleaned_data['mobile'],
                'email': form.cleaned_data['email'],
                'city': form.cleaned_data['city'],
                'district_id': form.cleaned_data['district'].id,
                'terms_accepted': form.cleaned_data['terms_accepted'],
            }
            
            # Generate and send OTP
            otp = self.generate_otp()
            mobile = form.cleaned_data['mobile']
            
            # Store OTP in cache (expires in 5 minutes)
            cache.set(f'otp_{mobile}', otp, 300)
            
            # Send OTP via SMS
            self.send_otp(mobile, otp)
            
            messages.success(request, 'आपके मोबाइल नंबर पर OTP भेजा गया है / OTP has been sent to your mobile number')
            return redirect('nanhe_patrakar:verify_otp')
        
        return render(request, self.template_name, {'form': form})

    def generate_otp(self):
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))

    def send_otp(self, mobile, otp):
        """Send OTP via SMS gateway"""
        # TODO: Implement actual SMS gateway integration
        # For development, print OTP
        print(f"[NANHE PATRAKAR OTP] Mobile: {mobile}, OTP: {otp}")
        
        # Production implementation:
        # You can integrate with your existing SMS provider
        # from your_project.utils import send_sms
        # message = f"आपका नन्हे पत्रकार पंजीकरण OTP है: {otp}. यह 5 मिनट के लिए मान्य है। - जन हिमाचल"
        # send_sms(mobile, message)
        
        return True


class OTPVerificationView(View):
    """OTP verification view"""
    template_name = 'nanhe_patrakar/verify_otp.html'
    form_class = OTPVerificationForm

    def get(self, request):
        # Check if registration data exists in session
        if 'registration_data' not in request.session:
            messages.error(request, 'कृपया पहले पंजीकरण पूरा करें / Please complete registration first')
            return redirect('nanhe_patrakar:register')
        
        form = self.form_class()
        mobile = request.session['registration_data']['mobile']
        return render(request, self.template_name, {
            'form': form,
            'masked_mobile': self.mask_mobile(mobile)
        })

    def post(self, request):
        form = self.form_class(request.POST)
        
        if 'registration_data' not in request.session:
            messages.error(request, 'सत्र समाप्त हो गया। कृपया पुनः पंजीकरण करें / Session expired. Please register again')
            return redirect('nanhe_patrakar:register')
        
        if form.is_valid():
            entered_otp = form.cleaned_data['otp']
            mobile = request.session['registration_data']['mobile']
            stored_otp = cache.get(f'otp_{mobile}')
            
            if not stored_otp:
                messages.error(request, 'OTP समाप्त हो गया है। कृपया नया OTP मांगें / OTP has expired. Please request a new one')
                return redirect('nanhe_patrakar:register')
            
            if entered_otp == stored_otp:
                # OTP verified, create user account
                user = self.create_user_account(request.session['registration_data'])
                
                # Delete OTP from cache
                cache.delete(f'otp_{mobile}')
                
                # Clear session data
                del request.session['registration_data']
                
                # Auto-login user
                login(request, user)
                
                messages.success(request, 'पंजीकरण सफल रहा! कृपया भुगतान के साथ आगे बढ़ें / Registration successful! Please proceed with payment')
                return redirect('nanhe_patrakar:payment')
            else:
                messages.error(request, 'गलत OTP। कृपया पुनः प्रयास करें / Invalid OTP. Please try again')
        
        mobile = request.session['registration_data']['mobile']
        return render(request, self.template_name, {
            'form': form,
            'masked_mobile': self.mask_mobile(mobile)
        })

    def create_user_account(self, data):
        """Create user and parent profile"""
        # Create user
        user = User.objects.create_user(
            username=data['mobile'],  # Using mobile as username
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        
        # Create parent profile
        ParentProfile.objects.create(
            user=user,
            mobile=data['mobile'],
            city=data['city'],
            district_id=data['district_id'],
            status='REGISTERED_NOT_ACTIVATED',
            terms_accepted=data['terms_accepted'],
            terms_accepted_at=timezone.now() if data['terms_accepted'] else None
        )
        
        return user

    def mask_mobile(self, mobile):
        """Mask mobile number for display"""
        if len(mobile) >= 10:
            return f"******{mobile[-4:]}"
        return mobile


class ResendOTPView(View):
    """Resend OTP"""
    
    def post(self, request):
        if 'registration_data' not in request.session:
            return redirect('nanhe_patrakar:register')
        
        mobile = request.session['registration_data']['mobile']
        
        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        
        # Store in cache
        cache.set(f'otp_{mobile}', otp, 300)
        
        # Send OTP
        print(f"[NANHE PATRAKAR RESEND OTP] Mobile: {mobile}, OTP: {otp}")
        
        messages.success(request, 'नया OTP आपके मोबाइल नंबर पर भेजा गया है / New OTP has been sent to your mobile number')
        return redirect('nanhe_patrakar:verify_otp')
    