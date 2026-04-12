from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # App APIs
    path('products/api/v1/', include('product.api.v1.urls')),
    path('auth/api/v1/', include('authenticate.api.v1.urls')),
    path('user/api/v1/', include('users.api.v1.urls')),
    path('cart/api/v1/', include('cart.api.v1.urls')),
]