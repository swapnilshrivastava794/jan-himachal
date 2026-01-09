from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .forms import ParentRegistrationForm
from .models import ParentProfile, ParticipationOrder, Program


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
    """Payment page - For now redirects to app download"""
    template_name = 'nanhe_patrakar/payment.html'
    login_url = '/nanhe-patrakar/register/'

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            program = parent_profile.program
            
            # Get the latest pending order
            order = ParticipationOrder.objects.filter(
                parent=parent_profile,
                payment_status='PENDING'
            ).first()
            
            if not order:
                # Create new order if none exists
                order = ParticipationOrder.objects.create(
                    parent=parent_profile,
                    program=program,
                    amount=program.price,
                    payment_status='PENDING'
                )
            
            context = {
                'parent': parent_profile,
                'program': program,
                'order': order
            }
            
            return render(request, self.template_name, context)
            
        except ParentProfile.DoesNotExist:
            messages.error(request, 'कृपया पहले पंजीकरण करें / Please register first')
            return redirect('nanhe_patrakar:register')
    
    def post(self, request):
        """For now, just mark as success and redirect to download page"""
        try:
            parent_profile = request.user.parent_profile
            
            # Update order status (temporary until Razorpay integration)
            order = ParticipationOrder.objects.filter(
                parent=parent_profile,
                payment_status='PENDING'
            ).first()
            
            if order:
                order.payment_status = 'SUCCESS'
                order.payment_date = timezone.now()
                order.save()
            
            # Update parent status
            parent_profile.status = 'PAYMENT_COMPLETED'
            parent_profile.save()
            
            messages.success(request, 'भुगतान सफल! / Payment successful!')
            return redirect('nanhe_patrakar:download_app')
            
        except Exception as e:
            messages.error(request, f'भुगतान में त्रुटि / Payment error: {str(e)}')
            return redirect('nanhe_patrakar:payment')


class DownloadAppView(LoginRequiredMixin, View):
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