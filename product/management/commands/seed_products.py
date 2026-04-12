import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from django.contrib.auth import get_user_model

# Import your models - update 'users' and 'products' to your actual app names
from users.models import BusinessProfile
from product.models import Category, Product, Color, Size, ProductVariant

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds the database with 20 sample products and variants'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.HTTP_INFO("Starting database seed..."))

        try:
            with transaction.atomic():
                # 1. Get or Create a Merchant User (No username field used)
                merchant_user, created = User.objects.get_or_create(
                    email="seller@example.com",
                    defaults={
                        "is_active": True,  # Admin level active
                    }
                )
                if created:
                    merchant_user.set_password("password123")
                    merchant_user.save()

                # 2. Ensure Business Profile exists and is active
                merchant, _ = BusinessProfile.objects.get_or_create(
                    user=merchant_user,
                    defaults={
                        "store_name": "The Gift Hub",
                        "business_address": "123 Market St, Bangalore",
                        "tax_id": "GSTIN123456789",
                        "is_active": True  # Profile level active (OTP Verified)
                    }
                )

                # 3. Setup Categories
                cat_name = "Home & Decor"
                category, _ = Category.objects.get_or_create(
                    name=cat_name,
                    defaults={"slug": slugify(cat_name)}
                )

                # 4. Setup Attributes (Colors & Sizes)
                color_data = [('Midnight Black', '#000000'),
                              ('Arctic White', '#FFFFFF'),
                              ('Royal Blue', '#0000FF')]
                size_data = ['Small', 'Medium', 'Large', 'Extra Large']

                colors = [Color.objects.get_or_create(name=name,
                    defaults={'hex_code': hex})[0] for name, hex in color_data]
                sizes = [Size.objects.get_or_create(name=name)[0] for name in
                         size_data]

                # 5. Create 20 Products
                for i in range(1, 21):
                    p_name = f"Premium Gift Item {i}"
                    p_code = f"GFT-{1000 + i}"

                    # Create the main Product
                    product = Product.objects.create(
                        merchant=merchant,
                        category=category,
                        name=p_name,
                        description=f"This is a premium description for {p_name}. Perfect for any occasion.",
                        base_price=random.randint(99, 999),
                        brand="LuxuryGifts",
                        code=p_code,
                        created_by=merchant_user,
                        is_active=True
                    )

                    # 6. Create 3 random Variants for each Product
                    # We pick a random subset of colors/sizes to simulate real inventory
                    selected_colors = random.sample(colors, 2)
                    selected_sizes = random.sample(sizes, 2)

                    for color in selected_colors:
                        for size in selected_sizes:
                            ProductVariant.objects.create(
                                product=product,
                                color=color,
                                size=size,
                                sku=f"{p_code}-{color.name[:2].upper()}-{size.name[:1].upper()}-{random.randint(10, 99)}",
                                price=product.base_price + random.randint(50,
                                    200),
                                stock=random.randint(10, 100),
                                created_by=merchant_user
                            )

            self.stdout.write(self.style.SUCCESS(
                f'Successfully seeded 20 products for {merchant.store_name}!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seed failed: {str(e)}"))