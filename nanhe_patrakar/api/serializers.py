# nanhe_patrakar/api/serializers.py

from datetime import datetime
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import User
from nanhe_patrakar.models import (
    ParentProfile, ChildProfile, Submission, 
    District, Program, Topic, SubmissionMedia
)
from .utils import get_parent_children_payload
import re

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with Nanhe Patrakar context"""

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        user_type = "user"
        program_info = None

        if hasattr(self.user, 'parent_profile'):
            parent_profile = self.user.parent_profile
            user_type = "nanhe_patrakar"

            program_info = {
                "parent_id": parent_profile.id,
                "program_id": parent_profile.program.id if parent_profile.program else None,
                "program_name": parent_profile.program.name if parent_profile.program else None,
                "status": parent_profile.status,
                "mobile": parent_profile.mobile,
                "city": parent_profile.city,
                "district": parent_profile.district.name if parent_profile.district else None,

                # Children summary
                "children": get_parent_children_payload(parent_profile),

                # Optional / future-safe fields
                "kyc_status": getattr(parent_profile, 'kyc_status', None),
                "terms_accepted": parent_profile.terms_accepted,
                "terms_accepted_at": parent_profile.terms_accepted_at,
            }

        data.update({
            "user_id": self.user.id,
            "user_type": user_type,
            "refresh_expires": refresh.payload.get('exp'),
            "access_expires": data['access'] and None,
            "program_info": program_info
        })

        return data


class UserSerializer(serializers.ModelSerializer):
    """User basic info serializer"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class DistrictSerializer(serializers.ModelSerializer):
    """District serializer"""
    class Meta:
        model = District
        fields = ['id', 'name', 'name_hindi']


class DistrictListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for district list"""
    
    class Meta:
        model = District
        fields = ['id', 'name', 'name_hindi']
        

class ProgramSerializer(serializers.ModelSerializer):
    """Program serializer"""
    class Meta:
        model = Program
        fields = ['id', 'name', 'name_hindi', 'price', 'min_age', 'max_age']


class ParentChildMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildProfile
        fields = ['id', 'name']
        
        
class ParentProfileSerializer(serializers.ModelSerializer):
    """Parent profile serializer"""
    user = UserSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    program = ProgramSerializer(read_only=True)
    children = ParentChildMinimalSerializer(
        many=True,
        read_only=True
    )
    
    class Meta:
        model = ParentProfile
        fields = [
            'id', 'user', 'mobile', 'city', 'district', 
            'program', 'children', 'status', 'created_at'
        ]


class ChildProfileSerializer(serializers.ModelSerializer):
    """Child profile serializer"""
    parent = ParentProfileSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    age_group_display = serializers.CharField(source='get_age_group_display', read_only=True)
    
    class Meta:
        model = ChildProfile
        fields = [
            'id', 'parent', 'name', 'date_of_birth', 'age', 
            'age_group', 'age_group_display', 'gender', 'school_name', 
            'district', 'photo', 'is_active', 'created_at'
        ]
        read_only_fields = ['age_group', 'created_at']


class ChildProfileCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating child profile"""
    district_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ChildProfile
        fields = [
            'name', 'date_of_birth', 'age', 'gender', 
            'school_name', 'district_id', 'photo'
        ]
    
    def validate_age(self, value):
        if value < 8 or value > 16:
            raise serializers.ValidationError("Age must be between 8 and 16")
        return value
    
    def validate_district_id(self, value):
        if not District.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid district")
        return value


class TopicSerializer(serializers.ModelSerializer):
    """Topic serializer"""
    class Meta:
        model = Topic
        fields = ['id', 'title', 'title_hindi']

class SubmissionMediaSerializer(serializers.ModelSerializer):
    """Submission media serializer"""
    class Meta:
        model = SubmissionMedia
        fields = ['id', 'media_type', 'file', 'file_name', 'file_size', 'display_order', 'created_at']


class SubmissionSerializer(serializers.ModelSerializer):
    """Submission serializer with media files"""
    child = ChildProfileSerializer(read_only=True)
    topic = TopicSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    content_type_display = serializers.CharField(source='get_content_type_display', read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    media_files = SubmissionMediaSerializer(many=True, read_only=True)  # NEW
    
    class Meta:
        model = Submission
        fields = [
            'id', 'submission_id', 'child', 'topic', 'title', 
            'content_type', 'content_type_display', 'language', 
            'language_display', 'content_text', 'audio_file', 
            'video_file', 'media_description', 'media_files',  # NEW
            'status', 'status_display', 'revision_reason', 
            'published_at', 'published_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['submission_id', 'created_at', 'updated_at']



class SubmissionCreateSerializer(serializers.Serializer):
    """Serializer for creating submission with multiple media files"""
    child_id = serializers.IntegerField()
    topic_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255)
    content_type = serializers.ChoiceField(choices=Submission.CONTENT_TYPE_CHOICES)
    language = serializers.ChoiceField(choices=Submission.LANGUAGE_CHOICES)
    content_text = serializers.CharField(required=False, allow_blank=True)
    media_description = serializers.CharField(required=False, allow_blank=True)
    
    # Multiple images and videos will be handled in the view
    
    def validate_child_id(self, value):
        if not ChildProfile.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid child profile")
        return value
    
    def validate_topic_id(self, value):
        if value and not Topic.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid topic")
        return value


class ChildProfileListSerializer(serializers.ModelSerializer):
    """Simplified child profile for listing"""
    parent_name = serializers.SerializerMethodField()
    latest_submission = serializers.SerializerMethodField()
    total_submissions = serializers.SerializerMethodField()
    
    class Meta:
        model = ChildProfile
        fields = [
            'id', 'name', 'age', 'age_group', 'parent_name',
            'latest_submission', 'total_submissions', 'created_at'
        ]
    
    def get_parent_name(self, obj):
        return obj.parent.user.get_full_name()
    
    def get_latest_submission(self, obj):
        latest = obj.submissions.order_by('-created_at').first()
        if latest:
            return {
                'id': latest.id,
                'title': latest.title,
                'status': latest.status,
                'created_at': latest.created_at
            }
        return None
    
    def get_total_submissions(self, obj):
        return obj.submissions.count()
    

class ParentRegistrationSerializer(serializers.Serializer):
    """Serializer for parent registration"""
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    username = serializers.CharField(max_length=150, required=False)
    mobile = serializers.CharField(max_length=15)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(min_length=6, write_only=True, required=False)
    city = serializers.CharField(max_length=100)
    district_id = serializers.IntegerField()
    terms_accepted = serializers.BooleanField()
    
    def validate_mobile(self, value):
        # Remove spaces and special characters
        import re
        mobile = re.sub(r'[^\d+]', '', value)
        
        # Validate Indian mobile number format
        if not re.match(r'^[6-9]\d{9}$', mobile):
            raise serializers.ValidationError('कृपया वैध 10 अंकों का मोबाइल नंबर दर्ज करें / Please enter a valid 10-digit Indian mobile number')
        
        return mobile
    
    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError('आपको नियम और शर्तें स्वीकार करनी होंगी / You must accept the terms and conditions')
        return value
    
    def validate_district_id(self, value):
        if not District.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError('अमान्य जिला / Invalid district')
        return value