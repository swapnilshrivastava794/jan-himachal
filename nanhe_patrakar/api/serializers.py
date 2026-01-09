# nanhe_patrakar/api/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from nanhe_patrakar.models import (
    ParentProfile, ChildProfile, Submission, 
    District, Program, Topic, SubmissionMedia
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from datetime import datetime

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with user type detection"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Get the refresh token to extract expiration times
        refresh = self.get_token(self.user)
        
        # Determine user type based on Nanhe Patrakar registration
        user_type = "user"  # Default user type
        program_info = None
        
        # Check if user is registered to Nanhe Patrakar program
        if hasattr(self.user, 'parent_profile'):
            parent_profile = self.user.parent_profile
            user_type = "nanhe_patrakar"
            
            # Add parent profile information
            program_info = {
                "parent_id": parent_profile.id,
                "program_id": parent_profile.program.id if parent_profile.program else None,
                "program_name": parent_profile.program.name if parent_profile.program else None,
                "status": parent_profile.status,
                "mobile": parent_profile.mobile,
                "city": parent_profile.city,
                "district": parent_profile.district.name if parent_profile.district else None,
                "kyc_status": parent_profile.kyc_status if hasattr(parent_profile, 'kyc_status') else None,
            }
        
        # Calculate expiration times
        access_token_expiration = datetime.fromtimestamp(refresh.access_token['exp'])
        refresh_token_expiration = datetime.fromtimestamp(refresh['exp'])
        
        # Build response data
        data.update({
            "user_id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "full_name": self.user.get_full_name(),
            "user_type": user_type,
            "program_info": program_info,
            "access_token_expiration": access_token_expiration.isoformat(),
            "refresh_token_expiration": refresh_token_expiration.isoformat(),
            # Expiration in seconds from now
            "access_expires_in": int(refresh.access_token['exp'] - datetime.now().timestamp()),
            "refresh_expires_in": int(refresh['exp'] - datetime.now().timestamp()),
        })
        
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to token
        token['username'] = user.username
        token['email'] = user.email
        
        # Add user type to token
        if hasattr(user, 'parent_profile'):
            token['user_type'] = 'nanhe_patrakar'
        else:
            token['user_type'] = 'user'
        
        return token
    

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


class ParentProfileSerializer(serializers.ModelSerializer):
    """Parent profile serializer"""
    user = UserSerializer(read_only=True)
    district = DistrictSerializer(read_only=True)
    program = ProgramSerializer(read_only=True)
    
    class Meta:
        model = ParentProfile
        fields = [
            'id', 'user', 'mobile', 'city', 'district', 
            'program', 'status', 'created_at'
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