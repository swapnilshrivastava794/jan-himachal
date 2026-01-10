from rest_framework.generics import ListAPIView , RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from post_management.models import category , NewsPost , VideoNews, AppUser
from .serializers import CategorySerializer , NewsListSerializer, SearchNewsSerializer, SearchVideoSerializer , VideoListSerializer, AppUserSignupSerializer, AppUserLoginSerializer, AppUserUpdateSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from nanhe_patrakar.api.utils import success_response, error_response

from django.contrib.auth.models import User


class SearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50


class CategoryListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def get_queryset(self):
        return category.objects.filter(
            cat_status='active'
        ).order_by('order')

class NewsListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = NewsListSerializer

     # 🔹 Pagination defined INSIDE view
    class Pagination(PageNumberPagination):
        page_size = 10                 # default records
        page_size_query_param = 'limit'
        max_page_size = 50

    pagination_class = Pagination

    def get_queryset(self):
        qs = NewsPost.objects.filter(
            status='active',
            is_active=True
        ).order_by('-post_date')

        # 🔹 Sub-category filter (MANDATORY when sent)
        subcat_id = self.request.GET.get('subcategory_id')
        if subcat_id:
            qs = qs.filter(post_cat_id=subcat_id)

        # 🔹 Status-based filters
        if self.request.GET.get('breaking') == '1':
            qs = qs.filter(BreakingNews=True)

        if self.request.GET.get('trending') == '1':
            qs = qs.filter(trending=True)

        if self.request.GET.get('headlines') == '1':
            qs = qs.filter(Head_Lines=True)

        if self.request.GET.get('articles') == '1':
            qs = qs.filter(articles=True)

        # 🔹 Fallback: Show posts with post_status=1 if the filtered list is empty
        if not qs.exists():
            fallback_qs = NewsPost.objects.filter(status='active', is_active=True, post_status=1)
            if not fallback_qs.exists():
                # Ultimate Fallback: Just show latest active posts if no status=1 exists
                return NewsPost.objects.filter(status='active', is_active=True).order_by('-post_date')
            return fallback_qs.order_by('-post_date')

        return qs


class NewsDetailAPI(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = NewsListSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return NewsPost.objects.filter(
            status='active',
            is_active=True
        )

class VideoListAPI(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = VideoListSerializer

     # 🔹 Pagination defined INSIDE view
    class Pagination(PageNumberPagination):
        page_size = 10                 # default records
        page_size_query_param = 'limit'
        max_page_size = 50

    pagination_class = Pagination

    def get_queryset(self):
        qs = VideoNews.objects.filter(
            is_active='active'
        ).order_by('-video_date')

        # 🔹 Sub-category filter
        subcat_id = self.request.GET.get('subcategory_id')
        if subcat_id:
            qs = qs.filter(News_Category_id=subcat_id)

        # 🔹 Video type filter (video / reel)
        video_type = self.request.GET.get('video_type')
        if video_type in ['video', 'reel']:
            qs = qs.filter(video_type=video_type)

        # 🔹 Status filters
        if self.request.GET.get('breaking') == '1':
            qs = qs.filter(BreakingNews=True)

        if self.request.GET.get('trending') == '1':
            qs = qs.filter(trending=True)

        if self.request.GET.get('headlines') == '1':
            qs = qs.filter(Head_Lines=True)

        if self.request.GET.get('articles') == '1':
            qs = qs.filter(articles=True)

        # 🔹 Fallback: Show videos with counter=1 if the filtered list is empty
        if not qs.exists():
            fallback_qs = VideoNews.objects.filter(is_active='active', counter=1)
            if not fallback_qs.exists():
                # Ultimate Fallback: Just show latest active videos if no counter=1 exists
                return VideoNews.objects.filter(is_active='active').order_by('-video_date')
            return fallback_qs.order_by('-video_date')

        return qs


class VideoDetailAPI(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = VideoListSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return VideoNews.objects.filter(is_active='active')
    

class GlobalSearchAPI(APIView):
    permission_classes = [AllowAny]
    pagination_class = SearchPagination

    def get(self, request):
        query = request.GET.get('q', '').strip()

        if not query:
            return Response({
                "count": 0,
                "results": []
            })

        # 🔹 NEWS SEARCH
        news_qs = NewsPost.objects.select_related(
            'post_cat',
            'post_cat__sub_cat'
        ).filter(
            Q(post_title__icontains=query) |
            Q(post_short_des__icontains=query) |
            Q(slug__icontains=query) |
            Q(post_cat__subcat_name__icontains=query) |
            Q(post_cat__sub_cat__cat_name__icontains=query),
            status='active',
            is_active=True
        ).order_by('-post_date')

        # 🔹 VIDEO SEARCH
        video_qs = VideoNews.objects.select_related(
            'News_Category',
            'News_Category__sub_cat'
        ).filter(
            Q(video_title__icontains=query) |
            Q(video_short_des__icontains=query) |
            Q(slug__icontains=query) |
            Q(News_Category__subcat_name__icontains=query) |
            Q(News_Category__sub_cat__cat_name__icontains=query),
            is_active='active'
        ).order_by('-video_date')

        # 🔹 Serialize
        news_data = SearchNewsSerializer(
            news_qs, many=True, context={'request': request}
        ).data

        video_data = SearchVideoSerializer(
            video_qs, many=True, context={'request': request}
        ).data

        # 🔹 Combine results
        combined = (
            [{"type": "news", **item} for item in news_data] +
            [{"type": "video", **item} for item in video_data]
        )

        # 🔹 Pagination manually
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(combined, request)
        return paginator.get_paginated_response(page)

class AppSignupAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = AppUserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens manually
            refresh = RefreshToken()
            refresh['user_id'] = user.id
            refresh['email'] = user.email
            
            return Response({
                "status": "success", 
                "message": "Account created successfully!", 
                "data": serializer.data,
                "tokens": {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AppLoginAPI(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = AppUserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = AppUser.objects.get(email=email)
            except AppUser.DoesNotExist:
                return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            if check_password(password, user.password):
                # Generate JWT tokens manually
                refresh = RefreshToken()
                refresh['user_id'] = user.id
                refresh['email'] = user.email

                return Response({
                    "status": "success",
                    "message": "Login successful",
                    "tokens": {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    "user": {
                        "id": user.id,
                        "name": user.name,
                        "email": user.email,
                        "phone": user.phone,
                        "city": user.city,
                        "country": user.country
                    }
                }, status=status.HTTP_200_OK)
            else:
                return Response({"status": "error", "message": "Invalid password"}, status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AppProfileUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user_id):
        # Helper method for consistent error handling
        try:
            return AppUser.objects.get(id=user_id)
        except AppUser.DoesNotExist:
            return None

    def post(self, request):
        # We'll get user_id from the token (request.user comes from JWTAuthentication)
        # Note: SimpleJWT by default sets request.user to a Django User object.
        # Since we use a custom AppUser and manual token generation, 
        # request.user might be an internal SimpleJWT user object or a dict from the claim.
        # We should rely on the 'user_id' we put in the token claim.
        
        try:
            # When using manual token generation with SimpleJWT, request.user usually resolves
            # based on USER_ID_FIELD. Since AppUser is not the AUTH_USER_MODEL,
            # we need to be careful.
            # The safest way here since we manually forged tokens:
            token_user_id = request.auth.payload.get('user_id')
            user = self.get_object(token_user_id)
        except Exception:
            # Fallback/Debug
            return Response({"status": "error", "message": "Invalid auth token"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user:
             return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppUserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": "success",
                "message": "Profile updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationAPIView(APIView):
    """
    POST /api/nanhe-patrakar/register/
    
    Register a new user with username and password
    
    {
        "username": "john_doe",
        "password": "password123"
    }
    """
    
    @transaction.atomic
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                error_response("Username and password are required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate username length
        if len(username) < 3:
            return Response(
                error_response("Username must be at least 3 characters long"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate password length
        if len(password) < 6:
            return Response(
                error_response("Password must be at least 6 characters long"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response(
                error_response("Username already exists"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create user
            user = User.objects.create_user(
                username=username,
                password=password
            )
            
            return Response(
                success_response(
                    {
                        "user_id": user.id,
                        "username": user.username
                    },
                    "User registered successfully"
                ),
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                error_response(f"Failed to register user: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        