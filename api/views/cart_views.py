# api/views/cart_views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import pprint
from django.db.models import Prefetch
from ..models import Customer, Product, Cart, CartItem
from ..serializers import CartSerializer, CartItemSerializer

# Helper function to get or create a customer's cart with optimized queries


def get_or_create_cart(customer):
    try:
        # Use select_related for ForeignKey relationships and prefetch_related for related items
        return Cart.objects.prefetch_related(
            Prefetch('items', queryset=CartItem.objects.select_related('product'))
        ).get(customer=customer)
    except Cart.DoesNotExist:
        return Cart.objects.create(customer=customer)

# ===========================================================================
# Get current cart for authenticated customer
# ===========================================================================


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customer_cart(request):
    try:
        # Get the customer with one query
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Get or create the customer's cart with prefetched items and products
        cart = get_or_create_cart(customer)

        # Serialize the cart with its items
        serializer = CartSerializer(cart)

        return Response({
            "success": True,
            "cart": serializer.data
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

# ===========================================================================
# Add item to cart
# ===========================================================================


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    # Debug information
    pprint.pprint("=== DEBUG: ADD TO CART REQUEST ===")
    pprint.pprint(
        f"User: {request.user} (authenticated: {request.user.is_authenticated})")
    pprint.pprint(f"Method: {request.method}")
    pprint.pprint(f"Headers: {request.headers}")
    pprint.pprint(f"Data: {request.data}")
    pprint.pprint(
        f"CSRF Token from Header: {request.headers.get('X-CSRFTOKEN', 'None')}")
    pprint.pprint(f"Content Type: {request.content_type}")

    try:
        # Extract data from request
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        # Validate product_id
        if not product_id:
            return Response(
                {"error": "Product ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate quantity
        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the customer
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Get or create the cart
        cart = get_or_create_cart(customer)

        # Check if the product exists and is available
        try:
            product = Product.objects.get(
                id=product_id, inStock=True, suspend=False)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or unavailable"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use get_or_create to reduce queries
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            # Update quantity if item already exists
            cart_item.quantity += quantity
            # Only update the quantity field
            cart_item.save(update_fields=['quantity'])
            message = "Item quantity updated in cart"
        else:
            message = "Item added to cart"

        # Refresh cart with prefetched items to ensure serializer has latest data
        cart = get_or_create_cart(customer)

        # Return updated cart
        serializer = CartSerializer(cart)

        return Response({
            "success": True,
            "message": message,
            "cart": serializer.data
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===========================================================================
# Update cart item quantity
# ===========================================================================


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    try:
        # Extract quantity from request
        quantity = int(request.data.get('quantity', 1))

        # Validate quantity
        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the customer
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Use select_related to optimize the query
        cart_item = CartItem.objects.select_related('cart', 'product').get(
            id=item_id,
            cart__customer=customer
        )

        # Update the quantity with only the necessary fields
        cart_item.quantity = quantity
        cart_item.save(update_fields=['quantity'])

        # Get the updated cart with prefetched items
        cart = get_or_create_cart(customer)

        # Return updated cart
        serializer = CartSerializer(cart)

        return Response({
            "success": True,
            "message": "Cart item updated",
            "cart": serializer.data
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except CartItem.DoesNotExist:
        return Response(
            {"error": "Item not found in cart"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===========================================================================
# Remove item from cart
# ===========================================================================


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_from_cart(request, item_id):
    try:
        # Get the customer
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Combine queries to check if item exists and belongs to the customer
        cart_item = CartItem.objects.select_related('cart').get(
            id=item_id,
            cart__customer=customer
        )

        # Delete the cart item
        cart_item.delete()

        # Get the updated cart with prefetched items
        cart = get_or_create_cart(customer)

        # Return updated cart
        serializer = CartSerializer(cart)

        return Response({
            "success": True,
            "message": "Item removed from cart",
            "cart": serializer.data
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except CartItem.DoesNotExist:
        return Response(
            {"error": "Item not found in cart"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===========================================================================
# Clear cart
# ===========================================================================


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_cart(request):
    try:
        # Get the customer
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # More efficient bulk delete operation
        deleted, _ = CartItem.objects.filter(cart__customer=customer).delete()

        if deleted > 0:
            message = "Cart cleared"
        else:
            message = "Cart was already empty"

        # Get the updated empty cart
        cart = get_or_create_cart(customer)

        # Return empty cart
        serializer = CartSerializer(cart)

        return Response({
            "success": True,
            "message": message,
            "cart": serializer.data
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
