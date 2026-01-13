from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.urls import reverse
from .forms import ParentRegistrationForm
from .models import ParentProfile, ParticipationOrder, Program
import razorpay


class LandingPageView(View):
    """Nanhe Patrakar landing page matching Jan Himachal design"""
    template_name = 'nanhe_patrakar/landing.html'

    def get(self, request):
        program = Program.get_active_program()
        
        if not program:
            messages.error(request, 'कोई सक्रिय कार्यक्रम उपलब्ध नहीं है / No active program available')
            return render(request, self.template_name, {'program': None})
        
        context = {
            'program': program,
            'age_groups': [
                {
                    'name': 'Group A',
                    'name_hindi': 'समूह अ',
                    'range': f'{program.age_group_a_min}-{program.age_group_a_max} years',
                    'range_hindi': f'{program.age_group_a_min}-{program.age_group_a_max} वर्ष'
                },
                {
                    'name': 'Group B',
                    'name_hindi': 'समूह ब',
                    'range': f'{program.age_group_b_min}-{program.age_group_b_max} years',
                    'range_hindi': f'{program.age_group_b_min}-{program.age_group_b_max} वर्ष'
                },
                {
                    'name': 'Group C',
                    'name_hindi': 'समूह स',
                    'range': f'{program.age_group_c_min}-{program.age_group_c_max} years',
                    'range_hindi': f'{program.age_group_c_min}-{program.age_group_c_max} वर्ष'
                },
            ]
        }
        return render(request, self.template_name, context)


class ParentRegistrationView(View):
    """Parent registration view"""
    template_name = 'nanhe_patrakar/registration.html'
    form_class = ParentRegistrationForm

    def get(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'parent_profile'):
            return redirect('nanhe_patrakar:payment')

        program = Program.get_active_program()
        if not program:
            messages.error(request, 'पंजीकरण बंद है / Registration is closed')
            return redirect('nanhe_patrakar:landing')

        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'program': program})

    def post(self, request):
        program = Program.get_active_program()
        if not program:
            messages.error(request, 'पंजीकरण बंद है / Registration is closed')
            return redirect('nanhe_patrakar:landing')

        form = self.form_class(request.POST)
        
        if form.is_valid():
            try:
                # ONLY CHANGE THIS PART - Create user with username and password
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],  # Changed from mobile
                    email=form.cleaned_data['email'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    password=form.cleaned_data['password']  # Added password
                )

                # Rest remains the same
                parent_profile = ParentProfile.objects.create(
                    user=user,
                    program=program,
                    mobile=form.cleaned_data['mobile'],
                    city=form.cleaned_data['city'],
                    district=form.cleaned_data['district'],
                    status='PAYMENT_PENDING',
                    terms_accepted=form.cleaned_data['terms_accepted'],
                    terms_accepted_at=timezone.now() if form.cleaned_data['terms_accepted'] else None
                )

                ParticipationOrder.objects.create(
                    parent=parent_profile,
                    program=program,
                    amount=program.price,
                    payment_status='PENDING'
                )

                # Auto-login user
                login(request, user)

                messages.success(request, 'पंजीकरण सफल! अब भुगतान के साथ आगे बढ़ें / Registration successful! Please proceed with payment')
                return redirect('nanhe_patrakar:payment')  # Same redirect

            except Exception as e:
                messages.error(request, f'पंजीकरण में त्रुटि / Registration error: {str(e)}')

        return render(request, self.template_name, {'form': form, 'program': program})
    
    
class PaymentView(LoginRequiredMixin, View):
    """Display payment page with Razorpay integration"""
    template_name = 'nanhe_patrakar/payment.html'
    login_url = 'nanhe_patrakar:register'

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            
            # Check if already paid
            if parent_profile.status == 'PAYMENT_COMPLETED':
                return redirect('nanhe_patrakar:download_app')
            
            # Get or create pending order
            order = ParticipationOrder.objects.filter(
                parent=parent_profile,
                payment_status='PENDING'
            ).first()
            
            if not order:
                order = ParticipationOrder.objects.create(
                    parent=parent_profile,
                    program=parent_profile.program,
                    amount=parent_profile.program.price,
                    payment_status='PENDING'
                )
            
            # Create Razorpay order
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            razorpay_order = client.order.create({
                'amount': int(order.amount * 100),  # Amount in paise
                'currency': settings.RAZORPAY_CURRENCY,
                'receipt': order.order_id,
                'payment_capture': 1  # Auto capture
            })
            
            # Save Razorpay order ID
            order.razorpay_order_id = razorpay_order['id']
            order.payment_status = 'PROCESSING'
            order.save()
            
            # Build absolute callback URL using reverse
            callback_url = request.build_absolute_uri(
                reverse('nanhe_patrakar:payment_verify')
            )
            
            context = {
                'parent': parent_profile,
                'program': parent_profile.program,
                'order': order,
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'razorpay_order_id': razorpay_order['id'],
                'amount': int(order.amount * 100),
                'currency': settings.RAZORPAY_CURRENCY,
                'callback_url': callback_url,
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')


@method_decorator(csrf_exempt, name='dispatch')
class PaymentVerifyView(View):
    """Verify Razorpay payment"""
    
    def post(self, request):
        try:
            # Get payment details from request
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            # Find the order
            order = ParticipationOrder.objects.get(razorpay_order_id=razorpay_order_id)
            
            # Verify signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify payment signature
            client.utility.verify_payment_signature(params_dict)
            
            # Signature verified - Payment successful
            order.razorpay_payment_id = razorpay_payment_id
            order.razorpay_signature = razorpay_signature
            order.payment_status = 'SUCCESS'
            order.payment_date = timezone.now()
            order.save()
            
            # Update parent profile status
            parent_profile = order.parent
            parent_profile.status = 'PAYMENT_COMPLETED'
            parent_profile.save()
            
            messages.success(request, 'भुगतान सफल! Payment successful!')
            return redirect('nanhe_patrakar:download_app')
            
        except razorpay.errors.SignatureVerificationError:
            # Signature verification failed
            if 'order' in locals():
                order.payment_status = 'FAILED'
                order.save()
            messages.error(request, 'भुगतान सत्यापन विफल / Payment verification failed')
            return redirect('nanhe_patrakar:payment_failed')
            
        except ParticipationOrder.DoesNotExist:
            messages.error(request, 'ऑर्डर नहीं मिला / Order not found')
            return redirect('nanhe_patrakar:payment_failed')
            
        except Exception as e:
            messages.error(request, f'त्रुटि / Error: {str(e)}')
            return redirect('nanhe_patrakar:payment_failed')


class PaymentFailedView(LoginRequiredMixin, View):
    """Payment failed page"""
    template_name = 'nanhe_patrakar/payment_failed.html'
    login_url = 'nanhe_patrakar:register'

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            program = parent_profile.program
            
            context = {
                'parent': parent_profile,
                'program': program,
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            return redirect('nanhe_patrakar:register')


class DownloadAppView(LoginRequiredMixin, View):
    """App download page - only accessible after successful payment"""
    template_name = 'nanhe_patrakar/download_app.html'
    login_url = 'nanhe_patrakar:register'

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            program = parent_profile.program
            
            # Check if payment is completed
            if parent_profile.status != 'PAYMENT_COMPLETED':
                messages.warning(request, 'कृपया पहले भुगतान पूरा करें / Please complete payment first')
                return redirect('nanhe_patrakar:payment')
            
            # Get successful order
            order = ParticipationOrder.objects.filter(
                parent=parent_profile,
                payment_status='SUCCESS'
            ).first()
            
            if not order:
                messages.warning(request, 'भुगतान रिकॉर्ड नहीं मिला / Payment record not found')
                return redirect('nanhe_patrakar:payment')
            
            context = {
                'parent': parent_profile,
                'program': program,
                'order': order
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')
    """App download page with instructions"""
    template_name = 'nanhe_patrakar/download_app.html'
    login_url = '/nanhe-patrakar/register/'

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            program = parent_profile.program
            
            # Check if payment is completed
            if parent_profile.status != 'PAYMENT_COMPLETED':
                messages.warning(request, 'कृपया पहले भुगतान पूरा करें / Please complete payment first')
                return redirect('nanhe_patrakar:payment')
            
            context = {
                'parent': parent_profile,
                'program': program,
                'order': ParticipationOrder.objects.filter(
                    parent=parent_profile,
                    payment_status='SUCCESS'
                ).first()
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')
        