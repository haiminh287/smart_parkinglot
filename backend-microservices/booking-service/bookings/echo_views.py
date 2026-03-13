"""Test endpoint to echo headers"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def echo_headers(request):
    """Echo all headers received"""
    headers = {}
    for key, value in request.META.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-')
            headers[header_name] = value
        elif key in ['CONTENT_TYPE', 'CONTENT_LENGTH']:
            headers[key] = value
    
    return JsonResponse({
        'headers': headers,
        'session_keys': list(request.session.keys()) if hasattr(request, 'session') else [],
        'session_data': {
            '_auth_user_id': request.session.get('_auth_user_id') if hasattr(request, 'session') else None,
            'user_email': request.session.get('user_email') if hasattr(request, 'session') else None,
        }
    })
