from django.contrib import admin
from .models import Product, ProductVariant, ProductImage, Category, Color, Size


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)} # Auto-fills slug as you type the name
    # readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent')

    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(CategoryAdmin, self).save_model(request, obj, form,
                                                        change)
        

class SizeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by'] 

    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(SizeAdmin, self).save_model(request, obj, form,
                                                        change)
        
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code']
    search_fields = ['name']
    readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by'] 

    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(ColorAdmin, self).save_model(request, obj, form,
                                                        change)
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by']
    extra = 1 # Shows one empty row by default

    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(ProductVariantInline, self).save_model(request, obj, form,
                                                        change)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by']    
    extra = 1
    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(ProductImageInline, self).save_model(request, obj, form,
                                                        change)
    

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'category', 'is_active', 'created_on']
    list_filter = ['category', 'is_active', 'brand']
    search_fields = ['name', 'code', 'slug']
    prepopulated_fields = {'slug': ('name',)} # Auto-fills slug as you type the name
    inlines = [ProductVariantInline, ProductImageInline]
    readonly_fields = ['created_on', 'modified_on', 'created_by', 'modified_by'] 

    def save_model(self, request, obj, form, change):
        if change:
            obj.modified_by = request.user
        else:
            obj.created_by = request.user
            obj.modified_by = request.user
        super(ProductAdmin, self).save_model(request, obj, form,
                                                        change)


admin.site.register(Category,CategoryAdmin)
admin.site.register(Color, ColorAdmin)
admin.site.register(Size, SizeAdmin)
admin.site.register(Product, ProductAdmin)