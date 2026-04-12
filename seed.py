import os
import django
import random

# 1. Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils.text import slugify
from django.contrib.auth import get_user_model
from users.models import BusinessProfile
from product.models import Category, Product, Color, Size, ProductVariant

User = get_user_model()

def seed_data():

    # 1. Create a Test Merchant
    user, _ = User.objects.get_or_create(email="merchant@test.com")
    user.set_password("password123")
    user.is_active = True
    user.save()

    merchant, _ = BusinessProfile.objects.get_or_create(
        user=user,
        defaults={'name': 'Tech Haven', 'is_active': True}
    )

    # 2. Create Categories (Parent > Child)
    electronics, _ = Category.objects.get_or_create(name="Electronics")
    laptops, _ = Category.objects.get_or_create(name="Laptops", parent=electronics)
    phones, _ = Category.objects.get_or_create(name="Smartphones", parent=electronics)

    # 3. Create Attributes
    colors = []
    for c_name, hex_c in [('Space Gray', '#3c3c3c'), ('Silver', '#c0c0c0'), ('Midnight', '#000033')]:
        color, _ = Color.objects.get_or_create(name=c_name, hex_code=hex_c)
        colors.append(color)

    sizes = []
    for s_name in ['256GB', '512GB', '1TB']:
        size, _ = Size.objects.get_or_create(name=s_name)
        sizes.append(size)

    # 4. Create a Base Product
    product, created = Product.objects.get_or_create(
        merchant=merchant,
        category=laptops,
        name="MacBook Pro 14",
        defaults={
            'description': 'M3 Chip, Liquid Retina XDR display.',
            'base_price': 1999.99,
            'brand': 'Apple',
            'code': 'MBP14-M3'
        }
    )

    # 5. Create Variants
    if created:
        for c in colors:
            for s in sizes:
                ProductVariant.objects.create(
                    product=product,
                    color=c,
                    size=s,
                    sku=f"MBP14-{c.name[:2]}-{s.name}".upper(),
                    price=product.base_price + random.randint(0, 500),
                    stock=random.randint(5, 20)
                )


if __name__ == '__main__':
    seed_data()