# pagination.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DynamicPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class with dynamic page size
    
    Query Parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 10, max: 100)
    
    Example: /api/districts/?page=2&page_size=20
    """
    page_size = 10  # Default page size
    page_size_query_param = 'page_size'  # Allow client to set page size
    max_page_size = 100  # Maximum page size limit
    page_query_param = 'page'  # Page number parameter
    
    def get_paginated_response(self, data):
        """
        Custom paginated response format
        """
        return Response({
            'status': True,
            'message': 'Districts retrieved successfully',
            'data': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            }
        })