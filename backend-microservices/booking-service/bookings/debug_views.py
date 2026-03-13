from django.http import JsonResponse


def debug_user(request):
    """Debug endpoint to check user authentication"""
    return JsonResponse({
        'user': str(request.user),
        'user_type': str(type(request.user)),
        'is_authenticated': request.user.is_authenticated,
        'is_authenticated_type': type(request.user.is_authenticated),
        'id': str(getattr(request.user, 'id', None)),
        'email': getattr(request.user, 'email', None),
        'has_is_authenticated_attr': hasattr(request.user, 'is_authenticated'),
    })
