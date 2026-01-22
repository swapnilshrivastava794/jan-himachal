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
from .models import ParentProfile, ParticipationOrder, Program, ChildProfile, District
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
    """Parent registration view - Simplified with mobile as username"""
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
        return render(request, self.template_name, {
            'form': form, 
            'program': program
        })

    def post(self, request):
        program = Program.get_active_program()
        if not program:
            messages.error(request, 'पंजीकरण बंद है / Registration is closed')
            return redirect('nanhe_patrakar:landing')

        form = self.form_class(request.POST, request.FILES)
        
        if form.is_valid():
            # =============================================
            # STEP 1: EXTRACT AND VALIDATE DATA
            # =============================================
            mobile = form.cleaned_data['mobile']
            email = form.cleaned_data['email']
            
            # Use mobile number as username
            username = mobile
            
            # Check if mobile (username) already exists
            if User.objects.filter(username=username).exists():
                form.add_error('mobile', 'यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program
                })
            
            # Check if email already exists
            if User.objects.filter(email=email).exists():
                form.add_error('email', 'यह ईमेल पहले से पंजीकृत है / This email is already registered')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program
                })
            
            # Check if mobile already exists in ParentProfile (redundant but safe)
            if ParentProfile.objects.filter(mobile=mobile).exists():
                form.add_error('mobile', 'यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program
                })
            
            # =============================================
            # STEP 2: CREATE ALL RECORDS IN A TRANSACTION
            # =============================================
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    # Create user with mobile as username
                    user = User.objects.create_user(
                        username=username,  # Mobile number as username
                        email=email,
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        password=form.cleaned_data['password']
                    )

                    # Create parent profile (city and district are optional now)
                    parent_profile = ParentProfile.objects.create(
                        user=user,
                        program=program,
                        mobile=mobile,
                        city=None,  # Will be updated later
                        district=None,  # Will be updated later
                        status='PAYMENT_PENDING',
                        id_proof=None,
                        terms_accepted=form.cleaned_data['terms_accepted'],
                        terms_accepted_at=timezone.now() if form.cleaned_data['terms_accepted'] else None
                    )

                    # Create a placeholder/temporary Child Profile
                    # This will be updated later by the parent with complete information
                    ChildProfile.objects.create(
                        parent=parent_profile,
                        name="To be updated",  # Placeholder name
                        gender=None,  # Will be updated later
                        date_of_birth=None,  # Will be updated later
                        age=None,  # Will be updated later
                        school_name=None,  # Will be updated later
                        district=None,  # Will be updated later
                        photo=None,  # Will be updated later
                        age_group='A',  # Default age group, will be updated later
                        is_active=True
                    )

                    # Create order
                    ParticipationOrder.objects.create(
                        parent=parent_profile,
                        program=program,
                        amount=program.price,
                        payment_status='PENDING'
                    )

                    # Auto-login user
                    login(request, user)

                messages.success(
                    request, 
                    'पंजीकरण सफल! अब भुगतान के साथ आगे बढ़ें। भुगतान के बाद आप अपने बच्चे का पूरा विवरण अपडेट कर सकते हैं। / Registration successful! Please proceed with payment. After payment, you can update your child\'s complete details.'
                )
                return redirect('nanhe_patrakar:payment')

            except Exception as e:
                # Transaction will be rolled back automatically
                messages.error(request, f'पंजीकरण में त्रुटि / Registration error: {str(e)}')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program
                })

        # Form is not valid
        return render(request, self.template_name, {
            'form': form, 
            'program': program
        })
           
    
class PaymentView(LoginRequiredMixin, View):
    """Display payment page with Razorpay integration"""
    template_name = 'nanhe_patrakar/payment.html'
    login_url = 'nanhe_patrakar:register'

    def get(self, request):
        print("------- PaymentView GET Triggered -------")
        try:
            parent_profile = request.user.parent_profile
            print(f"User: {request.user.username}, Parent: {parent_profile.mobile}")
            
            # Check if already paid
            if parent_profile.status == 'PAYMENT_COMPLETED':
                print("Payment already completed, redirecting to download.")
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
                print(f"Created new Pending Order: {order.order_id}")
            else:
                print(f"Found existing Pending Order: {order.order_id}")
            
            # Create Razorpay order
            print(f"Creating Razorpay Order with Key ID: {settings.RAZORPAY_KEY_ID}")
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            razorpay_order = client.order.create({
                'amount': int(order.amount * 100),  # Amount in paise
                'currency': settings.RAZORPAY_CURRENCY,
                'receipt': order.order_id,
                'payment_capture': 1  # Auto capture
            })
            print(f"Razorpay Order Created: {razorpay_order['id']}")
            
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
            print("Error: ParentProfile not found for user")
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')
        except Exception as e:
            print(f"Error in PaymentView: {str(e)}")
            raise e


@method_decorator(csrf_exempt, name='dispatch')
class PaymentVerifyView(View):
    """Verify Razorpay payment"""
    
    def post(self, request):
        print("------- PaymentVerifyView POST Triggered -------")
        try:
            # Get payment details from request
            razorpay_payment_id = request.POST.get('razorpay_payment_id')
            razorpay_order_id = request.POST.get('razorpay_order_id')
            razorpay_signature = request.POST.get('razorpay_signature')
            
            print(f"Received Payment ID: {razorpay_payment_id}")
            print(f"Received Order ID: {razorpay_order_id}")
            
            # Find the order
            order = ParticipationOrder.objects.get(razorpay_order_id=razorpay_order_id)
            print(f"Found Local Order: {order.order_id}")
            
            # Verify signature
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify payment signature
            print("Verifying Signature...")
            client.utility.verify_payment_signature(params_dict)
            print("Signature Verified Successfully!")
            
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
            print(f"Updated Parent Profile Status to PAYMENT_COMPLETED for {parent_profile.mobile}")
            
            messages.success(request, 'भुगतान सफल! Payment successful!')
            return redirect('nanhe_patrakar:download_app')
            
        except razorpay.errors.SignatureVerificationError:
            print("!!! Signature Verification FAILED !!!")
            # Signature verification failed
            if 'order' in locals():
                order.payment_status = 'FAILED'
                order.save()
            messages.error(request, 'भुगतान सत्यापन विफल / Payment verification failed')
            return redirect('nanhe_patrakar:payment_failed')
            
        except ParticipationOrder.DoesNotExist:
            print(f"Error: Order not found for Razorpay Order ID {razorpay_order_id}")
            messages.error(request, 'ऑर्डर नहीं मिला / Order not found')
            return redirect('nanhe_patrakar:payment_failed')
            
        except Exception as e:
            print(f"Exception in Verify: {str(e)}")
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
        