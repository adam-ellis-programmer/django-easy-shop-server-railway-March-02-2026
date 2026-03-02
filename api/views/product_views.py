# api/views/product_views.py
from ..models import Product
from rest_framework.permissions import AllowAny
from pprint import pprint
import cloudinary.uploader
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch

from ..models import Customer, Product, ProductImage, ProductFeature
from ..serializers import ProductSerializer, ProductImageSerializer, ProductFeatureSerializer

# ===========================================b================================
# authenticated add product to database
# ===========================================================================


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_product(request):
    pprint({"REQUEST FILES": request.FILES})
    pprint({"REQUEST HEADERS": dict(request.headers)})
    pprint({"REQUEST METHOD": request.method})
    pprint({"REQUEST USER": str(request.user)})
    pprint({"REQUEST USER_id": str(request.user.id)})
    print('------------------ user')
    pprint(request.user)
    try:
        # Get the customer associated with the authenticated user
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Handle multipart form data
    product_data = request.data.copy()

    # Extract bullet points
    # takes the bullet points out the data so we can store them in a seperate table ProductFeature
    bullet_points = []
    for key in request.data:
        if key.startswith('bullet_') and request.data[key].strip():
            try:
                # Extract the index number for ordering
                # Adjust for zero-based indexing
                index = int(key.split('_')[1]) - 1
                bullet_points.append({
                    'text': request.data[key].strip(),
                    'order': index
                })
            except (IndexError, ValueError):
                # If there's an issue with the key format, just append with default order
                bullet_points.append({
                    'text': request.data[key].strip(),
                    'order': len(bullet_points)
                })

    # Remove bullet points from the product_data
    for key in list(product_data.keys()):
        if key.startswith('bullet_'):
            del product_data[key]

    # Parse boolean fields
    boolean_fields = [
        'featured', 'inStock', 'new', 'onSale',
        'popular', 'specialOffer', 'suspend'
    ]

    for field in boolean_fields:
        if field in product_data:
            value = product_data.get(field)
            if isinstance(value, str):
                is_true = value.lower() in ['true', 'on', '1', 'yes']
            else:
                is_true = bool(value)
            product_data[field] = is_true
        else:
            product_data[field] = False

    # Extract images from request
    images = request.FILES.getlist('images')

    # Create serializer
    serializer = ProductSerializer(data=product_data)

    if serializer.is_valid():
        # Save product with customer relationship
        product = serializer.save(customer=customer)

        # Create bullet points
        for bullet_point in bullet_points:
            ProductFeature.objects.create(
                product=product,
                text=bullet_point['text'],
                order=bullet_point['order']
            )

        # Upload images to Cloudinary and create ProductImage objects
        for index, image_file in enumerate(images):
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(image_file)

            # Create ProductImage with order field
            ProductImage.objects.create(
                product=product,
                image=upload_result['public_id'],  # Store Cloudinary public_id
                order=index  # Set the order based on the position in the list
            )

        # Re-fetch the product with images and bullet points to return in response
        # OPTIMIZED: Use prefetch_related to get all related data in one query
        updated_product = Product.objects.prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
            Prefetch('bullet_points',
                     queryset=ProductFeature.objects.order_by('order'))
        ).get(pk=product.pk)

        # Get ordered images (no additional query needed due to prefetch)
        image_serializer = ProductImageSerializer(
            updated_product.images.all(), many=True)

        # Get ordered bullet points (no additional query needed due to prefetch)
        bullet_point_serializer = ProductFeatureSerializer(
            updated_product.bullet_points.all(), many=True)

        # Combine product data with images and bullet points
        product_data = ProductSerializer(updated_product).data
        product_data['images'] = image_serializer.data
        product_data['bullet_points'] = bullet_point_serializer.data

        return Response(
            {
                "success": True,
                "message": "Product added successfully",
                "product": product_data
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ===========================================================================
# authenticated customer get their products
# ===========================================================================


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customer_products(request):
    print('------------- CUSTOMER--PRODUCTS RAN -------------')
    try:
        # Get the customer associated with the authenticated user
        customer = Customer.objects.get(user=request.user)

        # Get all products for this customer WITH prefetched relationships
        import time
        start_time = time.time()

        products = Product.objects.filter(
            customer=customer
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
            Prefetch('bullet_points',
                     queryset=ProductFeature.objects.order_by('order'))
        ).order_by('-created_at')

        # Serialize products with their related data
        product_data = []
        for product in products:
            # Use prefetched data - no new queries
            product_serialized = ProductSerializer(product).data

            # These don't generate new queries now
            product_serialized['images'] = ProductImageSerializer(
                product.images.all(), many=True
            ).data

            product_serialized['bullet_points'] = ProductFeatureSerializer(
                product.bullet_points.all(), many=True
            ).data

            product_data.append(product_serialized)

        # Get execution time
        execution_time = time.time() - start_time
        print(f"Query execution time: {execution_time:.2f} seconds")

        return Response({
            "success": True,
            "products": product_data,
            # Include this for debugging
            "execution_time_seconds": round(execution_time, 2)
        })

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

# ===========================================================================
# authenticated customer get their single product (to edit)
# ===========================================================================


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_customer_product_by_id(request, product_id):
    try:
        # Get the customer associated with the authenticated user
        customer = Customer.objects.get(user=request.user)

        # Get the specific product that belongs to this customer
        try:
            # OPTIMIZED: Use prefetch_related here to get all related data in one query
            product = Product.objects.prefetch_related(
                Prefetch(
                    'images', queryset=ProductImage.objects.order_by('order')),
                Prefetch('bullet_points',
                         queryset=ProductFeature.objects.order_by('order'))
            ).get(id=product_id, customer=customer)

            # Get the product's images (no additional query needed due to prefetch)
            image_serializer = ProductImageSerializer(
                product.images.all(), many=True)

            # Get the product's bullet points (no additional query needed due to prefetch)
            bullet_point_serializer = ProductFeatureSerializer(
                product.bullet_points.all(), many=True)

            # Serialize the product
            product_serialized = ProductSerializer(product).data
            product_serialized['images'] = image_serializer.data
            product_serialized['bullet_points'] = bullet_point_serializer.data

            return Response({
                "success": True,
                "product": product_serialized
            })

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or you don't have permission to access it"},
                status=status.HTTP_404_NOT_FOUND
            )

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

# ===========================================================================
# authenticated customer update product
# ===========================================================================


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_customer_product(request, product_id):
    try:
        # Get the customer associated with the authenticated user
        customer = Customer.objects.get(user=request.user)

        # Get the specific product that belongs to this customer
        try:
            product = Product.objects.get(id=product_id, customer=customer)

            # Process form data
            product_data = request.data.copy()

            # Extract bullet points
            bullet_points = []
            for key in request.data:
                if key.startswith('bullet_') and request.data[key].strip():
                    try:
                        index = int(key.split('_')[1]) - 1
                        bullet_points.append({
                            'text': request.data[key].strip(),
                            'order': index
                        })
                    except (IndexError, ValueError):
                        bullet_points.append({
                            'text': request.data[key].strip(),
                            'order': len(bullet_points)
                        })

            # Remove bullet points from the product_data
            for key in list(product_data.keys()):
                if key.startswith('bullet_'):
                    del product_data[key]

            # Parse boolean fields
            boolean_fields = [
                'featured', 'inStock', 'new', 'onSale',
                'popular', 'specialOffer', 'suspend'
            ]

            for field in boolean_fields:
                if field in product_data:
                    value = product_data.get(field)
                    if isinstance(value, str):
                        is_true = value.lower() in ['true', 'on', '1', 'yes']
                    else:
                        is_true = bool(value)
                    product_data[field] = is_true
                else:
                    product_data[field] = False

            # Extract images from request
            images = request.FILES.getlist('images')

            # Update the product with the form data
            serializer = ProductSerializer(
                product, data=product_data, partial=True)

            if serializer.is_valid():
                # Save updated product
                updated_product = serializer.save()

                # Delete existing bullet points
                ProductFeature.objects.filter(product=product).delete()

                # Create new bullet points
                for bullet_point in bullet_points:
                    ProductFeature.objects.create(
                        product=updated_product,
                        text=bullet_point['text'],
                        order=bullet_point['order']
                    )

                # Handle image uploads if new images are provided
                if images:
                    # Upload new images to Cloudinary and create ProductImage objects
                    for index, image_file in enumerate(images):
                        # Upload to Cloudinary
                        upload_result = cloudinary.uploader.upload(image_file)

                        # Create ProductImage with order field
                        ProductImage.objects.create(
                            product=updated_product,
                            image=upload_result['public_id'],
                            order=ProductImage.objects.filter(
                                product=product).count() + index
                        )

                # OPTIMIZED: Re-fetch the product with images and bullet points using prefetch_related
                updated_product = Product.objects.prefetch_related(
                    Prefetch(
                        'images', queryset=ProductImage.objects.order_by('order')),
                    Prefetch('bullet_points',
                             queryset=ProductFeature.objects.order_by('order'))
                ).get(pk=product.pk)

                # Get ordered images (no additional query needed due to prefetch)
                image_serializer = ProductImageSerializer(
                    updated_product.images.all(), many=True)

                # Get ordered bullet points (no additional query needed due to prefetch)
                bullet_point_serializer = ProductFeatureSerializer(
                    updated_product.bullet_points.all(), many=True)

                # Combine product data with images and bullet points
                product_data = ProductSerializer(updated_product).data
                product_data['images'] = image_serializer.data
                product_data['bullet_points'] = bullet_point_serializer.data

                return Response({
                    "success": True,
                    "message": "Product updated successfully",
                    "product": product_data
                })

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or you don't have permission to access it"},
                status=status.HTTP_404_NOT_FOUND
            )

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

# ===========================================================================
# authenticated customer delete product
# ===========================================================================


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_customer_product(request, product_id):
    try:
        # Get the customer associated with the authenticated user
        customer = Customer.objects.get(user=request.user)

        # Get the specific product that belongs to this customer
        try:
            product = Product.objects.get(id=product_id, customer=customer)

            # Delete associated images first (optional - depends on your model setup)
            # If you're using Cloudinary, you might want to delete the images from Cloudinary too
            for image in product.images.all():
                # Optional: Delete from Cloudinary
                # cloudinary.uploader.destroy(image.image)
                image.delete()

            # Delete the product
            product.delete()

            return Response({
                "success": True,
                "message": "Product deleted successfully"
            })

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found or you don't have permission to delete it"},
                status=status.HTTP_404_NOT_FOUND
            )

    except Customer.DoesNotExist:
        return Response(
            {"error": "Customer profile not found for this user"},
            status=status.HTTP_400_BAD_REQUEST
        )

# ===========================================================================
# public products
# ===========================================================================


@api_view(['GET'])
@permission_classes([AllowAny])
def public_products(request):
    print('hello')
    try:
        # Use Prefetch for ordered relations
        products = Product.objects.filter(
            inStock=True,
            suspend=False
        ).prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.order_by('order')),
            Prefetch('bullet_points',
                     queryset=ProductFeature.objects.order_by('order'))
        ).order_by('-created_at')

        # Optionally add more filters
        category = request.query_params.get('category', None)
        if category:
            products = products.filter(category=category)

        # Get total count for pagination
        total_products = products.count()

        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('pageSize', 9))
        # page wil always be at least 1 so we start at 0 * 9
        start = (page - 1) * page_size
        # 0 - 8
        # 9 - 17
        # 18 - 26
        end = start + page_size

        paginated_products = products[start:end]

        # Serialize products
        product_data = []
        for product in paginated_products:
            product_serialized = ProductSerializer(product).data
            product_serialized['images'] = ProductImageSerializer(
                # No need for .order_by() - already ordered in prefetch
                product.images.all(), many=True
            ).data
            product_serialized['bullet_points'] = ProductFeatureSerializer(
                # No need for .order_by() - already ordered in prefetch
                product.bullet_points.all(), many=True
            ).data

            product_data.append(product_serialized)

        return Response({
            "success": True,
            "products": product_data,
            "pagination": {
                "total": total_products,
                "page": page,
                "pageSize": page_size,
                "totalPages": (total_products + page_size - 1) // page_size
            }
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===========================================================================
#  public get product by id
# ===========================================================================


@api_view(['GET'])
@permission_classes([AllowAny])
def get_public_product_by_id(request, product_id):
    import time
    from django.db import connection

    # Clear the query log and start timing
    connection.queries_log.clear()
    total_start = time.time()

    print(f'====> get_public_product_by_id for product {product_id} <====')

    try:
        # Time the database query
        query_start = time.time()
        try:
            product = Product.objects.prefetch_related(
                Prefetch(
                    'images', queryset=ProductImage.objects.order_by('order')),
                Prefetch('bullet_points',
                         queryset=ProductFeature.objects.order_by('order'))
            ).get(id=product_id, inStock=True, suspend=False)

            query_time = time.time() - query_start
            print(f"Database query time: {query_time:.4f} seconds")
            print(f"Number of queries executed: {len(connection.queries)}")

            # Log the actual SQL queries
            for i, query in enumerate(connection.queries):
                print(
                    f"Query {i+1}: {query['time']}s - {query['sql'][:150]}...")

        except Product.DoesNotExist:
            return Response(
                {"success": False, "error": "Product not found or unavailable"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Time the serialization process
        serial_start = time.time()

        # Get the product's images (no additional query needed due to prefetch)
        image_serializer = ProductImageSerializer(
            product.images.all(), many=True)

        # Get the product's bullet points (no additional query needed due to prefetch)
        bullet_point_serializer = ProductFeatureSerializer(
            product.bullet_points.all(), many=True)

        # Serialize the product
        product_serialized = ProductSerializer(product).data
        product_serialized['images'] = image_serializer.data
        product_serialized['bullet_points'] = bullet_point_serializer.data

        serial_time = time.time() - serial_start
        print(f"Serialization time: {serial_time:.4f} seconds")

        total_time = time.time() - total_start
        print(f"Total view execution time: {total_time:.4f} seconds")

        return Response({
            "success": True,
            "product": product_serialized
        })

    except Exception as e:
        total_time = time.time() - total_start
        print(f"Error occurred after {total_time:.4f} seconds: {str(e)}")
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ===========================================================================
#  search products
# ===========================================================================


@api_view(['GET'])
def search_products(request):
    query = request.GET.get('q', '')

    print('QUERY BACKEND========>', query)

    if not query:
        return Response({'success': False, 'error': 'No search query provided'})

    # OPTIMIZED: Use prefetch_related when searching for products
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__icontains=query) |
        Q(tags__icontains=query)
    ).exclude(
        suspend=True
    ).prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.order_by('order')),
        Prefetch('bullet_points',
                 queryset=ProductFeature.objects.order_by('order'))
    )

    # Use the same serialization approach as in public_products
    product_data = []
    for product in products:
        # Serialize the product (no additional queries needed due to prefetch)
        product_serialized = ProductSerializer(product).data
        product_serialized['images'] = ProductImageSerializer(
            product.images.all(), many=True).data
        product_serialized['bullet_points'] = ProductFeatureSerializer(
            product.bullet_points.all(), many=True).data

        product_data.append(product_serialized)

    return Response({
        'success': True,
        'count': len(product_data),
        'products': product_data
    })
