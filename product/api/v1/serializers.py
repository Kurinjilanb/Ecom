from django.db import transaction
from rest_framework import serializers
from product.models import Product, ProductVariant, ProductImage, Category, Color, Size


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex_code']

    def validate_name(self, value):
        return value.strip().title()

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.hex_code = validated_data.get('hex_code', instance.hex_code)
        instance.save()
        return instance


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'name']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_feature']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'color', 'size', 'sku', 'price', 'stock']


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    merchant_name = serializers.CharField(source='merchant.store_name', read_only=True)
    thumbnail = serializers.SerializerMethodField()
    starting_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'brand', 'category_name',
            'merchant_name', 'thumbnail', 'starting_price', 'is_active', 'base_price'
        ]

    def get_thumbnail(self, obj):
        image = obj.images.filter(is_feature=True).first() or obj.images.first()
        if image:
            return image.image.url
        return None

    def get_starting_price(self, obj):
        first_variant = obj.variants.order_by('price').first()
        return first_variant.price if first_variant else obj.base_price


class ProductDetailSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    store_name = serializers.CharField(source='merchant.store_name', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'brand', 'base_price',
            'category_name', 'store_name', 'variants', 'images', 'created_on'
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True)
    images = ProductImageSerializer(many=True, required=False)

    class Meta:
        model = Product
        fields = ['name', 'description', 'base_price', 'category', 'brand', 'code', 'variants', 'images']

    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
        images_data = validated_data.pop('images', [])

        with transaction.atomic():
            product = Product.objects.create(**validated_data)

            ProductVariant.objects.bulk_create([
                ProductVariant(product=product, **variant)
                for variant in variants_data
            ])

            if images_data:
                ProductImage.objects.bulk_create([
                    ProductImage(product=product, **img)
                    for img in images_data
                ])

        return product


class ProductUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['name', 'description', 'base_price', 'category', 'brand', 'is_active']

