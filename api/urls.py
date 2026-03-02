# api/urls.py
# as_view = class based views
from django.urls import path

# ======================================
# AUTHENTIVATED
# ======================================
from .views import (
    RegisterView, LoginView, LogoutView,
    add_product, get_customer_products,
    get_customer_product_by_id, update_customer_product,
    delete_customer_product, public_products,
    get_public_product_by_id,
    # Payment views
    create_checkout_session, session_status,
)
from .views import cart_views  # Import cart_views module
from .views import search_products
# TEST ROUTES
# Import test views from the correct location
from .views.test_views import test_public_endpoint, test_protected_endpoint

# imported from the __init__
from .views import (
    add_comment, view_comments, update_comment, delete_comment, get_user_comments
)
from .views import bookmark_views

from .views import filter_products
from .views import payment_views
from .views.auth_views import get_csrf_token  # add this import
# from folder/function
from .views.order_views import get_orders, get_order_by_id
from .views.user_views import get_user, update_user

urlpatterns = [

    # =========================================================================
    # AUTH ROUTES
    # =========================================================================
    path('get-csrf-token/', get_csrf_token, name='get_csrf_token'),
    # fmt: off
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),


    # =========================================================================
    # PRODUCT ROUTES
    # =========================================================================

    # ============================
    # CUSTOMER AUTHENTICATED ROUTES
    # ============================

    path('add-product/', add_product, name='add_product'),
    path('customer-products/', get_customer_products, name='customer_products'),
    path('customer-products/<int:product_id>/', get_customer_product_by_id, name='customer_product_by_id'),
    path('customer-products/<int:product_id>/update/', update_customer_product, name='update_customer_product'),
    path('customer-products/<int:product_id>/delete/', delete_customer_product, name='delete_customer_product'),

    # search -- placed before products/<int:product_id> the more specific pattern should appear first.
     # ============================
     # FILTER / SEARCH ROUTES
     # ============================
    path('products/search/', search_products, name='search_products'),
    path('products/filter/', filter_products, name='filter_products'),


     # ============================
     # PUBLIC ROUTES
     # ============================
    path('products/', public_products, name='public_products'),
    # Use the imported view directly instead of product_views.get_public_product_by_id
    path('products/<int:product_id>/', get_public_product_by_id, name='get_public_product_by_id'),

    # =========================================================================
    # CART ROUTES
    # =========================================================================
    path('cart/', cart_views.get_customer_cart, name='get_customer_cart'),
    path('cart/add/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/',cart_views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', cart_views.clear_cart, name='clear_cart'),



    # =========================================================================
    # COMMENT ROUTES
    # =========================================================================
    path('products/<int:product_id>/comments/',view_comments, name='view_comments'),
    path('products/<int:product_id>/comments/add/',add_comment, name='add_comment'),
    path('comments/<int:comment_id>/update/', update_comment, name='update_comment'),
    path('comments/<int:comment_id>/delete/',delete_comment, name='delete_comment'),

    # get logged in users comments
     path('user/comments/', get_user_comments, name='get_user_comments'),         


    # =========================================================================
    # BOOKMARK ROUTES
    # =========================================================================

    path('bookmarks/', bookmark_views.get_user_bookmarks, name='get_user_bookmarks'),
    path('bookmarks/toggle/', bookmark_views.toggle_bookmark, name='toggle_bookmark'),
    path('bookmarks/<int:bookmark_id>/', bookmark_views.remove_bookmark, name='remove_bookmark'),



    # =========================================================================
    # PAYMENT ROUTES
    # =========================================================================
    path('payment/calculate/', payment_views.calculate_payment, name='calculate_payment'),
    path('payment/create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    path('payment/session-status/', session_status, name='session_status'),


    # =========================================================================
    # ORDER ROUTES
    # =========================================================================

    path('orders/', get_orders, name='get_orders'), 
    path('orders/<int:order_id>/', get_order_by_id, name='get_order_by_id'),  

    # =========================================================================
    # USER ROUTES 
    # =========================================================================

    path('get-user/<int:user_id>/', get_user, name='get_user'),  
    path('update-user/<int:user_id>/', update_user, name='update_user'),  

    # Test routes
    path('test/', test_public_endpoint, name='test_public_endpoint'),
    path('test/protected/', test_protected_endpoint, name='test_protected_endpoint'),
]

