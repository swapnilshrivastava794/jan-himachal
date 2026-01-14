# nanhe_patrakar/api/urls.py

from django.urls import path
from .views import (
    LoginView,
    ParentProfileAPIView, UserProfileUpdateAPIView,
    ChildProfileAPIView, ParentProfileUpdateAPIView,
    ChildProfileDetailAPIView, PublicChildProfilesListAPIView,
    ChildSubmissionsAPIView, FakePaymentSuccessAPIView,
    SubmissionCreateAPIView, EnrollToNanhePatrakarAPIView,
    ChildProfilesByRecentSubmissionsAPIView, 
    DistrictListAPIView, ParentRegistrationAPIView, TopicListAPIView, SubmissionListAPIView,
    SubmissionDetailAPIView, SubmissionStatsAPIView, CertificateCheckAPIView
)

urlpatterns = [
    # Authentication
    path('login/', LoginView.as_view(), name='api_login'),
    
    # User 
    path('user/update/', UserProfileUpdateAPIView.as_view(), name='user_update'),
    
    # Topic
    path('topics/', TopicListAPIView.as_view(), name='topic-list'),
    
    
    # Parent Profile
    path('register/', ParentRegistrationAPIView.as_view(), name='parent-register'),
    path('enrollment/', EnrollToNanhePatrakarAPIView.as_view(), name='enrollment'),
    path('parent-profile/', ParentProfileAPIView.as_view(), name='api_parent_profile'),
    path('update/parent-profile/', ParentProfileUpdateAPIView.as_view(), name='api_parent_profile'),
    
    # Child Profiles
    path('child-profiles/', ChildProfileAPIView.as_view(), name='api_child_profiles'),
    path('child-profiles/list/', PublicChildProfilesListAPIView.as_view(), name='api_child_profiles_list'),
    path('child-profiles/<int:child_id>/', ChildProfileDetailAPIView.as_view(), name='api_child_profile_detail'),
    path('child-profiles/by-recent-submissions/', ChildProfilesByRecentSubmissionsAPIView.as_view(), name='api_children_by_submissions'),
    path('certificate-check/<int:child_id>/', CertificateCheckAPIView.as_view(), name='certificate_check'),
    
    # Submissions
    path('child-profiles/<int:child_id>/submissions/', ChildSubmissionsAPIView.as_view(), name='api_child_submissions'),
    path('submission/', SubmissionCreateAPIView.as_view(), name='api_submission_create'),
    path('submissions/', SubmissionListAPIView.as_view(), name='submission-list'),
    path('submissions/<int:pk>/', SubmissionDetailAPIView.as_view(), name='submission-detail'),
    path('submissions/stats/', SubmissionStatsAPIView.as_view(), name='submission-stats'),
    
    path('districts/', DistrictListAPIView.as_view(), name='district-list'),
    
    #Fake Payment API 
    path('fake/payment/', FakePaymentSuccessAPIView.as_view()),

]