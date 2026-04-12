import stripe
from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from authenticate.permissions import CustomUserJWTAuthentication
from cart.models import Cart, CartItem, Order, OrderItem
from cart.api.v1.serializers import (
    CartSerializer, AddCartItemSerializer, UpdateCartItemSerializer,
    OrderSerializer, CheckoutSerializer,
)
from config.client.mail_engine import EmailEngine


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(buyer=user)
    return cart


# ─── Cart ────────────────────────────────────────────────────────────────────

@extend_schema(tags=['Cart'])
class CartView(APIView):
    """
    GET    — view the current buyer's cart
    DELETE — clear all items from the cart
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        return Response(CartSerializer(cart).data)

    def delete(self, request):
        cart = get_or_create_cart(request.user)
        cart.items.all().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Cart'])
class CartItemView(APIView):
    """
    POST — add a variant to the cart (increments qty if already present)
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        variant = serializer.validated_data['variant']
        quantity = serializer.validated_data['quantity']

        cart = get_or_create_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, variant=variant)

        if not created:
            new_qty = item.quantity + quantity
            if variant.stock < new_qty:
                return Response(
                    {"detail": f"Only {variant.stock} unit(s) available."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            item.quantity = new_qty
        else:
            item.quantity = quantity

        item.save()
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Cart'])
class CartItemDetailView(APIView):
    """
    PATCH  — update quantity of a specific cart item
    DELETE — remove a specific item from the cart
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_item(self, request, item_id):
        cart = get_or_create_cart(request.user)
        try:
            return cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return None

    def patch(self, request, item_id):
        item = self._get_item(request, item_id)
        if not item:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = UpdateCartItemSerializer(data=request.data, context={'item': item})
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data['quantity']
        item.save()
        return Response(CartSerializer(item.cart).data)

    def delete(self, request, item_id):
        item = self._get_item(request, item_id)
        if not item:
            return Response({"detail": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Checkout ────────────────────────────────────────────────────────────────

@extend_schema(
    tags=['Orders'],
    summary='Checkout — place an order from your cart',
    description=(
        'Validates stock for all cart items, creates an Order, decrements stock, and clears the cart. '
        'Rate-limited to 10/min.\n\n'
        'After placing the order, call `POST /cart/api/v1/orders/{id}/payment/` to pay via Stripe.'
    ),
    request=CheckoutSerializer,
    responses={
        201: OrderSerializer,
        400: OpenApiResponse(description='Cart empty or stock insufficient'),
    }
)
class CheckoutView(APIView):
    """
    POST — convert the cart into an order.
    Validates stock, creates Order + OrderItems, decrements stock, clears cart.
    Rate-limited to 10/min to prevent stock abuse.
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'checkout'

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_or_create_cart(request.user)
        items = list(cart.items.select_related('variant', 'variant__product').all())

        if not items:
            return Response({"detail": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate stock for every item before touching anything
        errors = []
        for item in items:
            if item.variant.stock < item.quantity:
                errors.append(
                    f"'{item.variant.product.name}' ({item.variant.sku}): "
                    f"only {item.variant.stock} unit(s) in stock."
                )
        if errors:
            return Response({"detail": errors}, status=status.HTTP_400_BAD_REQUEST)

        total = sum(item.subtotal for item in items)

        with transaction.atomic():
            order = Order.objects.create(
                buyer=request.user,
                shipping_address=serializer.validated_data['shipping_address'],
                total=total,
            )

            order_items = []
            for item in items:
                order_items.append(OrderItem(
                    order=order,
                    variant=item.variant,
                    product_name=item.variant.product.name,
                    sku=item.variant.sku,
                    price=item.variant.price,
                    quantity=item.quantity,
                ))
                item.variant.stock -= item.quantity
                item.variant.save()

            OrderItem.objects.bulk_create(order_items)
            cart.items.all().delete()

        # Notify buyer — order placed, awaiting payment
        EmailEngine.send_order_confirmation(request.user.email, order)

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


# ─── Orders ──────────────────────────────────────────────────────────────────

@extend_schema(tags=['Orders'], summary='List my orders', responses={200: OrderSerializer(many=True)})
class OrderListView(APIView):
    """GET — list the current buyer's orders"""
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects
            .filter(buyer=request.user)
            .prefetch_related('items')
            .order_by('-created_at')
        )
        return Response(OrderSerializer(orders, many=True).data)


@extend_schema(tags=['Orders'], summary='Get order detail', responses={200: OrderSerializer, 404: OpenApiResponse(description='Order not found')})
class OrderDetailView(APIView):
    """GET — retrieve a single order (must belong to the requesting buyer)"""
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = Order.objects.prefetch_related('items').get(
                id=order_id, buyer=request.user
            )
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OrderSerializer(order).data)


# ─── Stripe Payment ──────────────────────────────────────────────────────────

@extend_schema(
    tags=['Orders'],
    summary='Initiate Stripe payment for an order',
    description=(
        'Creates a Stripe PaymentIntent and returns the `client_secret`.\n\n'
        'The frontend uses this with **Stripe.js** (`stripe.confirmCardPayment(client_secret)`) '
        'to complete the payment. Once payment succeeds, Stripe notifies the webhook and the '
        'order status is automatically updated to `confirmed`.'
    ),
    responses={
        200: inline_serializer('PaymentIntentResponse', fields={
            'client_secret': serializers.CharField(),
            'payment_intent_id': serializers.CharField(),
            'amount': serializers.DecimalField(max_digits=12, decimal_places=2),
            'currency': serializers.CharField(),
        }),
        400: OpenApiResponse(description='Order already processed or Stripe error'),
        404: OpenApiResponse(description='Order not found'),
    }
)
class PaymentView(APIView):
    """
    POST — create a Stripe PaymentIntent for a pending order.
    Returns client_secret for the frontend to complete payment with Stripe.js.
    """
    authentication_classes = [CustomUserJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, buyer=request.user)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        if order.status != Order.Status.PENDING:
            return Response(
                {"detail": f"Order is already '{order.status}', cannot initiate payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(order.total * 100),  # Stripe expects smallest currency unit (cents)
                currency='usd',
                metadata={'order_id': order.id, 'buyer_email': request.user.email},
            )
            return Response({
                'client_secret': intent['client_secret'],
                'payment_intent_id': intent['id'],
                'amount': order.total,
                'currency': 'usd',
            })
        except stripe.error.StripeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(exclude=True)  # Internal webhook — exclude from public docs
class StripeWebhookView(APIView):
    """
    POST — Stripe sends signed payment events here.
    On payment_intent.succeeded: confirms the order and emails the buyer.
    Authentication is handled by Stripe's webhook signature, not JWT.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({"detail": "Invalid payload."}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'payment_intent.succeeded':
            intent = event['data']['object']
            order_id = intent.get('metadata', {}).get('order_id')

            if order_id:
                try:
                    order = Order.objects.prefetch_related('items').get(id=order_id)
                    if order.status == Order.Status.PENDING:
                        order.status = Order.Status.CONFIRMED
                        order.save()
                        EmailEngine.send_payment_confirmed(order.buyer.email, order)
                except Order.DoesNotExist:
                    pass

        return Response({'status': 'ok'})