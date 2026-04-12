from django_filters import FilterSet, NumberFilter, BooleanFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from authenticate.permissions import IsMerchant, IsOwner, CustomUserJWTAuthentication
from cart.models import Order
from config.client.mail_engine import EmailEngine
from product.api.v1.core.paginations import StandardResultsSetPagination
from product.models import Product, Color, Size
from product.api.v1.serializers import (
    ProductListSerializer, ProductDetailSerializer,
    ProductCreateSerializer, ProductUpdateSerializer,
    ColorSerializer, SizeSerializer,
    MerchantOrderSerializer, OrderStatusUpdateSerializer,
)


# --- Product filter ---

class ProductFilter(FilterSet):
    min_price = NumberFilter(field_name='base_price', lookup_expr='gte')
    max_price = NumberFilter(field_name='base_price', lookup_expr='lte')
    in_stock = BooleanFilter(method='filter_in_stock')

    class Meta:
        model = Product
        fields = ['category__slug', 'brand', 'merchant__store_name']

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(variants__stock__gt=0).distinct()
        return queryset


# --- Color / Size ---

@extend_schema(tags=['Merchant'])
class ColorListView(viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]


@extend_schema(tags=['Merchant'])
class SizeListView(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]


# --- Product ---

@extend_schema_view(
    list=extend_schema(
        tags=['Products'],
        summary='List all active products',
        parameters=[
            OpenApiParameter('min_price', OpenApiTypes.DECIMAL, description='Minimum base price'),
            OpenApiParameter('max_price', OpenApiTypes.DECIMAL, description='Maximum base price'),
            OpenApiParameter('in_stock', OpenApiTypes.BOOL, description='Only show products with stock available'),
            OpenApiParameter('category__slug', OpenApiTypes.STR, description='Filter by category slug'),
            OpenApiParameter('brand', OpenApiTypes.STR, description='Filter by brand name'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Search across name, description, brand, code'),
            OpenApiParameter('ordering', OpenApiTypes.STR, description='Order by: created_on, base_price (prefix - for descending)'),
        ],
    ),
    retrieve=extend_schema(tags=['Products'], summary='Get product detail by slug'),
    create=extend_schema(tags=['Merchant'], summary='Create a new product', description='Merchant only. Variants and images are nested in the request.'),
    update=extend_schema(tags=['Merchant'], summary='Update a product (full)'),
    partial_update=extend_schema(tags=['Merchant'], summary='Update a product (partial)'),
    destroy=extend_schema(tags=['Merchant'], summary='Deactivate a product', description='Soft delete — sets is_active=False. Product is hidden from listings but preserved in order history.'),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    list/retrieve  — public (AllowAny)
    create         — merchants only (IsMerchant)
    update/delete  — merchant + owner only (IsMerchant + IsOwner)
    destroy        — soft delete (sets is_active=False)
    """
    authentication_classes = [CustomUserJWTAuthentication]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'brand', 'code']
    ordering_fields = ['created_on', 'base_price']
    lookup_field = 'slug'

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related(
            'category', 'merchant'
        ).prefetch_related('images', 'variants')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated(), IsMerchant()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsMerchant(), IsOwner()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer
        if self.action == 'retrieve':
            return ProductDetailSerializer
        if self.action == 'create':
            return ProductCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ProductUpdateSerializer
        return ProductDetailSerializer

    # --- Public ---

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # --- Merchant only ---

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save(merchant=request.user.business_profile)
        return Response(ProductDetailSerializer(product).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductDetailSerializer(product).data)

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Soft delete — marks product inactive instead of removing from DB."""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Merchant order dashboard ---

@extend_schema(
    tags=['Merchant'],
    summary='List orders for my store',
    description='Returns all orders that contain at least one product belonging to the authenticated merchant.',
    parameters=[
        OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status: pending, confirmed, shipped, delivered, cancelled'),
    ],
    responses={200: MerchantOrderSerializer(many=True)},
)
class MerchantOrderListView(APIView):
    """
    GET — list all orders that contain the merchant's products, newest first.
    Optionally filter by status: ?status=pending
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated, IsMerchant]

    def get(self, request):
        queryset = Order.objects.filter(
            items__variant__product__merchant=request.user.business_profile
        ).distinct().prefetch_related('items').order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = MerchantOrderSerializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['Merchant'],
    summary='Update order status',
    description=(
        'Updates the status of an order. Valid transitions:\n\n'
        '`pending` → `confirmed` or `cancelled`\n\n'
        '`confirmed` → `shipped` or `cancelled`\n\n'
        '`shipped` → `delivered`\n\n'
        'Buyer receives an email notification on every status change.'
    ),
    request=OrderStatusUpdateSerializer,
    responses={
        200: MerchantOrderSerializer,
        400: OpenApiResponse(description='Invalid status transition'),
        404: OpenApiResponse(description='Order not found'),
    },
)
class MerchantOrderStatusUpdateView(APIView):
    """
    PATCH — update the status of an order that contains the merchant's products.
    Enforces valid status transitions and emails the buyer on change.
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated, IsMerchant]

    def patch(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items').get(
                id=order_id,
                items__variant__product__merchant=request.user.business_profile
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={'order': order}
        )
        serializer.is_valid(raise_exception=True)

        order.status = serializer.validated_data['status']
        order.save()

        EmailEngine.send_order_status_update(order.buyer.email, order)

        return Response(MerchantOrderSerializer(order).data)