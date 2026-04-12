from django.urls import path

from cart.api.v1.views import (
    CartView, CartItemView, CartItemDetailView,
    CheckoutView, OrderListView, OrderDetailView,
    PaymentView, StripeWebhookView,
)

urlpatterns = [
    # Cart
    path('', CartView.as_view(), name='cart'),
    path('items/', CartItemView.as_view(), name='cart-items'),
    path('items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    # Checkout
    path('checkout/', CheckoutView.as_view(), name='checkout'),

    # Orders
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),

    # Payment
    path('orders/<int:order_id>/payment/', PaymentView.as_view(), name='order-payment'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]