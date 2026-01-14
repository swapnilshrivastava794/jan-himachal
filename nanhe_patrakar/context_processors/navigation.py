from post_management.models import category

def blog_categories(request):
    """
    Provides Blogcat globally for header navigation
    """
    categories = category.objects.filter(cat_status='active').order_by('order')[:12]
    return {
        'Blogcat': categories
    }
