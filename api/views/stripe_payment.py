# api/views/stripe_payment.py
import json
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, IntegrityError

from ..models import Cart, Order, OrderItem, Customer

# Configure Stripe with your secret key from settings
stripe.api_key = settings.STRIPE_SECRET_KEY


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def create_checkout_session(request):
    print('---------------------------------------  ran -------------')
    """
    Create a Stripe checkout session for payment processing
    """
    try:
        # Get user's customer object
        customer = request.user.customer

        # Get the user's cart
        cart = Cart.objects.get(customer=customer)

        if cart.items.count() == 0:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Create line items for Stripe checkout
        line_items = []
        for item in cart.items.all():
            line_items.append({
                'price_data': {
                    'currency': 'gbp',  # Using GBP as per your UI
                    'product_data': {
                        'name': item.product.name,
                        # Add image if available
                        'images': [item.product.images.first().image.url] if item.product.images.exists() else [],
                    },
                    # Stripe requires amount in cents
                    'unit_amount': int(item.product.price * 100),
                },
                'quantity': item.quantity,
            })

        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            ui_mode='embedded',
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            customer_email=request.user.email,
            metadata={
                'cart_id': cart.id,
                'user_id': request.user.id,
            },
            # Use the frontend URL as return URL
            return_url=f"{settings.FRONTEND_URL}/return?session_id={{CHECKOUT_SESSION_ID}}",
        )

        return JsonResponse({'clientSecret': session.client_secret})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@csrf_exempt
def session_status(request):
    """
    Check the status of a checkout session
    """
    try:
        session_id = request.GET.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)

        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        # Track if we've processed this session
        is_processed = False

        # If payment is successful, check if an order already exists or create a new one
        if session.status == 'complete' and session.payment_status == 'paid':
            # Get metadata from session
            user_id = session.metadata.get('user_id')
            cart_id = session.metadata.get('cart_id')

            # Check if we've already processed this session
            existing_order = Order.objects.filter(
                session_id=session_id).first()
            if existing_order:
                # Order already exists for this session, no need to create a new one
                print(
                    f"Order already exists for session {session_id}, skipping creation")
                is_processed = True
            else:
                # Process the completed payment (create order, etc.)
                _process_successful_payment(session)
                is_processed = True

        return JsonResponse({
            'status': session.status,
            'is_processed': is_processed,
            'customer_email': session.customer_details.email if hasattr(session, 'customer_details') else None
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@transaction.atomic
def _process_successful_payment(session):
    print('PROCESSED ==== RAN ----------')
    """
    Process a successful payment by creating an order and emptying the cart
    """
    try:
        # Get user and cart from metadata
        user_id = int(session.metadata.get('user_id'))
        cart_id = int(session.metadata.get('cart_id'))
        session_id = session.id  # Get the Stripe session ID

        from django.contrib.auth.models import User
        user = User.objects.get(id=user_id)
        customer = Customer.objects.get(user=user)
        cart = Cart.objects.get(id=cart_id, customer=customer)

        # Check if cart is empty - skip creating an order if it is
        if cart.items.count() == 0:
            print(
                f"Cart is empty for session {session_id}, skipping order creation")
            return None

        try:
            # Create a new order with the session_id
            order = Order.objects.create(
                customer=customer,
                status='processing',
                total_amount=cart.total_price,
                shipping_address=session.shipping.address.to_dict() if hasattr(
                    session, 'shipping') and session.shipping else "{}",
                billing_address=session.customer_details.address.to_dict() if hasattr(
                    session, 'customer_details') and session.customer_details.address else "{}",
                payment_method='card',
                payment_status='completed',
                session_id=session_id  # Store the session ID in the order
            )

            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_price=cart_item.product.price,
                    quantity=cart_item.quantity
                )

            # Empty the cart
            cart.items.all().delete()

            return order

        except IntegrityError as e:
            # This could happen if another thread/process created an order with this session_id
            print(
                f"IntegrityError while creating order for session {session_id}: {e}")
            # Return the existing order instead
            return Order.objects.get(session_id=session_id)

    except Exception as e:
        # Log error but don't fail the response
        print(f"Error processing payment: {str(e)}")
        return None
