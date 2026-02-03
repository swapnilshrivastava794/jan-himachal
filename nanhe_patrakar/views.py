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
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django_user_agents.utils import get_user_agent


class LandingPageView(View):
    """Nanhe Patrakar landing page matching Jan Himachal design"""
    template_name = 'nanhe_patrakar/landing.html'

    def get(self, request):
        program = Program.get_active_program()
        
        if not program:
            messages.error(request, 'कोई सक्रिय कार्यक्रम उपलब्ध नहीं है / No active program available')
            return render(request, self.template_name, {'program': None, 'is_mobile': get_user_agent(request).is_mobile})
        
        context = {
            'is_mobile': get_user_agent(request).is_mobile,
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
            'program': program,
            'is_mobile': get_user_agent(request).is_mobile
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
            full_name = form.cleaned_data['full_name']
            child_name = form.cleaned_data.get('child_name') # Optional, not saving yet
            
            # Split full name
            name_parts = full_name.strip().split()
            first_name = name_parts[0]
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            # Use mobile number as username
            username = mobile
            
            # Check if mobile (username) already exists
            existing_user = User.objects.filter(username=username).first()
            if existing_user:
                try:
                    parent_profile = existing_user.parent_profile
                    if parent_profile.status != 'PAYMENT_COMPLETED':
                        # Existing user with pending payment -> Trigger Payment
                        login(request, existing_user)
                        
                        # Get or Create Order
                        order, created = ParticipationOrder.objects.get_or_create(
                            parent=parent_profile,
                            payment_status='PENDING',
                            defaults={
                                'program': program,
                                'amount': program.price
                            }
                        )
                        
                        # Generate Razorpay Order
                        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                        razorpay_order = client.order.create({
                            'amount': int(order.amount * 100),
                            'currency': settings.RAZORPAY_CURRENCY,
                            'receipt': order.order_id,
                            'payment_capture': 1
                        })
                        
                        order.razorpay_order_id = razorpay_order['id']
                        order.payment_status = 'PROCESSING'
                        order.save()

                        callback_url = request.build_absolute_uri(reverse('nanhe_patrakar:payment_verify'))

                        messages.info(request, "आपका पंजीकरण पहले से मौजूद है। कृपया भुगतान पूरा करें। / You are already registered. Please complete payment.")
                        
                        return render(request, self.template_name, {
                            'form': form, 
                            'program': program,
                            'is_mobile': get_user_agent(request).is_mobile,
                            'trigger_payment': True,
                            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                            'razorpay_order_id': razorpay_order['id'],
                            'amount': int(order.amount * 100),
                            'currency': settings.RAZORPAY_CURRENCY,
                            'callback_url': callback_url,
                            'parent': parent_profile
                        })
                    else:
                        form.add_error('mobile', 'आपका भुगतान पहले ही हो चुका है। कृपया लॉगिन करें। / Payment already completed. Please login.')
                        return render(request, self.template_name, {
                            'form': form, 
                            'program': program,
                            'is_mobile': get_user_agent(request).is_mobile
                        })
                except ParentProfile.DoesNotExist:
                     # User exists but no parent profile (should rarely happen here)
                     pass

            if User.objects.filter(email=email).exclude(username=username).exists():
                form.add_error('email', 'यह ईमेल पहले से पंजीकृत है / This email is already registered')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program,
                    'is_mobile': get_user_agent(request).is_mobile
                })
            
            # =============================================
            # STEP 2: CREATE ALL RECORDS IN A TRANSACTION
            # =============================================
            from django.db import transaction
            
            try:
                with transaction.atomic():
                    # Generate Default Password
                    generated_password = f"Jan@{mobile[-4:]}" # Example: Jan@4578

                    # Create user with mobile as username
                    user = User.objects.create_user(
                        username=username,  # Mobile number as username
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=generated_password
                    )

                    # Send Registration Email
                    apk_url = request.build_absolute_uri('/static/apk/janhimachal.apk')
                    subject = 'Nanhe Patrakar Registration Successful - Jan Himachal'
                    email_body = f"""
प्रिय {first_name} {last_name},

नन्हे पत्रकार कार्यक्रम में आपका स्वागत है!

आपका पंजीकरण सफल रहा है। आपके लॉगिन क्रेडenciales नीचे दिए गए हैं:

Username (मोबाइल नंबर): {username}
Password: {generated_password}

आप नीचे दिए गए लिंक से जन हिमाचल ऐप डाउनलोड कर सकते हैं:
{apk_url}

महत्वपूर्ण: कृपया भुगतान पूरा करने के बाद ही ऐप में लॉगिन करें।

धन्यवाद,
जन हिमाचल टीम
                    """
                    try:
                        print(f"DEBUG: Attempting to send registration email to {email}...")
                        send_mail(
                            subject,
                            email_body,
                            settings.DEFAULT_FROM_EMAIL,
                            [email],
                            fail_silently=False,
                        )
                        print("DEBUG: Email sent successfully.")
                    except Exception as e:
                        print(f"CRITICAL ERROR sending email: {str(e)}")

                    # Create parent profile
                    parent_profile = ParentProfile.objects.create(
                        user=user,
                        program=program,
                        mobile=mobile,
                        status='PAYMENT_PENDING',
                        terms_accepted=form.cleaned_data['terms_accepted'],
                        terms_accepted_at=timezone.now() if form.cleaned_data['terms_accepted'] else None
                    )

                    # Create Child Profile if name provided (or placeholder)
                    if child_name:
                        ChildProfile.objects.create(
                            parent=parent_profile,
                            name=child_name,
                            age_group='A',  # Default to Group A
                            is_active=True
                        )
                    else:
                        # Placeholder if no name provided
                        ChildProfile.objects.create(
                            parent=parent_profile,
                            name="To be updated",
                            age_group='A',
                            is_active=True
                        )

                    # Create order
                    order = ParticipationOrder.objects.create(
                        parent=parent_profile,
                        program=program,
                        amount=program.price,
                        payment_status='PENDING'
                    )

                    # Auto-login user
                    login(request, user)

                    # ---------------------------------------------------
                    # GENERATE RAZORPAY ORDER IMMEDIATELY (No Redirect)
                    # ---------------------------------------------------
                    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                    razorpay_order = client.order.create({
                        'amount': int(order.amount * 100),  # Amount in paise
                        'currency': settings.RAZORPAY_CURRENCY,
                        'receipt': order.order_id,
                        'payment_capture': 1
                    })
                    
                    order.razorpay_order_id = razorpay_order['id']
                    order.payment_status = 'PROCESSING'
                    order.save()

                    callback_url = request.build_absolute_uri(reverse('nanhe_patrakar:payment_verify'))

                # =============================================
                # STEP 3: RETURN RESPONSE
                # =============================================
                
                # AJAX Support
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'trigger_payment': True,
                        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                        'razorpay_order_id': razorpay_order['id'],
                        'amount': int(order.amount * 100),
                        'currency': settings.RAZORPAY_CURRENCY,
                        'callback_url': callback_url,
                        'prefill': {
                            'name': user.get_full_name(),
                            'email': user.email,
                            'contact': parent_profile.mobile
                        }
                    })

                # Render registration page again with Payment Context to trigger Modal (Fallback)
                return render(request, self.template_name, {
                    'form': form,
                    'program': program,
                    'is_mobile': get_user_agent(request).is_mobile,
                    'trigger_payment': True,  # Flag to JS
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'razorpay_order_id': razorpay_order['id'],
                    'amount': int(order.amount * 100),
                    'currency': settings.RAZORPAY_CURRENCY,
                    'callback_url': callback_url,
                    'parent': parent_profile
                })

            except Exception as e:
                # Transaction will be rolled back automatically
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'server': str(e)}}, status=500)

                messages.error(request, f'पंजीकरण में त्रुटि / Registration error: {str(e)}')
                return render(request, self.template_name, {
                    'form': form, 
                    'program': program,
                    'is_mobile': get_user_agent(request).is_mobile
                })

        # Form is not valid
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

        return render(request, self.template_name, {
            'form': form, 
            'program': program,
            'is_mobile': get_user_agent(request).is_mobile
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
                'is_mobile': get_user_agent(request).is_mobile,
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
                'is_mobile': get_user_agent(request).is_mobile,
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
                'program': program,
                'order': order,
                'is_mobile': get_user_agent(request).is_mobile,
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')


class PaymentSuccessView(View):
    """
    Static success page for Manual Registration flow.
    Razorpay Hosted Page will redirect here.
    """
    template_name = 'nanhe_patrakar/payment_success.html'

    def get(self, request):
        return render(request, self.template_name)


@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """
    Handle Razorpay Webhooks
    Updates order status, parent profile status, and sends success email
    """
    print("------- Razorpay Webhook Triggered -------")
    
    # Get webhook secret from settings
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    
    # Get signature from headers
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    
    if not webhook_signature:
        print("Error: Missing X-Razorpay-Signature header")
        return HttpResponse('Missing Signature', status=400)
    
    # Get request body
    request_body = request.body.decode('utf-8')
    
    # Verify signature
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    try:
        # Verify the webhook signature
        client.utility.verify_webhook_signature(request_body, webhook_signature, webhook_secret)
        print("Webhook Signature Verified Successfully")
        
        # Parse event data
        event = json.loads(request_body)
        event_type = event.get('event')
        
        print(f"Event Type: {event_type}")
        
        if event_type == 'payment.captured':
            payment_entity = event['payload']['payment']['entity']
            
            razorpay_payment_id = payment_entity['id']
            razorpay_order_id = payment_entity['order_id']
            amount = payment_entity['amount'] / 100 # Convert to Rupees
            
            print(f"Payment Captured: Order ID {razorpay_order_id}, Payment ID {razorpay_payment_id}")
            
            try:
                # Find the order
                order = ParticipationOrder.objects.get(razorpay_order_id=razorpay_order_id)
                
                # Update order only if not already success
                if order.payment_status != 'SUCCESS':
                    order.razorpay_payment_id = razorpay_payment_id
                    # order.razorpay_signature = webhook_signature # Webhooks don't return the checkout signature
                    order.payment_status = 'SUCCESS'
                    order.payment_date = timezone.now()
                    order.save()
                    
                    # Update parent profile
                    parent_profile = order.parent
                    parent_profile.status = 'PAYMENT_COMPLETED'
                    parent_profile.save()
                    
                    print(f"Order {order.order_id} and Parent {parent_profile.mobile} updated via Webhook")
                    
                    # -----------------------------------------------
                    # SEND SUCCESS EMAIL
                    # -----------------------------------------------
                    try:
                        subject = 'भुगतान सफल / Payment Successful - Nanhe Patrakar'
                        message = f"""
Dear Parent,

We have successfully received your payment of Rs. {amount} for Nanhe Patrakar registration.

Order ID: {order.order_id}
Transaction ID: {razorpay_payment_id}

Your login details:
Username: {parent_profile.mobile}
Password: (The password you set during registration)

Please login to the app/website to complete your child's profile and start participating.

Login here: https://janhimachal.com/nanhe-patrakar/login/

Regards,
Jan Himachal Team
                        """
                        
                        send_mail(
                            subject=subject,
                            message=message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[parent_profile.user.email],
                            fail_silently=True
                        )
                        print(f"Success Email sent to {parent_profile.user.email}")
                        
                    except Exception as e:
                        print(f"Error sending email: {str(e)}")
                    # -----------------------------------------------
                    
                else:
                    print(f"Order {order.order_id} already marked as SUCCESS")
                    
            except ParticipationOrder.DoesNotExist:
                print(f"Error: Order not found for Razorpay Order ID {razorpay_order_id}")
                return HttpResponse('Order Not Found', status=404)
        
        elif event_type == 'order.paid':
             # Note: logic for order.paid if needed
             pass
             
        return HttpResponse('Webhook Received', status=200)
        
    except razorpay.errors.SignatureVerificationError:
        print("!!! Webhook Signature Verification FAILED !!!")
        return HttpResponse('Invalid Signature', status=400)
        
    except Exception as e:
        print(f"Exception in Webhook: {str(e)}")
        return HttpResponse('Internal Server Error', status=500)
        