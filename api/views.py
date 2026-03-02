# # api/views.py
# import json
# import cloudinary.uploader
# from rest_framework import status
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from django.contrib.auth.models import User
# from django.contrib.auth import authenticate, login, logout
# from django.db import transaction
# from .models import Customer, Product, ProductImage
# from django.views.decorators.csrf import ensure_csrf_cookie
# from .serializers import UserSerializer, RegisterSerializer
# from .serializers import ProductSerializer

# import os


# class RegisterView(APIView):
#     permission_classes = [AllowAny]

#     @transaction.atomic
#     def post(self, request):
#         serializer = RegisterSerializer(data=request.data)
#         if serializer.is_valid():
#             # Create user
#             user = User.objects.create_user(
#                 # Use email as username
#                 username=serializer.validated_data['email'],
#                 email=serializer.validated_data['email'],
#                 password=serializer.validated_data['password'],
#                 first_name=serializer.validated_data['first_name'],
#                 last_name=serializer.validated_data['last_name']
#             )

#             #  Creates the associated customer profile
#             customer = Customer.objects.create(user=user)

#             #  Logs the user in (creates session)
#             login(request, user)

#             # Returns user data (session cookie is automatically set)
#             # Return user data (but not password)
#             user_data = UserSerializer(user).data

#             return Response({
#                 'user': user_data,
#                 'message': 'Registration successful'
#             }, status=status.HTTP_201_CREATED)

#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class LoginView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email = request.data.get('email')
#         password = request.data.get('password')

#         if not email or not password:
#             return Response(
#                 {'error': 'Please provide both email and password'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # Find user by email (since we're using email as username)
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return Response(
#                 {'error': 'Invalid credentials'},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )

#         # Authenticate with username (which is set to email)
#         user = authenticate(username=user.username, password=password)

#         if user:
#             login(request, user)
#             return Response({
#                 'user': UserSerializer(user).data,
#                 'message': 'Login successful'
#             })

#         return Response(
#             {'error': 'Invalid credentials'},
#             status=status.HTTP_401_UNAUTHORIZED
#         )


# class LogoutView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         logout(request)
#         return Response({'message': 'Logout successful'})


# @ensure_csrf_cookie
# def get_csrf_token(request):
#     """View to set CSRF cookie"""
#     from django.http import JsonResponse
#     return JsonResponse({"success": "CSRF cookie set"})


# # =================================================================
# # CREATE PRODUCT
# # =================================================================

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def add_product(request):
#     print("Request FILES:", request.FILES)
    
#     # Get the customer associated with the authenticated user
#     try:
#         customer = Customer.objects.get(user=request.user)
#     except Customer.DoesNotExist:
#         return Response(
#             {"error": "Customer profile not found for this user"},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     # Handle multipart form data
#     product_data = request.data.copy()
    
#     # Parse boolean fields
#     boolean_fields = [
#         'featured', 'inStock', 'new', 'onSale',
#         'popular', 'specialOffer', 'suspend'
#     ]
    
#     for field in boolean_fields:
#         # Convert string values to boolean
#         if field in product_data:
#             product_data[field] = product_data[field].lower() == 'true'
#         else:
#             product_data[field] = False
    
#     # Extract images from request
#     images = request.FILES.getlist('images')
    
#     # Create serializer
#     serializer = ProductSerializer(data=product_data)
    
#     if serializer.is_valid():
#         # Save product with customer relationship
#         product = serializer.save(customer=customer)
        
#         # Upload images to Cloudinary and create ProductImage objects
#         for index, image_file in enumerate(images):
#             # Upload to Cloudinary
#             upload_result = cloudinary.uploader.upload(image_file)
            
#             # Create ProductImage with order value based on index
#             ProductImage.objects.create(
#                 product=product,
#                 image=upload_result['public_id'],  # Store Cloudinary public_id
#                 order=index  # Set the order based on the position in the list
#             )
        
#         # Re-fetch the product with images to return in response
#         updated_product = Product.objects.get(pk=product.pk)
#         updated_serializer = ProductSerializer(updated_product)
        
#         return Response(
#             {
#                 "success": True,
#                 "message": "Product added successfully",
#                 "product": updated_serializer.data
#             },
#             status=status.HTTP_201_CREATED
#         )
    
#     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   