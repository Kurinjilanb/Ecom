from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserProfileView, BusinessRegistrationView, BuyerRegistrationView

urlpatterns = [
    path('oauth/',
        include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('business-registration/', BusinessRegistrationView.as_view(),
        name='business-registration'),
    path('profile/', BuyerRegistrationView.as_view(), name='buyer-profile'),

]