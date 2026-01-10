# nanhe_patrakar/api/urls.py

from django.urls import path
from .views import (
    LoginView,
    ParentProfileAPIView,
    ChildProfileAPIView,
    ChildProfileDetailAPIView,
    ChildSubmissionsAPIView,
    SubmissionCreateAPIView, EnrollToNanhePatrakarAPIView,
    ChildProfilesByRecentSubmissionsAPIView, 
    DistrictListAPIView, ParentRegistrationAPIView
)

urlpatterns = [
    # Authentication
    path('login/', LoginView.as_view(), name='api_login'),
    
    # Parent Profile
    path('register/', ParentRegistrationAPIView.as_view(), name='parent-register'),
    path('enrollment/', EnrollToNanhePatrakarAPIView.as_view(), name='enrollment'),
    path('parent-profile/', ParentProfileAPIView.as_view(), name='api_parent_profile'),
    
    # Child Profiles
    path('child-profiles/', ChildProfileAPIView.as_view(), name='api_child_profiles'),
    path('child-profiles/<int:child_id>/', ChildProfileDetailAPIView.as_view(), name='api_child_profile_detail'),
    path('child-profiles/by-recent-submissions/', ChildProfilesByRecentSubmissionsAPIView.as_view(), name='api_children_by_submissions'),
    
    # Submissions
    path('child-profiles/<int:child_id>/submissions/', ChildSubmissionsAPIView.as_view(), name='api_child_submissions'),
    path('submission/', SubmissionCreateAPIView.as_view(), name='api_submission_create'),
    
    path('districts/', DistrictListAPIView.as_view(), name='district-list'),

]