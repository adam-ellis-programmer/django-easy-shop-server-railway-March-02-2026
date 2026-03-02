from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from api.models import Cart


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_payment(request):
    """Calculate the total payment amount from the user's cart and include product images"""
    try:
        # Get the customer's cart
        cart = request.user.customer.cart

        # Calculate total (using the property from the model)
        total_amount = cart.total_price
        item_count = cart.item_count

        # Get individual items with their details including images
        items = []
        for item in cart.items.all():
            # Get product images
            product_images = []
            for image in item.product.images.all().order_by('order'):
                product_images.append({
                    'id': image.id,
                    'url': image.image.url,  # Cloudinary image URL
                    'order': image.order
                })

            # Create item data with images
            item_data = {
                'id': item.id,
                'product_id': item.product.id,
                'name': item.product.name,
                'price': float(item.product.price),
                'quantity': item.quantity,
                'subtotal': float(item.total_price),
                'images': product_images
            }

            items.append(item_data)

        return JsonResponse({
            'success': True,
            'payment': {
                'total_amount': float(total_amount),
                'item_count': item_count,
                'items': items
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
