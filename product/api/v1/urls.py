from django.urls import path, include
from rest_framework.routers import DefaultRouter

from product.api.v1.views import (
    ProductViewSet, ColorListView, SizeListView,
    MerchantOrderListView, MerchantOrderStatusUpdateView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'colors', ColorListView, basename='color')
router.register(r'sizes', SizeListView, basename='size')

urlpatterns = [
    path(r'', include(router.urls)),

    # Merchant order dashboard
    path('merchant/orders/', MerchantOrderListView.as_view(), name='merchant-orders'),
    path('merchant/orders/<int:order_id>/status/', MerchantOrderStatusUpdateView.as_view(), name='merchant-order-status'),
]