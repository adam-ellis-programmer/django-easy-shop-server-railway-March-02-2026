# api/models.py
from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField


class Customer(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='customer'
    )  # link to Django's built-in User
    # your custom fields
    # related_name='customer' is what makes the magic work in both directions

    # Forward: Customer → User
    # customer.user.email

    # Reverse: User → Customer (this is what related_name enables)
    # user.customer.is_test_user

    is_test_user = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Product(models.Model):
    # Basic information
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)

    # Optional fields from your form
    itemsInStock = models.PositiveIntegerField(
        default=0, blank=True, null=True)
    percentageOff = models.PositiveIntegerField(
        default=0, blank=True, null=True)

    # Boolean fields
    featured = models.BooleanField(default=False)
    inStock = models.BooleanField(default=True)
    new = models.BooleanField(default=False)
    onSale = models.BooleanField(default=False)
    popular = models.BooleanField(default=False)
    specialOffer = models.BooleanField(default=False)
    suspend = models.BooleanField(default=False)

    # Description fields
    description = models.TextField(blank=True, null=True)
    detailedDescription = models.TextField(blank=True, null=True)

    # Foreign key to Customer
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='products')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Image for {self.product.name}"
# api/models.py


class ProductFeature(models.Model):
    """
    Stores bullet points for the 'About this item' section of products.
    Each bullet point is related to a specific product.
    """
    product = models.ForeignKey(
        'Product',  # Use string to avoid circular import issues
        on_delete=models.CASCADE,
        related_name='bullet_points'  # This allows product.bullet_points.all() access
    )
    text = models.CharField(
        max_length=500,
        help_text="Enter a feature or bullet point for this product"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="The order in which this bullet point appears in the list"
    )

    class Meta:
        ordering = ['order']  # Default ordering by the order field
        verbose_name = "Product Feature"
        verbose_name_plural = "Product Features"

    def __str__(self):
        return f"{self.product.name}: {self.text[:50]}{'...' if len(self.text) > 50 else ''}"


# api/models.py (add these models to your existing models file)

class Cart(models.Model):
    customer = models.OneToOneField(
        Customer, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.customer.user.username}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevent duplicate products in cart
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in cart {self.cart.id}"

    @property
    def total_price(self):
        return self.product.price * self.quantity


# api/models.py


class Comment(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensure each user can comment only once per product
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.product.name}"


class Bookmark(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='bookmarks')
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure each user can bookmark a product only once
        unique_together = ('customer', 'product')

    def __str__(self):
        return f"{self.customer.user.username} bookmarked {self.product.name}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    )
    # able to say customer.orders.all() with related name
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    session_id = models.CharField(
        max_length=255, blank=True, null=True, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    billing_address = models.TextField()
    payment_method = models.CharField(max_length=100)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    tracking_number = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.user.username} ({self.status})"

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True
    )
    # Store product details in case the product is deleted later
    product_name = models.CharField(max_length=255)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in Order #{self.order.id}"

    @property
    def total_price(self):
        return self.product_price * self.quantity

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"


"""
Why unique_together is appropriate here:
Many-to-many relationship with constraint: 
Each comment connects a user to a product, and a user can comment on many products, 

while a product can have comments from many users. 
You just want to add the constraint that a specific 
user-product combination can only occur once.

Composite unique constraint:  
unique_together creates a database-level 
constraint on the combination of two fields.

------- Why OneToOneField doesn't work for comments:
class Comment(models.Model):
    product_user = models.OneToOneField(???)

The problem is that OneToOneField links to a single model, 
not a combination of models. There's no 
"user-product" model to link to.
"""
