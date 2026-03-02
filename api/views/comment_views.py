# api/views/comment_views.py
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError, connection
from django.db.models import Prefetch

from ..models import Product, Comment, ProductImage
from ..serializers import CommentSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, product_id):
    """
    Add a comment to a product. Each user can only comment once per product.
    """
    try:
        # Check if product exists
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Extract data from request
        text = request.data.get('text', '').strip()
        rating = request.data.get('rating')

        # Validate input
        if not text:
            return Response(
                {"error": "Comment text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not rating or not (1 <= int(rating) <= 5):
            return Response(
                {"error": "Rating must be between 1 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to create the comment
        try:
            comment = Comment.objects.create(
                product=product,
                user=request.user,
                text=text,
                rating=int(rating)
            )

            serializer = CommentSerializer(comment)
            return Response({
                "success": True,
                "message": "Comment added successfully",
                "comment": serializer.data
            }, status=status.HTTP_201_CREATED)

        except IntegrityError:
            # This happens if user already commented on this product
            return Response({
                "error": "You have already commented on this product",
                "hint": "You can update your existing comment instead"
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def view_comments(request, product_id):
    """
    View all comments for a specific product.
    """
    try:
        # Clear the query log for performance monitoring
        connection.queries_log.clear()
        total_start = time.time()

        # Check if product exists and get comments in a single query with select_related
        try:
            # First verify the product exists
            if not Product.objects.filter(id=product_id).exists():
                return Response(
                    {"error": "Product not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get comments for this product with user information in a single query
            comments = Comment.objects.filter(
                product_id=product_id).select_related('user')

            # Log performance metrics
            query_time = time.time() - total_start
            print(f"Comments query time: {query_time:.4f} seconds")
            print(f"Number of queries executed: {len(connection.queries)}")

            serializer = CommentSerializer(comments, many=True)

            return Response({
                "success": True,
                "count": comments.count(),
                "comments": serializer.data
            })

        except Product.DoesNotExist:
            return Response(
                {"error": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_comment(request, comment_id):
    """
    Update user's own comment.
    """
    try:
        # Check if comment exists and belongs to user
        try:
            comment = Comment.objects.select_related(
                'product').get(id=comment_id, user=request.user)
        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found or you don't have permission to update it"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Extract data from request
        text = request.data.get('text', '').strip()
        rating = request.data.get('rating')

        # Validate input
        if not text:
            return Response(
                {"error": "Comment text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not rating or not (1 <= int(rating) <= 5):
            return Response(
                {"error": "Rating must be between 1 and 5"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the comment
        comment.text = text
        comment.rating = int(rating)
        comment.save()

        serializer = CommentSerializer(comment)
        return Response({
            "success": True,
            "message": "Comment updated successfully",
            "comment": serializer.data
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    """
    Delete user's own comment.
    """
    try:
        # Check if comment exists and belongs to user
        try:
            comment = Comment.objects.get(id=comment_id, user=request.user)
        except Comment.DoesNotExist:
            return Response(
                {"error": "Comment not found or you don't have permission to delete it"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete the comment
        comment.delete()

        return Response({
            "success": True,
            "message": "Comment deleted successfully"
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_comments(request):
    """
    Retrieve all comments made by the current authenticated user.
    """
    try:
        # Clear the query log for performance monitoring
        connection.queries_log.clear()
        total_start = time.time()

        # Get all comments for the current user with product and product images in a single query
        # This uses prefetch_related for the many-to-one relationship with ProductImage
        comments = Comment.objects.filter(user=request.user).select_related(
            'product', 'user'
        ).prefetch_related(
            Prefetch('product__images', queryset=ProductImage.objects.order_by(
                'order'), to_attr='prefetched_images')
        )

        # Log performance metrics
        query_time = time.time() - total_start
        print(f"User comments query time: {query_time:.4f} seconds")
        print(f"Number of queries executed: {len(connection.queries)}")

        # Serialize the comments
        serializer = CommentSerializer(comments, many=True)
        data = serializer.data

        # Add product information to each comment using the prefetched data
        for i, comment in enumerate(comments):
            data[i]['product_name'] = comment.product.name
            data[i]['product_id'] = comment.product.id

            # Get image URL if available (using prefetched data)
            if hasattr(comment.product, 'prefetched_images') and comment.product.prefetched_images:
                data[i]['product_image'] = comment.product.prefetched_images[0].image.url
            else:
                data[i]['product_image'] = None

        return Response({
            "success": True,
            "count": len(data),
            "comments": data
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
