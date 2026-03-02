# api/views/order_views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Prefetch
import logging

from api.models import Order, OrderItem, Product, ProductImage

# Set up logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_orders(request):
    print('------ orders ran -------')
    """
    Get all orders for the authenticated customer with their order items and product images
    """
    try:
        # Get customer associated with the authenticated user
        customer = request.user.customer

        # in models so we use Order, on_delete=models.CASCADE, related_name='items'
        orders = Order.objects.filter(customer=customer).prefetch_related(
            'items',
            'items__product',
        ).order_by('-created_at')

        orders_data = []
        for order in orders:
            # Use 'items' instead of 'orderitem_set'
            order_items = order.items.all()  # Changed this line

            # Format items with their first image
            items_data = []
            for item in order_items:
                # Default item data
                item_data = {
                    'id': item.id,
                    'product_id': item.product.id if item.product else None,
                    'product_name': item.product_name,
                    'product_price': str(item.product_price),
                    'quantity': item.quantity,
                    'total_price': str(item.total_price),
                    'image_url': None
                }

                # Handle image separately to avoid potential issues
                if item.product:
                    try:
                        first_image = ProductImage.objects.filter(
                            product=item.product).order_by('order').first()
                        if first_image and first_image.image:
                            item_data['image_url'] = first_image.image.url
                    except Exception as img_err:
                        # Log error but continue processing
                        logger.error(
                            f"Error fetching image for product {item.product.id}: {str(img_err)}")

                items_data.append(item_data)

            # Format the complete order
            order_data = {
                'id': order.id,
                'status': order.status,
                'total_amount': str(order.total_amount),
                'item_count': order.item_count,
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'tracking_number': order.tracking_number or '',  # Ensure not None
                'items': items_data
            }

            orders_data.append(order_data)

        return JsonResponse({
            'success': True,
            'orders': orders_data
        })

    except Exception as e:
        # Log the full exception for debugging
        logger.error(f"Error in get_orders: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_order_by_id(request, order_id):
    """
    Get a specific order by ID with its order items and product images
    """
    try:
        # Get customer associated with the authenticated user
        customer = request.user.customer

        # Simplify the query to ensure it works properly
        order = get_object_or_404(
            Order.objects.prefetch_related(
                'orderitem_set',
                'orderitem_set__product'
            ),
            id=order_id,
            customer=customer
        )

        # Format items with their first image
        items_data = []
        for item in order.orderitem_set.all():
            item_data = {
                'id': item.id,
                'product_id': item.product.id if item.product else None,
                'product_name': item.product_name,
                'product_price': str(item.product_price),
                'quantity': item.quantity,
                'total_price': str(item.total_price),
                'image_url': None
            }

            # Handle image separately with proper error handling
            if item.product:
                try:
                    first_image = ProductImage.objects.filter(
                        product=item.product).order_by('order').first()
                    if first_image and first_image.image:
                        item_data['image_url'] = first_image.image.url
                except Exception as img_err:
                    # Log error but continue processing
                    logger.error(
                        f"Error fetching image for product {item.product.id}: {str(img_err)}")

            items_data.append(item_data)

        # Format the complete order with null checks
        order_data = {
            'id': order.id,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'item_count': order.item_count,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'shipping_address': order.shipping_address or '',
            'billing_address': order.billing_address or '',
            'payment_method': order.payment_method or '',
            'payment_status': order.payment_status or '',
            'tracking_number': order.tracking_number or '',
            'items': items_data
        }

        return JsonResponse({
            'success': True,
            'order': order_data
        })

    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        # Log the full exception for debugging
        logger.error(f"Error in get_order_by_id: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
