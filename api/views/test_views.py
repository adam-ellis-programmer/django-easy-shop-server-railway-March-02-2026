# =============================================================================
# TESTING ROUTES
# =============================================================================
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

# Public test endpoint (no authentication required)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_public_endpoint(request):
    return Response({
        "success": True,
        "message": "This is a public test endpoint",
        "authenticated": request.user.is_authenticated,
        "user": request.user.username if request.user.is_authenticated else None
    })

# Protected test endpoint (authentication required)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_protected_endpoint(request):
    return Response({
        "success": True,
        "message": "This is a protected test endpoint and auth needed ",
        "authenticated": True,
        "user": request.user.username
    })

# api/views/test_views.py


@api_view(['GET'])
@permission_classes([AllowAny])
def test_public_endpoint(request):
    return Response({
        "success": True,
        "message": "This is a public test endpoint",
        "authenticated": request.user.is_authenticated,
        "user": request.user.username if request.user.is_authenticated else None
    })


@csrf_exempt  # Add CSRF exemption for testing
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_protected_endpoint(request):
    # Print basic info about the request data
    print("-----REQUEST DATA....------")
    print(request.data)

    # Extract values from request.data
    name = request.data.get('name')
    email = request.data.get('email')
    msg = request.data.get('msg')
    some_key = request.data.get('some_key')
    test = request.data.get('test')

    # Return a response with all the data
    return Response({
        "success": True,
        "message": "This is a protected test endpoint and auth needed",
        "authenticated": True,
        "user": request.user.username,
        "received_data": {
            "name": name,
            "email": email,
            "msg": msg,
            "some_key": some_key,
            "test": test
        }
    })
