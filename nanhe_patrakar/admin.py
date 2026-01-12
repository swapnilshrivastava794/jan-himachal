from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Program, ParentProfile, ParticipationOrder, ChildProfile, 
    ParentConsent, Topic, Submission, Certificate, District, SubmissionMedia
)


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_hindi', 'price', 'min_age', 'max_age', 'is_active', 'registration_open', 'participants_count']
    list_filter = ['is_active', 'registration_open', 'created_at']
    search_fields = ['name', 'name_hindi', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Program Information', {
            'fields': ('name', 'name_hindi', 'slug', 'description', 'description_hindi', 'featured_image')
        }),
        ('Pricing & Age', {
            'fields': ('price', 'min_age', 'max_age')
        }),
        ('Age Groups Configuration', {
            'fields': (
                ('age_group_a_min', 'age_group_a_max'),
                ('age_group_b_min', 'age_group_b_max'),
                ('age_group_c_min', 'age_group_c_max')
            ),
            'description': 'Configure age ranges for each group'
        }),
        ('App Download Links', {
            'fields': ('android_app_url', 'ios_app_url')
        }),
        ('Program Status', {
            'fields': ('is_active', 'registration_open', 'display_order')
        }),
        ('Legal', {
            'fields': ('terms_and_conditions', 'privacy_policy'),
            'classes': ('collapse',)
        }),
    )
    
    def participants_count(self, obj):
        count = obj.participants.count()
        return format_html('<strong>{}</strong>', count)
    participants_count.short_description = 'Total Participants'


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'mobile', 'program', 'district', 'status_badge', 'id_proof_verified', 'created_at']
    list_filter = ['status', 'program', 'id_proof_verified', 'terms_accepted', 'district', 'created_at']
    search_fields = ['user__email', 'mobile', 'user__first_name', 'user__last_name', 'city']
    readonly_fields = ['created_at', 'updated_at', 'terms_accepted_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'mobile', 'program', 'status')
        }),
        ('Location', {
            'fields': ('city', 'district')
        }),
        ('Verification', {
            'fields': ('id_proof', 'id_proof_verified')
        }),
        ('Terms & Conditions', {
            'fields': ('terms_accepted', 'terms_accepted_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'REGISTERED': 'blue',
            'PAYMENT_PENDING': 'orange',
            'PAYMENT_COMPLETED': 'green',
            'ACTIVE': 'green',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(ParticipationOrder)
class ParticipationOrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'parent_name', 'program', 'amount', 'payment_status_badge', 'payment_date', 'created_at']
    list_filter = ['payment_status', 'program', 'payment_date', 'created_at']
    search_fields = ['order_id', 'invoice_number', 'razorpay_order_id', 'parent__user__email', 'parent__mobile']
    readonly_fields = ['order_id', 'invoice_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'parent', 'program', 'amount', 'payment_status')
        }),
        ('Razorpay Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'payment_method')
        }),
        ('Invoice', {
            'fields': ('invoice_number', 'invoice_url', 'payment_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parent_name(self, obj):
        return obj.parent.user.get_full_name()
    parent_name.short_description = 'Parent Name'
    
    def payment_status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'SUCCESS': 'green',
            'FAILED': 'red',
            'REFUNDED': 'gray',
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.payment_status
        )
    payment_status_badge.short_description = 'Payment Status'


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_name', 'age', 'age_group_badge', 'district', 'is_active', 'created_at']
    list_filter = ['age_group', 'is_active', 'district', 'gender', 'created_at']
    search_fields = ['name', 'parent__user__first_name', 'parent__user__last_name', 'school_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Child Information', {
            'fields': ('parent', 'name', 'date_of_birth', 'age', 'age_group', 'gender')
        }),
        ('Location & School', {
            'fields': ('district', 'school_name')
        }),
        ('Photo & Status', {
            'fields': ('photo', 'id_proof', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def parent_name(self, obj):
        return f"{obj.parent.user.get_full_name()} ({obj.parent.mobile})"
    parent_name.short_description = 'Parent'
    
    def age_group_badge(self, obj):
        colors = {'A': '#60a5fa', 'B': '#34d399', 'C': '#fbbf24'}
        labels = {'A': '8-10 yrs', 'B': '11-13 yrs', 'C': '14-16 yrs'}
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.age_group, 'gray'), labels.get(obj.age_group, obj.age_group)
        )
    age_group_badge.short_description = 'Age Group'


@admin.register(ParentConsent)
class ParentConsentAdmin(admin.ModelAdmin):
    list_display = ['child', 'all_consents_given', 'consent_given_at', 'ip_address']
    list_filter = ['parent_guidance_agreed', 'publication_consent', 'data_usage_agreed', 'consent_given_at']
    search_fields = ['child__name']
    readonly_fields = ['consent_given_at', 'ip_address']
    
    def all_consents_given(self, obj):
        if obj.parent_guidance_agreed and obj.publication_consent and obj.data_usage_agreed:
            return format_html('<span style="color: green;">✓ All Consents Given</span>')
        return format_html('<span style="color: red;">✗ Incomplete</span>')
    all_consents_given.short_description = 'Consent Status'


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'title_hindi', 'age_groups_display', 'is_active', 'display_order', 'submission_count']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'title_hindi']
    ordering = ['display_order', 'title']
    
    def age_groups_display(self, obj):
        groups = obj.get_age_groups_list()
        return ', '.join([f"Group {g}" for g in groups])
    age_groups_display.short_description = 'Age Groups'
    
    def submission_count(self, obj):
        count = obj.submissions.count()
        return format_html('<strong>{}</strong>', count)
    submission_count.short_description = 'Submissions'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['submission_id', 'child_name', 'title', 'status_badge', 'content_type', 'language', 'created_at']
    list_filter = ['status', 'content_type', 'language', 'child__age_group', 'created_at']
    search_fields = ['submission_id', 'title', 'child__name']
    readonly_fields = ['submission_id', 'created_at', 'updated_at', 'reviewed_at', 'published_at']
    
    fieldsets = (
        ('Submission Details', {
            'fields': ('submission_id', 'child', 'topic', 'title', 'content_type', 'language')
        }),
        ('Content', {
            'fields': ('content_text', 'audio_file', 'video_file', 'media_description')
        }),
        ('Status & Review', {
            'fields': ('status', 'reviewed_by', 'reviewed_at', 'revision_reason', 'editorial_notes')
        }),
        ('Publication', {
            'fields': ('published_at', 'published_url', 'seo_tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_submissions', 'publish_submissions']
    
    def child_name(self, obj):
        return obj.child.name
    child_name.short_description = 'Child Name'
    
    def status_badge(self, obj):
        colors = {
            'DRAFT': 'gray',
            'SUBMITTED': 'blue',
            'UNDER_REVIEW': 'orange',
            'REVISION_REQUESTED': 'yellow',
            'RESUBMITTED': 'lightblue',
            'APPROVED': 'lightgreen',
            'PUBLISHED': 'green',
            'REJECTED': 'red',
            'CERTIFICATE_ISSUED': 'purple',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.status.replace('_', ' ')
        )
    status_badge.short_description = 'Status'
    
    def approve_submissions(self, request, queryset):
        updated = queryset.filter(status='SUBMITTED').update(status='APPROVED')
        self.message_user(request, f'{updated} submissions approved successfully.')
    approve_submissions.short_description = 'Approve selected submissions'
    
    def publish_submissions(self, request, queryset):
        updated = queryset.filter(status='APPROVED').update(status='PUBLISHED')
        self.message_user(request, f'{updated} submissions published successfully.')
    publish_submissions.short_description = 'Publish selected submissions'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_id', 'child_name', 'age_group', 'issued_at', 'emailed_status']
    list_filter = ['age_group', 'emailed_to_parent', 'issued_at']
    search_fields = ['certificate_id', 'child_name', 'verification_code']
    readonly_fields = ['certificate_id', 'verification_code', 'issued_at', 'email_sent_at']
    
    def emailed_status(self, obj):
        if obj.emailed_to_parent:
            return format_html('<span style="color: green;">✓ Sent on {}</span>', obj.email_sent_at.strftime('%d %b %Y'))
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    emailed_status.short_description = 'Email Status'


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'name_hindi', 'is_active', 'parent_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'name_hindi']
    
    def parent_count(self, obj):
        count = ParentProfile.objects.filter(district=obj).count()
        return format_html('<strong>{}</strong>', count)
    parent_count.short_description = 'Registered Parents'
    
    
@admin.register(SubmissionMedia)
class SubmissionMediaAdmin(admin.ModelAdmin):
    list_display = ['submission', 'media_type', 'file_name', 'file_size_kb', 'display_order', 'created_at']
    list_filter = ['media_type', 'created_at']
    search_fields = ['submission__submission_id', 'file_name']
    
    def file_size_kb(self, obj):
        return f"{obj.file_size / 1024:.2f} KB"
    file_size_kb.short_description = 'File Size'


# Customize Admin Site
admin.site.site_header = 'नन्हे पत्रकार प्रबंधन / Nanhe Patrakar Administration'
admin.site.site_title = 'Nanhe Patrakar Admin'
admin.site.index_title = 'प्रबंधन डैशबोर्ड / Management Dashboard'