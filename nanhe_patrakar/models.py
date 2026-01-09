from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid


class ParentProfile(models.Model):
    """Parent profile with verification status"""
    STATUS_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('PAYMENT_COMPLETED', 'Payment Completed'),
        ('ACTIVE', 'Active'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    program = models.ForeignKey('Program', on_delete=models.PROTECT, related_name='participants')
    mobile = models.CharField(max_length=15, unique=True)
    city = models.CharField(max_length=100)
    district = models.ForeignKey('District', on_delete=models.PROTECT)
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='REGISTERED')
    id_proof = models.FileField(upload_to='parent_docs/', null=True, blank=True)
    id_proof_verified = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nanhe_patrakar_parent_profiles'
        verbose_name = 'Parent Profile'
        verbose_name_plural = 'Parent Profiles'

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.mobile}"


class ParticipationOrder(models.Model):
    """Payment and participation order tracking"""
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]

    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='orders')
    program = models.ForeignKey('Program', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    
    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)
    
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    invoice_url = models.URLField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nanhe_patrakar_participation_orders'
        ordering = ['-created_at']
        verbose_name = 'Participation Order'
        verbose_name_plural = 'Participation Orders'

    def __str__(self):
        return f"{self.order_id} - {self.parent.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"NP{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        if not self.invoice_number and self.payment_status == 'SUCCESS':
            self.invoice_number = f"INV{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


class ChildProfile(models.Model):
    """Child participant profile"""
    AGE_GROUP_CHOICES = [
        ('A', 'Group A (8-10 years)'),
        ('B', 'Group B (11-13 years)'),
        ('C', 'Group C (14-16 years)'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='children')
    name = models.CharField(max_length=200)
    date_of_birth = models.DateField()
    age = models.IntegerField(validators=[MinValueValidator(8), MaxValueValidator(16)])
    age_group = models.CharField(max_length=1, choices=AGE_GROUP_CHOICES)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    school_name = models.CharField(max_length=255, null=True, blank=True)
    district = models.ForeignKey('District', on_delete=models.PROTECT)
    photo = models.ImageField(upload_to='child_photos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nanhe_patrakar_child_profiles'
        verbose_name = 'Child Profile'
        verbose_name_plural = 'Child Profiles'

    def __str__(self):
        return f"{self.name} - Age Group {self.age_group}"

    def calculate_age_group(self):
        """Auto-assign age group based on age"""
        if 8 <= self.age <= 10:
            return 'A'
        elif 11 <= self.age <= 13:
            return 'B'
        elif 14 <= self.age <= 16:
            return 'C'
        return None

    def save(self, *args, **kwargs):
        if not self.age_group:
            self.age_group = self.calculate_age_group()
        super().save(*args, **kwargs)


class ParentConsent(models.Model):
    """Parent consent and verification"""
    child = models.OneToOneField(ChildProfile, on_delete=models.CASCADE, related_name='consent')
    parent_guidance_agreed = models.BooleanField(default=False)
    publication_consent = models.BooleanField(default=False)
    data_usage_agreed = models.BooleanField(default=False)
    consent_text = models.TextField()
    consent_given_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'nanhe_patrakar_parent_consents'
        verbose_name = 'Parent Consent'
        verbose_name_plural = 'Parent Consents'

    def __str__(self):
        return f"Consent for {self.child.name}"


class Topic(models.Model):
    """Content topics for different age groups"""
    title = models.CharField(max_length=100)
    title_hindi = models.CharField(max_length=100, null=True, blank=True)
    age_groups = models.CharField(max_length=10, help_text="Comma-separated: A,B,C")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nanhe_patrakar_topics'
        ordering = ['display_order', 'title']
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'

    def __str__(self):
        return self.title

    def get_age_groups_list(self):
        return [g.strip() for g in self.age_groups.split(',')]


class Submission(models.Model):
    """Child content submissions"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('REVISION_REQUESTED', 'Revision Requested'),
        ('RESUBMITTED', 'Resubmitted'),
        ('APPROVED', 'Approved'),
        ('PUBLISHED', 'Published'),
        ('REJECTED', 'Rejected'),
        ('CERTIFICATE_ISSUED', 'Certificate Issued'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('ARTICLE', 'Article'),
        ('POEM', 'Poem'),
        ('EXPERIENCE', 'Experience'),
        ('SPEECH', 'Speech'),
    ]

    LANGUAGE_CHOICES = [
        ('HINDI', 'Hindi'),
        ('ENGLISH', 'English'),
        ('LOCAL', 'Local Language'),
    ]

    submission_id = models.CharField(max_length=100, unique=True, db_index=True)
    child = models.ForeignKey(ChildProfile, on_delete=models.CASCADE, related_name='submissions')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, related_name='submissions')
    
    title = models.CharField(max_length=255)
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES)
    content_text = models.TextField(null=True, blank=True)
    
    # Media fields
    audio_file = models.FileField(upload_to='submissions/audio/', null=True, blank=True)
    video_file = models.FileField(upload_to='submissions/video/', null=True, blank=True)
    media_description = models.TextField(null=True, blank=True)
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='DRAFT')
    
    # Review fields
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    revision_reason = models.TextField(null=True, blank=True)
    editorial_notes = models.TextField(null=True, blank=True)
    
    # Publication fields
    published_at = models.DateTimeField(null=True, blank=True)
    published_url = models.URLField(null=True, blank=True)
    seo_tags = models.CharField(max_length=500, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nanhe_patrakar_submissions'
        ordering = ['-created_at']
        verbose_name = 'Submission'
        verbose_name_plural = 'Submissions'

    def __str__(self):
        return f"{self.submission_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.submission_id:
            self.submission_id = f"SUB{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

class SubmissionMedia(models.Model):
    """
    Store multiple media files for a submission
    This allows unlimited images and videos per submission
    """
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
        ('AUDIO', 'Audio'),
    ]
    
    submission = models.ForeignKey(
        'Submission', 
        on_delete=models.CASCADE, 
        related_name='media_files'
    )
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to='submissions/media/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")
    display_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'nanhe_patrakar_submission_media'
        ordering = ['display_order', 'created_at']
        verbose_name = 'Submission Media'
        verbose_name_plural = 'Submission Media'
    
    def __str__(self):
        return f"{self.media_type} - {self.submission.submission_id}"
    

class Certificate(models.Model):
    """Generated certificates for published content"""
    certificate_id = models.CharField(max_length=100, unique=True, db_index=True)
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, related_name='certificate')
    child_name = models.CharField(max_length=200)
    age_group = models.CharField(max_length=1)
    certificate_pdf = models.FileField(upload_to='certificates/')
    verification_code = models.CharField(max_length=50, unique=True)
    
    issued_at = models.DateTimeField(auto_now_add=True)
    emailed_to_parent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'nanhe_patrakar_certificates'
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'

    def __str__(self):
        return f"{self.certificate_id} - {self.child_name}"

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            self.certificate_id = f"CERT{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
        if not self.verification_code:
            self.verification_code = uuid.uuid4().hex[:12].upper()
        super().save(*args, **kwargs)


class District(models.Model):
    """Himachal Pradesh districts for validation"""
    name = models.CharField(max_length=100, unique=True)
    name_hindi = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'nanhe_patrakar_districts'
        ordering = ['name']
        verbose_name = 'District'
        verbose_name_plural = 'Districts'

    def __str__(self):
        return self.name


class Program(models.Model):
    """Dynamic program configuration"""
    name = models.CharField(max_length=200, help_text="Program name in English")
    name_hindi = models.CharField(max_length=200, help_text="Program name in Hindi")
    slug = models.SlugField(unique=True, help_text="URL friendly name")
    
    description = models.TextField(help_text="Program description in English")
    description_hindi = models.TextField(help_text="Program description in Hindi")
    
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Participation fee in INR")
    
    min_age = models.IntegerField(default=8, help_text="Minimum age for participation")
    max_age = models.IntegerField(default=16, help_text="Maximum age for participation")
    
    # App download links
    android_app_url = models.URLField(blank=True, null=True, help_text="Google Play Store URL")
    ios_app_url = models.URLField(blank=True, null=True, help_text="Apple App Store URL")
    
    # Age group configuration
    age_group_a_min = models.IntegerField(default=8)
    age_group_a_max = models.IntegerField(default=10)
    age_group_b_min = models.IntegerField(default=11)
    age_group_b_max = models.IntegerField(default=13)
    age_group_c_min = models.IntegerField(default=14)
    age_group_c_max = models.IntegerField(default=16)
    
    # Program status
    is_active = models.BooleanField(default=True)
    registration_open = models.BooleanField(default=True, help_text="Accept new registrations")
    
    # Additional details
    terms_and_conditions = models.TextField(blank=True)
    privacy_policy = models.TextField(blank=True)
    
    # Display settings
    display_order = models.IntegerField(default=0)
    featured_image = models.ImageField(upload_to='program_images/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nanhe_patrakar_programs'
        ordering = ['display_order', 'name']
        verbose_name = 'Program'
        verbose_name_plural = 'Programs'

    def __str__(self):
        return f"{self.name} (₹{self.price})"
    
    @classmethod
    def get_active_program(cls):
        """Get the first active program"""
        return cls.objects.filter(is_active=True, registration_open=True).first()