# get_csrf_token → plain Django view
# LoginView, RegisterView, LogoutView → DRF APIViews
# api/views/auth_views.py

import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse

from ..models import Customer
from ..serializers import UserSerializer, RegisterSerializer


#
from django.middleware.csrf import get_token


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Create user
            user = User.objects.create_user(
                # Use email as username
                username=serializer.validated_data['email'],
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                first_name=serializer.validated_data['first_name'],
                last_name=serializer.validated_data['last_name']
            )

            #  Creates the associated customer profile
            customer = Customer.objects.create(user=user)

            #  Logs the user in (creates session)
            login(request, user)

            # Return user data (but not password)
            user_data = UserSerializer(user).data

            return Response({
                'user': user_data,
                'message': 'Registration successful'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# login(request, user)
# ```

# Django's built-in `login()` function does several things automatically:
# ```
# 1. Verifies the user is authenticated
# 2. Creates a new session in the database
# 3. Generates a unique session ID
# 4. Adds Set-Cookie: sessionid=ji09p6bp... to the response
# 5. Browser stores the sessionid cookie

class LoginView(APIView):
    # no csrf token needed
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Please provide both email and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by email (since we're using email as username)
        try:
            user = User.objects.get(email=email)

        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Authenticate with username (which is set to email)
        user = authenticate(username=user.username, password=password)

        if user:
            # *** SETS THE SESSION COOKIE IN THE BROWSER ***
            login(request, user)
            return Response({
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            })

        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'})


# we call this fron user slice (register & login) #
# ******** @ensure_csrf_cookie sets the csrf ********

# It's a Django decorator that says "make sure the
# CSRF cookie is set on the response". Django intercepts
# the response before it's sent and adds the Set-Cookie:
# csrftoken=... header automatically.

# old version without token response
# @ensure_csrf_cookie
# def get_csrf_token(request):
#     """View to set CSRF cookie"""
#     return JsonResponse({"success": "CSRF cookie set"})


@ensure_csrf_cookie
def get_csrf_token(request):
    """View to set CSRF cookie and return token in response body"""
    return JsonResponse({
        "csrfToken": get_token(request)
    })
