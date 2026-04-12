from django.db import models
from django.conf import settings
from django.utils.text import slugify

from users.models import BusinessProfile


# Create your models here.

class AbstractUserBase(models.Model):
    """
    Abstract User base class for sub apps under core
    """
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   related_name='%(class)s_createdby',
                                   blank=True, null=True,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    related_name='%(class)s_modifiedby',
                                    null=True, blank=True,
                                    on_delete=models.SET_NULL)

    class Meta:
        abstract = True

class AbstractDateBase(models.Model):
    """
    Abstract Date base class for sub apps under core
    """
    created_on = models.DateTimeField(auto_now_add=True)
    modified_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
    
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    # Self-referencing FK for sub-categories
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    image = models.ImageField(upload_to='categories/', null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        k = self.parent
        while k is not None:
            full_path.append(k.name)
            k = k.parent
        return ' -> '.join(full_path[::-1])

class Product(AbstractUserBase, AbstractDateBase):
    merchant = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='products'
    )
    name = models.CharField(max_length=255)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True, blank=True) # Allow blank for auto-generation
    code = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.name)}-{self.code.lower()}"
        super().save(*args, **kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['-created_on']),
        ]

    def __str__(self):
        return self.name

class ProductImage(AbstractUserBase, AbstractDateBase):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    is_feature = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_feature:
            ProductImage.objects.filter(product=self.product,
                is_feature=True).update(is_feature=False)
        super().save(*args, **kwargs)

class Color(AbstractUserBase, AbstractDateBase):
    name = models.CharField(max_length=50, unique=True)
    hex_code = models.CharField(max_length=7, help_text="e.g. #FFFFFF") # For frontend swatches

    def __str__(self):
        return self.name

class Size(AbstractUserBase, AbstractDateBase):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class ProductVariant(AbstractUserBase, AbstractDateBase):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.PROTECT, related_name='variants')
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'color', 'size')
        verbose_name = "Product Variant"
        verbose_name_plural = "Product Variants"

    def __str__(self):
        return f"{self.product.name} ({self.color.name} - {self.size.name})"