
# api/views/user_views.py
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import Customer
from ..serializers import UserSerializer

# Get user details


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user(request, user_id):
        # ADD THESE DEBUG LINES
    print(f"Requested user_id: {user_id}")
    print(f"Authenticated user ID: {request.user.id}")
    print(f"User is staff: {request.user.is_staff}")
    print(f"User is authenticated: {request.user.is_authenticated}")

    # Check if the requesting user is authorized to access this data
    if request.user.id != user_id and not request.user.is_staff:
        return Response(
            {"error": "You are not authorized to access this user's data"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)
        serializer = UserSerializer(user)
        serialized_data = serializer.data

        # Add is_active status directly -- seraliser is handling this 
        # serialized_data['is_active'] = user.is_active

        # Get the customer profile if it exists
        customer_data = {}
        try:
            customer = Customer.objects.get(user=user)
            customer_data = {
                "customer_id": customer.id,
                "created_at": customer.created_at,
                "updated_at": customer.updated_at
            }
        except Customer.DoesNotExist:
            pass

        # Combine user data with customer data
        data = {
            "success": True,
            "user": {**serialized_data, **customer_data}
        }

        return Response(data)
    except User.DoesNotExist:
        return Response(
            {"success": False, "error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
# Update user details


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_user(request, user_id):
    # Check if the requesting user is authorized to update this data
    if request.user.id != user_id and not request.user.is_staff:
        return Response(
            {"error": "You are not authorized to update this user's data"},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        user = User.objects.get(id=user_id)

        # Get the updatable fields from the request
        data = request.data

        # Fields that regular users can update
        allowed_fields = ['first_name', 'last_name', 'email', 'is_active']

        # Additional fields that only staff/admins can update
        admin_fields = ['username']

        # Update the allowed fields
        for field in allowed_fields:
            if field in data:
                # Special handling for boolean fields
                if field == 'is_active':
                    # Convert string 'true'/'false' to boolean if needed
                    if isinstance(data[field], str):
                        value = data[field].lower() == 'true'
                    else:
                        value = bool(data[field])
                    setattr(user, field, value)
                else:
                    setattr(user, field, data[field])

        # Admin can update additional fields
        if request.user.is_staff or request.user.is_superuser:
            for field in admin_fields:
                if field in data:
                    setattr(user, field, data[field])

        # Save the user
        user.save()

        # Return the updated user data
        serializer = UserSerializer(user)
        serialized_data = serializer.data

        # Add is_active status directly if it's not in the serializer
        if 'is_active' not in serialized_data:
            serialized_data['is_active'] = user.is_active

        return Response({
            "success": True,
            "user": serialized_data,
            "message": "User updated successfully"
        })
    except User.DoesNotExist:
        return Response(
            {"success": False, "error": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
