from django.contrib import admin

from cart.models import Cart, CartItem, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'sku', 'price', 'quantity']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'updated_at']
    inlines = [CartItemInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'status', 'total', 'created_at']
    list_filter = ['status']
    inlines = [OrderItemInline]