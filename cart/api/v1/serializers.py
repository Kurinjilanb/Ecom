from rest_framework import serializers

from cart.models import Cart, CartItem, Order, OrderItem
from product.models import ProductVariant


class CartItemSerializer(serializers.ModelSerializer):
    variant_sku = serializers.ReadOnlyField(source='variant.sku')
    product_name = serializers.ReadOnlyField(source='variant.product.name')
    color = serializers.ReadOnlyField(source='variant.color.name')
    size = serializers.ReadOnlyField(source='variant.size.name')
    unit_price = serializers.ReadOnlyField(source='variant.price')
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = CartItem
        fields = ['id', 'variant', 'variant_sku', 'product_name', 'color', 'size',
                  'unit_price', 'quantity', 'subtotal']
        read_only_fields = ['id']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'updated_at']


class AddCartItemSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=ProductVariant.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate(self, data):
        variant = data['variant']
        quantity = data['quantity']
        if variant.stock < quantity:
            raise serializers.ValidationError(
                f"Only {variant.stock} unit(s) available for this variant."
            )
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        item = self.context.get('item')
        if item and item.variant.stock < value:
            raise serializers.ValidationError(
                f"Only {item.variant.stock} unit(s) available."
            )
        return value


# --- Order ---

class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'sku', 'price', 'quantity', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'status', 'shipping_address', 'total', 'items', 'created_at']
        read_only_fields = ['id', 'status', 'total', 'created_at']


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()