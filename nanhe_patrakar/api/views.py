# nanhe_patrakar/api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max

from nanhe_patrakar.models import (
    ParentProfile, ChildProfile, Submission, 
    District, Topic, SubmissionMedia
)
from .serializers import (
    ParentProfileSerializer, ChildProfileSerializer,
    ChildProfileCreateSerializer, SubmissionSerializer,
    SubmissionCreateSerializer, ChildProfileListSerializer,
    CustomTokenObtainPairSerializer
)
from .utils import success_response, error_response


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    
    Login with username/email and password
    Returns JWT tokens with user information
    
    Request Body:
    {
        "username": "vasista123",  // Can be username or email
        "password": "yourpassword"
    }
    
    Response:
    {
        "status": true,
        "data": {
            "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user_id": 1,
            "username": "vasista123",
            "email": "vasista@example.com",
            "first_name": "Vasista",
            "last_name": "Rachaputi",
            "full_name": "Vasista Rachaputi",
            "user_type": "nanhe_patrakar",
            "program_info": {
                "parent_id": 5,
                "program_id": 1,
                "program_name": "Nanhe Patrakar 2025",
                "status": "ACTIVE",
                "mobile": "9876543210",
                "city": "Shimla",
                "district": "Shimla"
            },
            "access_token_expiration": "2025-01-10T14:30:00",
            "refresh_token_expiration": "2025-02-09T13:30:00",
            "access_expires_in": 3600,
            "refresh_expires_in": 2592000
        },
        "message": "Login successful"
    }
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            return Response(
                success_response(serializer.validated_data, "Login successful"),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_401_UNAUTHORIZED
            )


class ParentProfileAPIView(APIView):
    """
    GET /api/nanhe-patrakar/parent-profile/
    
    Get logged-in parent profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            serializer = ParentProfileSerializer(parent_profile)
            
            return Response(
                success_response(serializer.data, "Parent profile retrieved"),
                status=status.HTTP_200_OK
            )
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )


class ChildProfileAPIView(APIView):
    """
    GET /api/nanhe-patrakar/child-profiles/
    List all child profiles of logged-in parent
    
    POST /api/nanhe-patrakar/child-profiles/
    Create new child profile
    
    {
        "name": "Child Name",
        "date_of_birth": "2015-05-15",
        "age": 9,
        "gender": "M",
        "school_name": "ABC School",
        "district_id": 1,
        "photo": <file>
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            children = ChildProfile.objects.filter(
                parent=parent_profile
            ).select_related('district').order_by('-created_at')
            
            serializer = ChildProfileSerializer(children, many=True)
            
            return Response(
                success_response(serializer.data, "Child profiles retrieved"),
                status=status.HTTP_200_OK
            )
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
    
    @transaction.atomic
    def post(self, request):
        try:
            parent_profile = request.user.parent_profile
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChildProfileCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            district = District.objects.get(id=serializer.validated_data['district_id'])
            
            child_profile = ChildProfile.objects.create(
                parent=parent_profile,
                name=serializer.validated_data['name'],
                date_of_birth=serializer.validated_data['date_of_birth'],
                age=serializer.validated_data['age'],
                gender=serializer.validated_data.get('gender'),
                school_name=serializer.validated_data.get('school_name'),
                district=district,
                photo=serializer.validated_data.get('photo')
            )
            
            response_serializer = ChildProfileSerializer(child_profile)
            
            return Response(
                success_response(
                    response_serializer.data,
                    "Child profile created successfully"
                ),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                error_response(f"Failed to create child profile: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChildProfileDetailAPIView(APIView):
    """
    GET /api/nanhe-patrakar/child-profiles/<child_id>/
    Get specific child profile
    
    PUT /api/nanhe-patrakar/child-profiles/<child_id>/
    Update child profile
    
    DELETE /api/nanhe-patrakar/child-profiles/<child_id>/
    Delete child profile
    """
    permission_classes = [IsAuthenticated]
    
    def get_child_profile(self, request, child_id):
        """Helper to get child profile and verify ownership"""
        try:
            parent_profile = request.user.parent_profile
            child_profile = ChildProfile.objects.get(
                id=child_id,
                parent=parent_profile
            )
            return child_profile
        except (ParentProfile.DoesNotExist, ChildProfile.DoesNotExist):
            return None
    
    def get(self, request, child_id):
        child_profile = self.get_child_profile(request, child_id)
        
        if not child_profile:
            return Response(
                error_response("Child profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChildProfileSerializer(child_profile)
        
        return Response(
            success_response(serializer.data, "Child profile retrieved"),
            status=status.HTTP_200_OK
        )
    
    @transaction.atomic
    def put(self, request, child_id):
        child_profile = self.get_child_profile(request, child_id)
        
        if not child_profile:
            return Response(
                error_response("Child profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ChildProfileCreateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(
                error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Update fields
            for field, value in serializer.validated_data.items():
                if field == 'district_id':
                    district = District.objects.get(id=value)
                    child_profile.district = district
                else:
                    setattr(child_profile, field, value)
            
            child_profile.save()
            
            response_serializer = ChildProfileSerializer(child_profile)
            
            return Response(
                success_response(
                    response_serializer.data,
                    "Child profile updated successfully"
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f"Failed to update child profile: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def delete(self, request, child_id):
        child_profile = self.get_child_profile(request, child_id)
        
        if not child_profile:
            return Response(
                error_response("Child profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            child_name = child_profile.name
            child_profile.delete()
            
            return Response(
                success_response(
                    {"child_id": child_id, "name": child_name},
                    "Child profile deleted successfully"
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f"Failed to delete child profile: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChildSubmissionsAPIView(APIView):
    """
    GET /api/nanhe-patrakar/child-profiles/<child_id>/submissions/
    
    Get all submissions of a specific child
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, child_id):
        try:
            parent_profile = request.user.parent_profile
            
            # Verify child belongs to parent
            child_profile = ChildProfile.objects.get(
                id=child_id,
                parent=parent_profile
            )
            
            submissions = Submission.objects.filter(
                child=child_profile
            ).select_related('topic').order_by('-created_at')
            
            serializer = SubmissionSerializer(submissions, many=True)
            
            return Response(
                success_response(
                    {
                        "child_id": child_id,
                        "child_name": child_profile.name,
                        "total_submissions": submissions.count(),
                        "submissions": serializer.data
                    },
                    "Submissions retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        except ChildProfile.DoesNotExist:
            return Response(
                error_response("Child profile not found or unauthorized"),
                status=status.HTTP_404_NOT_FOUND
            )


class SubmissionCreateAPIView(APIView):
    """
    POST /api/nanhe-patrakar/submissions/
    
    Create submission with multiple images and videos
    
    Form Data:
    - child_id
    - topic_id (optional)
    - title
    - content_type
    - language
    - content_text (optional)
    - media_description (optional)
    - image_1, image_2, image_3, ... (files)
    - video_1, video_2, video_3, ... (files)
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        try:
            parent_profile = request.user.parent_profile
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SubmissionCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Verify child belongs to parent
            child_profile = ChildProfile.objects.get(
                id=serializer.validated_data['child_id'],
                parent=parent_profile
            )
            
            topic = None
            if serializer.validated_data.get('topic_id'):
                topic = Topic.objects.get(id=serializer.validated_data['topic_id'])
            
            # Create submission
            submission = Submission.objects.create(
                child=child_profile,
                topic=topic,
                title=serializer.validated_data['title'],
                content_type=serializer.validated_data['content_type'],
                language=serializer.validated_data['language'],
                content_text=serializer.validated_data.get('content_text', ''),
                media_description=serializer.validated_data.get('media_description', ''),
                status='SUBMITTED'
            )
            
            # Handle multiple images
            image_order = 0
            for key in sorted(request.FILES.keys()):
                if key.startswith('image_'):
                    image_file = request.FILES[key]
                    SubmissionMedia.objects.create(
                        submission=submission,
                        media_type='IMAGE',
                        file=image_file,
                        file_name=image_file.name,
                        file_size=image_file.size,
                        display_order=image_order
                    )
                    image_order += 1
            
            # Handle multiple videos
            video_order = 0
            for key in sorted(request.FILES.keys()):
                if key.startswith('video_'):
                    video_file = request.FILES[key]
                    SubmissionMedia.objects.create(
                        submission=submission,
                        media_type='VIDEO',
                        file=video_file,
                        file_name=video_file.name,
                        file_size=video_file.size,
                        display_order=video_order
                    )
                    video_order += 1
            
            # Handle audio files
            audio_order = 0
            for key in sorted(request.FILES.keys()):
                if key.startswith('audio_'):
                    audio_file = request.FILES[key]
                    SubmissionMedia.objects.create(
                        submission=submission,
                        media_type='AUDIO',
                        file=audio_file,
                        file_name=audio_file.name,
                        file_size=audio_file.size,
                        display_order=audio_order
                    )
                    audio_order += 1
            
            submission.save()
            
            response_serializer = SubmissionSerializer(submission)
            
            return Response(
                success_response(
                    response_serializer.data,
                    f"Submission created with {image_order} images, {video_order} videos, {audio_order} audios"
                ),
                status=status.HTTP_201_CREATED
            )
        except ChildProfile.DoesNotExist:
            return Response(
                error_response("Child profile not found or unauthorized"),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                error_response(f"Failed to create submission: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            

class ChildProfilesByRecentSubmissionsAPIView(APIView):
    """
    GET /api/nanhe-patrakar/child-profiles/by-recent-submissions/
    
    Get all child profiles ordered by most recent submissions
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            parent_profile = request.user.parent_profile
            
            # Get child profiles with their latest submission date
            children = ChildProfile.objects.filter(
                parent=parent_profile
            ).annotate(
                latest_submission_date=Max('submissions__created_at'),
                submission_count=Count('submissions')
            ).order_by('-latest_submission_date', '-created_at')
            
            serializer = ChildProfileListSerializer(children, many=True)
            
            return Response(
                success_response(
                    {
                        "total_children": children.count(),
                        "children": serializer.data
                    },
                    "Child profiles retrieved successfully"
                ),
                status=status.HTTP_200_OK
            )
        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
            