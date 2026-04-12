from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from users.fields import CustomEmailField


class UserManager(BaseUserManager):
    """
    Custom User manager
    """
    use_in_migrations = True

    def _create_user(self, email=None, password=None,
                     **extra_fields):
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email,
                          **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None,
                    **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(
            email,
            password,
            **extra_fields
        )

    def create_superuser(self, email=None, password=None,
                         **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_2FA_required', False)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(
            email,
            password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model derived from AbstractBaseUser
    """
    email = CustomEmailField(('email address'),
                             help_text=('Required. Valid email address '
                                         'of the user'), unique=True)
    first_name = models.CharField(('first name'), max_length=100, blank=True)
    last_name = models.CharField(('last name'), max_length=100, blank=True)
    date_joined = models.DateTimeField(('date joined'), default=timezone.now,
                                       blank=True)
    is_active = models.BooleanField(('active'), help_text=(
        'Designates whether this user should be treated as active. '
        'Unselect this instead of deleting accounts.'
    ), default=True)
    is_staff = models.BooleanField(('staff'), help_text=(
        'Designates whether the user can log into this admin site.'),
                                   default=False)
    is_2FA_required = models.BooleanField(('2FA required'),
                                          help_text=
                                          ('Designates whether '
                                            'the 2FA is enabled or not.'),
                                          default=True)
    last_password_changed = models.DateTimeField(('last password change'), null=True, blank=True, default=None)
    objects = UserManager()

    USERNAME_FIELD = 'email'

    class Meta:
        verbose_name = ('user')
        verbose_name_plural = ('users')

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """

        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """
        Returns the short name for the user.
        """
        return self.first_name

    def save(self, *args, **kwargs):
        """
        Save method
        """
        super(User, self).save(*args, **kwargs)


class BaseProfile(models.Model):
    """
    Common fields shared by BOTH Buyers and Businesses.
    We use 'abstract = True' so this doesn't create its own table.
    """
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='profiles/avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    is_active = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class BuyerProfile(BaseProfile):
    """Specific data for customers."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='buyer_profile'
    )
    default_shipping_address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    favorite_categories = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Buyer: {self.user.email}"

class BusinessProfile(BaseProfile):
    """Specific data for Merchants."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business_profile'
    )
    store_name = models.CharField(max_length=255, unique=True)
    business_address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Store: {self.store_name} ({self.user.email})"