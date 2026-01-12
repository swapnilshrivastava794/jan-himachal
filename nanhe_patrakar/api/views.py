# nanhe_patrakar/api/views.py

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max
from django.db.models import Q
from django.utils import timezone

from datetime import datetime

from nanhe_patrakar.models import (
    ParentProfile, ChildProfile, Submission, 
    District, Topic, SubmissionMedia, Program, 
    ParticipationOrder
)
from .serializers import (
    ParentProfileSerializer, ChildProfileSerializer, ParentProfileUpdateSerializer,
    ChildProfileCreateSerializer, SubmissionSerializer, UserUpdateSerializer,
    SubmissionCreateSerializer, ChildProfileListSerializer, ParentFallbackUserSerializer,
    CustomTokenObtainPairSerializer, DistrictSerializer, ParentRegistrationSerializer, TopicListSerializer,
    TopicSerializer, SubmissionDetailSerializer, SubmissionListSerializer, SubmissionMediaSerializer
)
from .utils import success_response, error_response, build_nanhe_patrakar_program_info
from .pagination import DynamicPageNumberPagination

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
    
    Get logged-in parent profile.
    If parent profile does not exist, return user details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            parent_profile = getattr(request.user, 'parent_profile', None)

            # CASE 1: Parent profile exists
            if parent_profile:
                serializer = ParentProfileSerializer(parent_profile)
                return Response(
                    success_response(
                        {
                            "profile_exists": True,
                            "parent_profile": serializer.data
                        },
                        "Parent profile retrieved"
                    ),
                    status=status.HTTP_200_OK
                )

            # CASE 2: Parent profile does not exist → fallback to user info
            user_serializer = ParentFallbackUserSerializer(request.user)
            return Response(
                success_response(
                    {
                        "profile_exists": False,
                        "user": user_serializer.data
                    },
                    "Parent profile not created yet"
                ),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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

            queryset = ChildProfile.objects.filter(
                parent=parent_profile
            ).select_related('district').order_by('-created_at')

            paginator = DynamicPageNumberPagination()
            paginated_qs = paginator.paginate_queryset(queryset, request)

            serializer = ChildProfileSerializer(paginated_qs, many=True)

            return paginator.get_paginated_response(serializer.data)

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
                photo=serializer.validated_data.get('photo'),
                id_proof=serializer.validated_data.get('id_proof'),
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
    permission_classes = [AllowAny]
    
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
        child_profile = ChildProfile.objects.filter(
                id=child_id).first()
        
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
    permission_classes = [AllowAny]
    
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

    Get child profiles ordered by most recent submissions (Paginated)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            parent_profile = request.user.parent_profile

            queryset = ChildProfile.objects.filter(
                parent=parent_profile
            ).annotate(
                latest_submission_date=Max('submissions__created_at'),
                submission_count=Count('submissions')
            ).order_by('-latest_submission_date', '-created_at')

            paginator = DynamicPageNumberPagination()
            paginated_qs = paginator.paginate_queryset(queryset, request)

            serializer = ChildProfileListSerializer(paginated_qs, many=True)

            return paginator.get_paginated_response(serializer.data)

        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
            

class DistrictListAPIView(ListAPIView):
    """
    GET /api/districts/
    
    Get list of districts with pagination and search
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 10, max: 100)
    - search: Search by name or name_hindi
    - is_active: Filter by active status (true/false)
    - ordering: Sort by field (name, -name, created_at, -created_at)
    
    Examples:
    - /api/districts/
    - /api/districts/?page=2&page_size=20
    - /api/districts/?search=shimla
    - /api/districts/?is_active=true
    - /api/districts/?ordering=-name
    - /api/districts/?page=1&page_size=50&search=shimla&is_active=true
    
    Response:
    {
        "status": true,
        "message": "Districts retrieved successfully",
        "data": {
            "count": 12,
            "total_pages": 2,
            "current_page": 1,
            "page_size": 10,
            "next": "http://localhost:8000/api/districts/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "name": "Shimla",
                    "name_hindi": "शिमला",
                    "is_active": true,
                    "created_at": "2025-01-09T10:30:00Z"
                },
                ...
            ]
        }
    }
    """
    serializer_class = DistrictSerializer
    pagination_class = DynamicPageNumberPagination
    
    def get_queryset(self):
        """
        Get filtered and sorted queryset based on query parameters
        """
        queryset = District.objects.all()
        
        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(name_hindi__icontains=search)
            )
        
        # Active status filter
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            if is_active.lower() in ['true', '1', 'yes']:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(is_active=False)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', 'name')
        valid_ordering_fields = ['name', '-name', 'name_hindi', '-name_hindi', 
                                 'created_at', '-created_at', 'id', '-id']
        if ordering in valid_ordering_fields:
            queryset = queryset.order_by(ordering)
        
        return queryset


class ParentRegistrationAPIView(APIView):
    """
    POST /api/nanhe-patrakar/parent/register/
    
    Register new parent for Nanhe Patrakar program
    Works for both new users and existing users
    
    For New Users (provide all fields):
    {
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe123",
        "mobile": "9876543210",
        "email": "john@example.com",
        "password": "password123",
        "city": "Shimla",
        "district_id": 1,
        "terms_accepted": true
    }
    
    For Existing Users (must be authenticated, provide only):
    {
        "mobile": "9876543210",
        "city": "Shimla",
        "district_id": 1,
        "terms_accepted": true
    }
    """
    permission_classes = [AllowAny]  # Allow both authenticated and non-authenticated
    
    @transaction.atomic
    def post(self, request):
        # Check if active program exists
        program = Program.get_active_program()
        if not program:
            return Response(
                error_response('पंजीकरण बंद है / Registration is closed'),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user is authenticated
        is_authenticated = request.user.is_authenticated
        
        # Validate input data
        serializer = ParentRegistrationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            validated_data = serializer.validated_data
            
            # Get district
            district = District.objects.get(id=validated_data['district_id'])
            
            # Check if mobile already registered in program
            if ParentProfile.objects.filter(mobile=validated_data['mobile']).exists():
                return Response(
                    error_response('यह मोबाइल नंबर पहले से पंजीकृत है / This mobile number is already registered in the program'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # ============================================
            # Handle Existing User (Authenticated)
            # ============================================
            if is_authenticated:
                user = request.user
                
                # Create parent profile for existing user
                parent_profile = ParentProfile.objects.create(
                    user=user,
                    program=program,
                    mobile=validated_data['mobile'],
                    city=validated_data['city'],
                    district=district,
                    status='PAYMENT_PENDING',
                    terms_accepted=validated_data['terms_accepted'],
                    terms_accepted_at=timezone.now() if validated_data['terms_accepted'] else None
                )
                
                # Create pending order
                order = ParticipationOrder.objects.create(
                    parent=parent_profile,
                    program=program,
                    amount=program.price,
                    payment_status='PENDING'
                )
                
                # Generate new JWT tokens with updated claims
                refresh = RefreshToken.for_user(user)
                refresh['user_type'] = 'nanhe_patrakar'
                refresh['parent_id'] = parent_profile.id
                
                message = 'मौजूदा उपयोगकर्ता के लिए पंजीकरण सफल! / Registration successful for existing user!'
            
            # ============================================
            # Handle New User (Not Authenticated)
            # ============================================
            else:
                # Validate required fields for new user
                if not all([
                    validated_data.get('username'),
                    validated_data.get('password'),
                    validated_data.get('email'),
                    validated_data.get('first_name'),
                    validated_data.get('last_name')
                ]):
                    return Response(
                        error_response('नए उपयोगकर्ता के लिए सभी फ़ील्ड आवश्यक हैं / All fields required for new user: username, password, email, first_name, last_name'),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if username already exists
                if User.objects.filter(username=validated_data['username']).exists():
                    return Response(
                        error_response('उपयोगकर्ता नाम पहले से मौजूद है / Username already exists'),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if email already exists
                if User.objects.filter(email=validated_data['email']).exists():
                    return Response(
                        error_response('ईमेल पहले से पंजीकृत है / Email already registered'),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create new user account
                user = User.objects.create_user(
                    username=validated_data['username'],
                    email=validated_data['email'],
                    first_name=validated_data['first_name'],
                    last_name=validated_data['last_name'],
                    password=validated_data['password']
                )
                
                # Create parent profile
                parent_profile = ParentProfile.objects.create(
                    user=user,
                    program=program,
                    mobile=validated_data['mobile'],
                    city=validated_data['city'],
                    district=district,
                    status='PAYMENT_PENDING',
                    terms_accepted=validated_data['terms_accepted'],
                    terms_accepted_at=timezone.now() if validated_data['terms_accepted'] else None
                )
                
                # Create pending order
                order = ParticipationOrder.objects.create(
                    parent=parent_profile,
                    program=program,
                    amount=program.price,
                    payment_status='PENDING'
                )
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                refresh['user_type'] = 'nanhe_patrakar'
                refresh['parent_id'] = parent_profile.id
                
                message = 'पंजीकरण सफल! अब भुगतान के साथ आगे बढ़ें / Registration successful! Please proceed with payment'
            
            # ============================================
            # Build Common Response
            # ============================================
            
            # Calculate token expiration
            access_token_expiration = datetime.fromtimestamp(refresh.access_token['exp'])
            refresh_token_expiration = datetime.fromtimestamp(refresh['exp'])
            
            response_data = {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': user.get_full_name()
                },
                'parent_profile': {
                    'id': parent_profile.id,
                    'program_id': program.id,
                    'program_name': program.name,
                    'mobile': parent_profile.mobile,
                    'city': parent_profile.city,
                    'district_id': district.id,
                    'district_name': district.name,
                    'status': parent_profile.status,
                    'created_at': parent_profile.created_at.isoformat()
                },
                'order': {
                    'id': order.id,
                    'order_id': order.order_id,
                    'amount': float(order.amount),
                    'payment_status': order.payment_status,
                    'created_at': order.created_at.isoformat()
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'access_token_expiration': access_token_expiration.isoformat(),
                    'refresh_token_expiration': refresh_token_expiration.isoformat(),
                    'access_expires_in': int(refresh.access_token['exp'] - datetime.now().timestamp()),
                    'refresh_expires_in': int(refresh['exp'] - datetime.now().timestamp()),
                }
            }
            
            return Response(
                success_response(response_data, message),
                status=status.HTTP_201_CREATED
            )
            
        except District.DoesNotExist:
            return Response(
                error_response('जिला नहीं मिला / District not found'),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Rollback: If user was created but profile failed, delete the user
            if not is_authenticated and 'user' in locals():
                try:
                    user.delete()
                except:
                    pass
            
            return Response(
                error_response(f'पंजीकरण में त्रुटि / Registration error: {str(e)}'),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
      
      
class EnrollToNanhePatrakarAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        data = request.data
        files = request.FILES

        if hasattr(user, 'parent_profile'):
            return Response(
                error_response("User already enrolled"),
                status=status.HTTP_400_BAD_REQUEST
            )

        program = Program.get_active_program()
        if not program:
            return Response(
                error_response("Registration is closed"),
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------- VALIDATIONS ----------

        terms_accepted_raw = str(data.get('terms_accepted', '')).lower()
        terms_accepted = terms_accepted_raw in ['true', '1', 'yes']

        if not terms_accepted:
            return Response(
                error_response("Terms must be accepted"),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            child_age = int(data.get('child_age'))
        except (TypeError, ValueError):
            return Response(
                error_response("Invalid child_age"),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            child_dob = datetime.strptime(
                data.get('child_date_of_birth'),
                "%Y-%m-%d"
            ).date()
        except Exception:
            return Response(
                error_response("child_date_of_birth must be YYYY-MM-DD"),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            parent_district = District.objects.get(id=int(data.get('district_id')))
            child_district = District.objects.get(id=int(data.get('child_district_id')))
        except (District.DoesNotExist, TypeError, ValueError):
            return Response(
                error_response("Invalid district"),
                status=status.HTTP_404_NOT_FOUND
            )

        if ParentProfile.objects.filter(mobile=data.get('mobile')).exists():
            return Response(
                error_response("Mobile already registered"),
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------- OBJECT CREATION ----------

        parent_profile = ParentProfile.objects.create(
            user=user,
            program=program,
            mobile=data.get('mobile'),
            city=data.get('city'),
            district=parent_district,
            status='PAYMENT_PENDING',
            terms_accepted=True,
            terms_accepted_at=timezone.now(),
            id_proof=files.get('parent_id_proof')
        )

        child_profile = ChildProfile.objects.create(
            parent=parent_profile,
            name=data.get('child_name'),
            date_of_birth=child_dob,
            age=child_age,
            gender=data.get('child_gender'),
            school_name=data.get('child_school_name'),
            district=child_district,
            id_proof=files.get('child_id_proof'),
            photo=files.get('child_photo')
        )

        order = ParticipationOrder.objects.create(
            parent=parent_profile,
            program=program,
            amount=program.price,
            payment_status='PENDING'
        )

        # ---------- RESPONSE PAYLOAD ----------

        return Response(
            success_response(
                {
                    "user_id": user.id,
                    "user_type": "nanhe_patrakar",
                    "program_info": build_nanhe_patrakar_program_info(parent_profile)
                },
                "Enrollment successful. Please proceed with payment."
            ),
            status=status.HTTP_201_CREATED
        )



class FakePaymentSuccessAPIView(APIView):
    """
    TEMPORARY API – Fake payment success
    Marks participation order as SUCCESS
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        order_id = request.data.get('order_id')

        # Ensure user is enrolled
        if not hasattr(user, 'parent_profile'):
            return Response(
                error_response("User is not enrolled in the program"),
                status=status.HTTP_400_BAD_REQUEST
            )

        parent_profile = user.parent_profile

        try:
            # If order_id provided, use it
            if order_id:
                order = ParticipationOrder.objects.get(
                    order_id=order_id,
                    parent=parent_profile
                )
            else:
                # Otherwise, pick latest pending order
                order = ParticipationOrder.objects.filter(
                    parent=parent_profile,
                    payment_status='PENDING'
                ).latest('created_at')

            if order.payment_status == 'SUCCESS':
                return Response(
                    error_response("Payment already completed for this order"),
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Mark payment success
            order.payment_status = 'SUCCESS'
            order.payment_method = 'FAKE'
            order.payment_date = timezone.now()
            order.save()

            # Update parent status
            parent_profile.status = 'PAYMENT_COMPLETED'
            parent_profile.save(update_fields=['status', 'updated_at'])

            return Response(
                success_response(
                    {
                        "order_id": order.order_id,
                        "payment_status": order.payment_status,
                        "payment_date": order.payment_date.isoformat(),
                        "invoice_number": order.invoice_number,
                        "parent_status": parent_profile.status
                    },
                    "Fake payment completed successfully"
                ),
                status=status.HTTP_200_OK
            )

        except ParticipationOrder.DoesNotExist:
            return Response(
                error_response("Order not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        

class PublicChildProfilesListAPIView(APIView):
    """
    GET /api/nanhe-patrakar/child-profiles/
    List all child profiles 
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        try:

            queryset = ChildProfile.objects.filter(is_active=True).select_related('district').order_by('-created_at')

            paginator = DynamicPageNumberPagination()
            paginated_qs = paginator.paginate_queryset(queryset, request)

            serializer = ChildProfileSerializer(paginated_qs, many=True)

            return paginator.get_paginated_response(serializer.data)

        except ParentProfile.DoesNotExist:
            return Response(
                error_response("Parent profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
            
            
class ParentProfileUpdateAPIView(APIView):
    """
    PUT /api/nanhe-patrakar/parent-profile/update/

    Update parent profile and related user details.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            parent_profile = getattr(request.user, 'parent_profile', None)

            if not parent_profile:
                return Response(
                    error_response("Parent profile not found"),
                    status=status.HTTP_404_NOT_FOUND
                )

            user = request.user

            user_serializer = UserUpdateSerializer(
                user,
                data=request.data,
                partial=True
            )

            parent_serializer = ParentProfileUpdateSerializer(
                parent_profile,
                data=request.data,
                partial=True
            )

            # Validate both before saving anything
            user_serializer.is_valid(raise_exception=True)
            parent_serializer.is_valid(raise_exception=True)

            with transaction.atomic():
                user_serializer.save()
                parent_serializer.save()

            return Response(
                success_response(
                    {
                        "user": UserUpdateSerializer(user).data,
                        "parent_profile": ParentProfileSerializer(parent_profile).data
                    },
                    "Parent profile updated successfully"
                ),
                status=status.HTTP_200_OK
            )

        except serializers.ValidationError as ve:
            return Response(
                error_response(ve.detail),
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileUpdateAPIView(APIView):
    """
    PUT /api/nanhe-patrakar/user-profile/update/

    Update logged-in user's basic details.
    """
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            user = request.user

            serializer = UserUpdateSerializer(
                user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response(
                success_response(
                    serializer.data,
                    "User profile updated successfully"
                ),
                status=status.HTTP_200_OK
            )

        except serializers.ValidationError as ve:
            return Response(
                error_response(ve.detail),
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                error_response(str(e)),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TopicListAPIView(ListAPIView):
    """
    GET /api/nanhe-patrakar/topics/
    
    Get list of all topics
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - is_active: Filter by active status (true/false)
    - age_group: Filter by age group (A, B, C)
    - search: Search in title
    - ordering: Sort by field (title, -title, display_order, -display_order, created_at, -created_at)
    
    Examples:
    - /api/nanhe-patrakar/topics/
    - /api/nanhe-patrakar/topics/?is_active=true
    - /api/nanhe-patrakar/topics/?age_group=A
    - /api/nanhe-patrakar/topics/?search=environment
    - /api/nanhe-patrakar/topics/?ordering=display_order
    - /api/nanhe-patrakar/topics/?page=2&page_size=20
    
    Response:
    {
        "status": true,
        "message": "Topics retrieved successfully",
        "data": {
            "count": 15,
            "total_pages": 2,
            "current_page": 1,
            "page_size": 10,
            "next": "...",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "title": "Environment Day",
                    "title_hindi": "पर्यावरण दिवस",
                    "age_groups": "A,B,C",
                    "age_groups_list": ["A", "B", "C"],
                    "is_active": true,
                    "display_order": 1,
                    "created_at": "2025-01-09T10:30:00Z"
                }
            ]
        }
    }
    """
    permission_classes = [AllowAny]
    serializer_class = TopicListSerializer
    pagination_class = DynamicPageNumberPagination
    
    def get_queryset(self):
        """Get filtered topics"""
        queryset = Topic.objects.all()
        
        # Active filter
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            if is_active.lower() in ['true', '1', 'yes']:
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ['false', '0', 'no']:
                queryset = queryset.filter(is_active=False)
        
        # Age group filter
        age_group = self.request.query_params.get('age_group', None)
        if age_group:
            queryset = queryset.filter(age_groups__icontains=age_group.upper())
        
        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(title_hindi__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get('ordering', 'display_order')
        valid_ordering_fields = [
            'title', '-title', 'display_order', '-display_order',
            'created_at', '-created_at', 'id', '-id'
        ]
        if ordering in valid_ordering_fields:
            queryset = queryset.order_by(ordering)
        
        return queryset


class SubmissionListAPIView(ListAPIView):
    """
    GET /api/nanhe-patrakar/submissions/
    
    Public API - Get list of all submissions with filters
    No authentication required
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 10, max: 100)
    - child_id: Filter by child ID
    - topic_id: Filter by topic ID
    - status: Filter by status (DRAFT, SUBMITTED, APPROVED, REJECTED, PUBLISHED, etc.)
    - content_type: Filter by content type (ARTICLE, POEM, EXPERIENCE, SPEECH)
    - language: Filter by language (HINDI, ENGLISH, LOCAL)
    - age_group: Filter by child's age group (A, B, C)
    - search: Search in title or content
    - ordering: Sort by field (created_at, -created_at, updated_at, -updated_at)
    
    Examples:
    - /api/nanhe-patrakar/submissions/
    - /api/nanhe-patrakar/submissions/?child_id=5
    - /api/nanhe-patrakar/submissions/?topic_id=3
    - /api/nanhe-patrakar/submissions/?child_id=5&topic_id=3
    - /api/nanhe-patrakar/submissions/?status=PUBLISHED
    - /api/nanhe-patrakar/submissions/?content_type=ARTICLE
    - /api/nanhe-patrakar/submissions/?language=HINDI
    - /api/nanhe-patrakar/submissions/?age_group=B
    - /api/nanhe-patrakar/submissions/?search=environment
    - /api/nanhe-patrakar/submissions/?page=2&page_size=20
    
    Response:
    {
        "status": true,
        "message": "Submissions retrieved successfully",
        "data": {
            "count": 50,
            "total_pages": 5,
            "current_page": 1,
            "page_size": 10,
            "next": "...",
            "previous": null,
            "results": [...]
        }
    }
    """
    permission_classes = [AllowAny]
    serializer_class = SubmissionListSerializer
    pagination_class = DynamicPageNumberPagination
    
    def get_queryset(self):
        """Get filtered submissions - public access"""
        # Base queryset - all submissions
        queryset = Submission.objects.all().select_related(
            'child',
            'topic',
            'child__district'
        ).prefetch_related('media_files')
        
        # Filter by child_id
        child_id = self.request.query_params.get('child_id', None)
        if child_id:
            queryset = queryset.filter(child_id=child_id)
        
        # Filter by topic_id
        topic_id = self.request.query_params.get('topic_id', None)
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            valid_statuses = [
                'DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'REVISION_REQUESTED',
                'RESUBMITTED', 'APPROVED', 'PUBLISHED', 'REJECTED', 'CERTIFICATE_ISSUED'
            ]
            if status_filter.upper() in valid_statuses:
                queryset = queryset.filter(status=status_filter.upper())
        
        # Filter by content_type
        content_type = self.request.query_params.get('content_type', None)
        if content_type:
            valid_types = ['ARTICLE', 'POEM', 'EXPERIENCE', 'SPEECH']
            if content_type.upper() in valid_types:
                queryset = queryset.filter(content_type=content_type.upper())
        
        # Filter by language
        language = self.request.query_params.get('language', None)
        if language:
            valid_languages = ['HINDI', 'ENGLISH', 'LOCAL']
            if language.upper() in valid_languages:
                queryset = queryset.filter(language=language.upper())
        
        # Filter by age_group
        age_group = self.request.query_params.get('age_group', None)
        if age_group:
            queryset = queryset.filter(child__age_group=age_group.upper())
        
        # Search filter
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content_text__icontains=search) |
                Q(media_description__icontains=search) |
                Q(child__name__icontains=search) |
                Q(topic__title__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        valid_ordering_fields = [
            'created_at', '-created_at', 'updated_at', '-updated_at',
            'title', '-title', 'status', '-status', 'published_at', '-published_at'
        ]
        if ordering in valid_ordering_fields:
            queryset = queryset.order_by(ordering)
        
        return queryset


class SubmissionDetailAPIView(APIView):
    """
    GET /api/nanhe-patrakar/submissions/<id>/
    
    Public API - Get detailed submission information
    No authentication required
    
    Response:
    {
        "status": true,
        "message": "Submission retrieved successfully",
        "data": {
            "id": 1,
            "submission_id": "SUB-20250109-001",
            "child": 5,
            "child_details": {
                "id": 5,
                "name": "Rahul Kumar",
                "age": 10,
                "age_group": "B",
                "school": "ABC School",
                "district": "Shimla"
            },
            "topic": 3,
            "topic_details": {
                "id": 3,
                "title": "Environment Day",
                "title_hindi": "पर्यावरण दिवस",
                "description": "..."
            },
            "title": "My Environment Story",
            "content_type": "TEXT",
            "content_type_display": "Text",
            "language": "HINDI",
            "language_display": "Hindi",
            "content_text": "...",
            "status": "PUBLISHED",
            "status_display": "Published",
            "media_files": [
                {
                    "id": 1,
                    "media_type": "IMAGE",
                    "file": "/media/submissions/...",
                    "file_name": "photo.jpg",
                    "display_order": 0
                }
            ],
            "parent_info": {
                "id": 10,
                "name": "John Doe",
                "mobile": "9876543210",
                "city": "Shimla"
            },
            "created_at": "2025-01-09T10:30:00Z",
            "updated_at": "2025-01-09T14:30:00Z"
        }
    }
    """
    permission_classes = [AllowAny]
    
    def get(self, request, pk):
        try:
            # Get submission - public access
            submission = Submission.objects.select_related(
                'child',
                'topic',
                'child__district',
                'child__parent__user'
            ).prefetch_related('media_files').get(id=pk)
            
            serializer = SubmissionDetailSerializer(submission)
            
            return Response(
                success_response(
                    serializer.data,
                    'Submission retrieved successfully'
                ),
                status=status.HTTP_200_OK
            )
            
        except Submission.DoesNotExist:
            return Response(
                error_response("Submission not found"),
                status=status.HTTP_404_NOT_FOUND
            )


class SubmissionStatsAPIView(APIView):
    """
    GET /api/nanhe-patrakar/submissions/stats/
    
    Public API - Get submission statistics
    No authentication required
    
    Query Parameters:
    - child_id: Get stats for specific child (optional)
    - topic_id: Get stats for specific topic (optional)
    - age_group: Get stats for specific age group (optional)
    
    Response:
    {
        "status": true,
        "message": "Statistics retrieved successfully",
        "data": {
            "total_submissions": 25,
            "by_status": {
                "DRAFT": 3,
                "SUBMITTED": 5,
                "APPROVED": 10,
                "REJECTED": 2,
                "PUBLISHED": 5
            },
            "by_content_type": {
                "ARTICLE": 15,
                "POEM": 5,
                "EXPERIENCE": 3,
                "SPEECH": 2
            },
            "by_language": {
                "HINDI": 18,
                "ENGLISH": 5,
                "LOCAL": 2
            },
            "by_age_group": {
                "A": 8,
                "B": 10,
                "C": 7
            },
            "by_child": [
                {
                    "child_id": 5,
                    "child_name": "Rahul Kumar",
                    "submission_count": 15
                }
            ],
            "by_topic": [
                {
                    "topic_id": 3,
                    "topic_title": "Environment Day",
                    "submission_count": 8
                }
            ]
        }
    }
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Base queryset - all submissions
        queryset = Submission.objects.all()
        
        # Filter by child if specified
        child_id = request.query_params.get('child_id', None)
        if child_id:
            queryset = queryset.filter(child_id=child_id)
        
        # Filter by topic if specified
        topic_id = request.query_params.get('topic_id', None)
        if topic_id:
            queryset = queryset.filter(topic_id=topic_id)
        
        # Filter by age_group if specified
        age_group = request.query_params.get('age_group', None)
        if age_group:
            queryset = queryset.filter(child__age_group=age_group.upper())
        
        # Total submissions
        total = queryset.count()
        
        # By status
        by_status = {}
        for status_choice in ['DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'REVISION_REQUESTED', 
                             'RESUBMITTED', 'APPROVED', 'PUBLISHED', 'REJECTED', 'CERTIFICATE_ISSUED']:
            count = queryset.filter(status=status_choice).count()
            if count > 0:
                by_status[status_choice] = count
        
        # By content type
        by_content_type = {}
        for content_type in ['ARTICLE', 'POEM', 'EXPERIENCE', 'SPEECH']:
            count = queryset.filter(content_type=content_type).count()
            if count > 0:
                by_content_type[content_type] = count
        
        # By language
        by_language = {}
        for language in ['HINDI', 'ENGLISH', 'LOCAL']:
            count = queryset.filter(language=language).count()
            if count > 0:
                by_language[language] = count
        
        # By age group
        by_age_group = {}
        for age_grp in ['A', 'B', 'C']:
            count = queryset.filter(child__age_group=age_grp).count()
            if count > 0:
                by_age_group[age_grp] = count
        
        # By child
        by_child = queryset.values(
            'child__id',
            'child__name'
        ).annotate(
            submission_count=Count('id')
        ).order_by('-submission_count')[:10]  # Top 10 children
        
        by_child_data = [
            {
                'child_id': item['child__id'],
                'child_name': item['child__name'],
                'submission_count': item['submission_count']
            }
            for item in by_child
        ]
        
        # By topic
        by_topic = queryset.filter(
            topic__isnull=False
        ).values(
            'topic__id',
            'topic__title'
        ).annotate(
            submission_count=Count('id')
        ).order_by('-submission_count')[:10]  # Top 10 topics
        
        by_topic_data = [
            {
                'topic_id': item['topic__id'],
                'topic_title': item['topic__title'],
                'submission_count': item['submission_count']
            }
            for item in by_topic
        ]
        
        stats = {
            'total_submissions': total,
            'by_status': by_status,
            'by_content_type': by_content_type,
            'by_language': by_language,
            'by_age_group': by_age_group,
            'by_child': by_child_data,
            'by_topic': by_topic_data
        }
        
        return Response(
            success_response(stats, 'Statistics retrieved successfully'),
            status=status.HTTP_200_OK
        )