# api/views/bookmark_views.py
import time
from django.db import connection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import Bookmark, Product, Customer
from ..serializers import BookmarkSerializer


def log_performance(func):
    def wrapper(*args, **kwargs):
        # Clear existing queries
        connection.queries_log.clear()

        # Start timing
        start_time = time.time()

        # Execute the view function
        result = func(*args, **kwargs)

        # Calculate time and log queries
        total_time = time.time() - start_time
        query_count = len(connection.queries)

        print(f"--- Performance Log for {func.__name__} ---")
        print(f"Total execution time: {total_time:.4f} seconds")
        print(f"Number of queries: {query_count}")

        # Log individual queries (top 5 slowest)
        if query_count > 0:
            sorted_queries = sorted(connection.queries,
                                    key=lambda q: float(q.get('time', 0)),
                                    reverse=True)

            print("\nTop 5 slowest queries:")
            for i, query in enumerate(sorted_queries[:5]):
                print(
                    f"{i+1}. Time: {query.get('time')}s - {query.get('sql')[:150]}...")

        print("-----------------------------------")

        return result
    return wrapper


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@log_performance
def get_user_bookmarks(request):
    try:
        # Get the customer associated with the logged in user
        # Use select_related to get user data in the same query
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Get all bookmarks for this customer with prefetched product data
        # This avoids N+1 query problem in the serializer
        bookmarks = Bookmark.objects.filter(customer=customer)\
            .select_related('product')\
            .prefetch_related('product__images', 'product__bullet_points')

        # Serialize the bookmarks with related product data
        serializer = BookmarkSerializer(bookmarks, many=True)

        return Response({
            'success': True,
            'bookmarks': serializer.data
        })
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Customer profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@log_performance
def toggle_bookmark(request):
    try:
        # Get the product ID from the request data
        product_id = request.data.get('product_id')

        if not product_id:
            return Response({
                'success': False,
                'error': 'Product ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get the customer associated with the logged in user
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Get the product
        product = Product.objects.get(id=product_id)

        # Check if bookmark already exists
        bookmark = Bookmark.objects.filter(
            customer=customer, product=product).first()

        if bookmark:
            # If bookmark exists, remove it
            bookmark.delete()
            message = 'Bookmark removed'
        else:
            # If bookmark doesn't exist, create it
            bookmark = Bookmark.objects.create(
                customer=customer, product=product)
            message = 'Bookmark added'

        # Get updated bookmarks for user with prefetched data
        bookmarks = Bookmark.objects.filter(customer=customer)\
            .select_related('product')\
            .prefetch_related('product__images', 'product__bullet_points')

        serializer = BookmarkSerializer(bookmarks, many=True)

        return Response({
            'success': True,
            'message': message,
            'bookmarks': serializer.data
        })
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Customer profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Product.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Product not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@log_performance
def remove_bookmark(request, bookmark_id):
    try:
        # Get the customer associated with the logged in user
        customer = Customer.objects.select_related(
            'user').get(user=request.user)

        # Get the bookmark and ensure it belongs to this customer
        bookmark = Bookmark.objects.get(id=bookmark_id, customer=customer)

        # Delete the bookmark
        bookmark.delete()

        # Get updated bookmarks for user with prefetched data
        bookmarks = Bookmark.objects.filter(customer=customer)\
            .select_related('product')\
            .prefetch_related('product__images', 'product__bullet_points')

        serializer = BookmarkSerializer(bookmarks, many=True)

        return Response({
            'success': True,
            'message': 'Bookmark removed successfully',
            'bookmarks': serializer.data
        })
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Customer profile not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Bookmark.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Bookmark not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
