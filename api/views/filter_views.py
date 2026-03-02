# api/views/filter_views.py
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
import time

from ..models import Product
from ..serializers import ProductSerializer, ProductImageSerializer, ProductFeatureSerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def filter_products(request):

    # Clear the query log
    connection.queries_log.clear()

    # Start timing
    start_time = time.time()

    try:
        # Get the category from query parameters
        category = request.GET.get('q', '')

        if not category:
            return Response({
                "success": False,
                "error": "No category provided"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Filter products by category (only active/non-suspended products)
        # Use prefetch_related to load related images and bullet_points in a single query
        query_start = time.time()
        products = Product.objects.filter(
            category__icontains=category,
            inStock=True,
            suspend=False
        ).prefetch_related(
            'images',
            'bullet_points'
        ).order_by('-created_at')
        products_list = list(products)  # Force query execution
        query_time = time.time() - query_start
        print(f"Query execution time: {query_time:.2f} seconds")

        # Timing serialization separately
        serialize_start = time.time()
        # Serialize products with their images and bullet points
        product_data = []
        for product in products_list:
            # Get the product's images (already prefetched)
            product_images = sorted(
                product.images.all(), key=lambda x: x.order)
            image_serializer = ProductImageSerializer(
                product_images, many=True)

            # Get the product's bullet points (already prefetched)
            product_bullet_points = sorted(
                product.bullet_points.all(), key=lambda x: x.order)
            bullet_point_serializer = ProductFeatureSerializer(
                product_bullet_points, many=True)

            # Serialize the product
            product_serialized = ProductSerializer(product).data
            product_serialized['images'] = image_serializer.data
            product_serialized['bullet_points'] = bullet_point_serializer.data

            product_data.append(product_serialized)

        serialize_time = time.time() - serialize_start
        print(f"Serialization time: {serialize_time:.2f} seconds")

        # Print all executed queries
        print(f"Total queries executed: {len(connection.queries)}")
        for i, query in enumerate(connection.queries):
            print(f"Query {i+1}: {query['time']}s - {query['sql']}")

        total_time = time.time() - start_time
        print(f"Total view execution time: {total_time:.2f} seconds")

        return Response({
            "success": True,
            "count": len(product_data),
            "products": product_data
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
