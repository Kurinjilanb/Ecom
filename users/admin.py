from admin_confirm.admin import AdminConfirmMixin
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import (Group as AuthGroup,
                                        Permission as AuthPermission)

from users.models import BusinessProfile

User = get_user_model()

class BusinessProfileInline(admin.StackedInline):
    model = BusinessProfile
    can_delete = False
    verbose_name_plural = 'Business/Merchant Profile'

class CustomUserAdmin(AdminConfirmMixin, UserAdmin):
    """Define admin model for custom User model."""

    inlines = (BusinessProfileInline,)

    list_display = ('email', 'first_name', 'last_name', 'is_staff',
                    'is_superuser', 'is_2FA_required')
    search_fields = ('email', 'first_name', 'last_name')

    ordering = ('email',)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser:
            self.fieldsets = (
                (None, {'fields': ('email', 'password')}),
                (('Personal info'), {'fields': ('first_name', 'last_name',)}),
                (('Permissions'), {'fields': ('is_active', 'is_staff',
                                               'is_superuser',
                                               'is_2FA_required',
                                               'groups', 'user_permissions')}),
                (('Important dates'),
                 {'fields': (
                     'last_login', 'date_joined', 'last_password_changed')}),
            )
            self.add_fieldsets = (
                (None, {
                    'classes': ('wide',),
                    'fields': ('email', 'password1', 'password2', 'is_active',
                               'is_staff', 'is_superuser', 'is_2FA_required'),
                }),
            )

        else:
            if not obj:
                self.add_fieldsets = (
                    (None, {
                        'classes': ('wide',),
                        'fields': ('email', 'password1', 'password2',
                                   'is_staff', 'first_name', 'last_name'),
                    }),
                )
            else:
                self.fieldsets = (
                    (None, {'fields': ('email', 'password', 'is_staff')}),
                    (('Personal info'), {'fields': ('first_name', 'last_name',)})
                )
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            self.readonly_fields = ('date_joined', 'last_login',
                                    'is_superuser', 'is_active',
                                    'last_password_changed',)
        else:
            self.readonly_fields = ('date_joined',)
        return self.readonly_fields


    def get_queryset(self, request):
            return super().get_queryset(request)

    def get_model_perms(self, request):
        if not request.user.is_superuser:
            return {}
        else:
            return super().get_model_perms(request)


class Group(AuthGroup):
    """
    Proxy model for Django Contrib Groups
    """

    class Meta:
        proxy = True
        verbose_name = ('group')
        verbose_name_plural = ('groups')


class Permission(AuthPermission):
    """
    Proxy model for Django Contrib Permissions
    """

    class Meta:
        proxy = True
        verbose_name = ('permission')
        verbose_name_plural = ('permissions')


class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'user', 'is_verified', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('store_name', 'user__email')

    # This adds a dropdown action in the Admin list view
    actions = ['make_verified', 'remove_verification']

    @admin.action(description='Verify selected merchants')
    def make_verified(self, request, queryset):
        queryset.update(is_verified=True)
        self.message_user(request, "Selected merchants have been verified.")

    @admin.action(description='Unverify selected merchants')
    def remove_verification(self, request, queryset):
        queryset.update(is_verified=False)
        self.message_user(request,
            "Verification removed from selected merchants.")


admin.site.unregister(AuthGroup)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Permission)
admin.site.register(BusinessProfile, BusinessProfileAdmin)

