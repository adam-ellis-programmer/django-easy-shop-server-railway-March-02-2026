# api/serializers.py
# turns django data into json
from .models import Comment, Bookmark
import os
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Product, ProductImage, ProductFeature, CartItem, Cart

# Serializers handle the conversion between Python objects and JSON/XML. They're similar to Django forms.
# You can add custom fields with SerializerMethodField as you've seen:


from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'is_test_user', 'is_suspended']


class UserSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name',
                  'last_name', 'is_active', 'customer']


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    def validate_email(self, value):
        """Check that the email is not already in use"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists.")
        return value


# include order in the frontend response (expose these fields)
# Get your Cloudinary cloud name from environment or settings
CLOUDINARY_CLOUD_NAME = os.environ.get(
    'CLOUDINARY_CLOUD_NAME', 'your-cloud-name')


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order', 'image_url']

    def get_image_url(self, obj):
        # obj is the actual ProductImage database object
        # dynamically create a new field in the serialized output that doesn't exist in the database model.
        # he method that provides the value must be named get_<field_name>
        # frontend receives JSON that includes both the original database fields AND your calculated image_url field:
        # not storing duplicative data (the full URL) in your database.
        # If you need to change your cloud provider or URL structure, you only need to update the serializer, not the database.
        # Construct the full Cloudinary URL
        return f"https://res.cloudinary.com/{CLOUDINARY_CLOUD_NAME}/image/upload/{obj.image}"

# api/serializers.py
# Update the ProductSerializer to include images


# api/serializers.py

class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = ['id', 'text', 'order']


class ProductSerializer(serializers.ModelSerializer):
    # Add bullet_points to the serializer
    bullet_points = ProductFeatureSerializer(many=True, read_only=True)
    # explicitly define the images field in your ProductSerializer using the appropriate nested serializer:
    # With this change, the images field will use the ProductImageSerializer to serialize each related image, giving you the full image objects with all their fields.
    images = ProductImageSerializer(many=True, read_only=True)  # Add this line

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'description', 'detailedDescription',
            'category', 'tags', 'inStock', 'itemsInStock',
            'featured', 'new', 'onSale', 'percentageOff',
            'popular', 'specialOffer', 'suspend', 'bullet_points',
            'images',
        ]
# In Product Views: You're manually adding serialized images using product_serialized['images'] = image_serializer.data
# In Cart Views: You're relying on the default serialization of the images field which only gives you IDs
# For images, you've only included the field name in the fields list without defining it explicitly

# api/serializers.py (add these serializers to your existing serializers file)


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity',
                  'total_price', 'added_at', 'updated_at']

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total_price',
                  'item_count', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())

    def get_item_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'text', 'rating', 'user',
                  'username', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username


# Adding new serializers for the Bookmark feature
class BookmarkProductSerializer(serializers.ModelSerializer):
    """Serializer for product data within bookmarks to ensure we get all needed product details"""
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'price', 'description', 'category',
            'tags', 'images', 'inStock', 'onSale', 'percentageOff',
            'specialOffer'
        ]


class BookmarkSerializer(serializers.ModelSerializer):
    """Serializer for bookmarks with nested product data"""
    product = BookmarkProductSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ['id', 'customer', 'product', 'created_at']
        read_only_fields = ['customer', 'created_at']
