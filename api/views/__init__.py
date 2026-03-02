# api/views/__init__.py
# First, since you already have the search_products
# function in the product_views.py file, we need to
# update your __init__.py to expose this function.
# Then update your URLs file to use the imported search_products view function.
# from .auth_views import RegisterView, LoginView, LogoutView, get_csrf_token
# api/views/__init__.py

# from .auth_views import RegisterView, LoginView, LogoutView, get_csrf_token
from .auth_views import RegisterView, LoginView, LogoutView
# ======================
# Product views
# ======================
from .product_views import (
    add_product,
    get_customer_products,
    get_customer_product_by_id,
    update_customer_product,
    delete_customer_product,
)

# ======================
# Public product views
# ======================
from .product_views import (
    public_products,
    get_public_product_by_id,
    search_products,  # Add this line to import the search function
)
# ======================
# Cart views
# ======================
from .cart_views import (
    get_customer_cart,
    add_to_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart,
)

# This allows imports like: from api.views import RegisterView, add_product, get_customer_cart
# ======================
#  comment views
# ======================
from .comment_views import (
    add_comment,
    view_comments,
    update_comment,
    delete_comment,
    get_user_comments,
)
# ======================
# book mark views
# ======================

from .bookmark_views import (
    toggle_bookmark,
    get_user_bookmarks,
    remove_bookmark
)

# ======================
# filter views
# ======================

from .filter_views import (
    filter_products,
)

# ======================
# payment views
# ======================
from .stripe_payment import (
    create_checkout_session,
    session_status,
)