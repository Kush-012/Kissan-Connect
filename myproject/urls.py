from django.contrib import admin
from django.urls import path, include
from farm import views as farm_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Safe Google login interceptor (prevents DoesNotExist crash if app not created)
    path('accounts/google/login/', farm_views.google_login_wrapper, name='google_login'),
    # Route allauth logout through our clean logout handler to delete all cookies
    path('accounts/logout/', farm_views.logout_view, name='account_logout'),
    # allauth URLs (includes Google OAuth callback)
    path('accounts/', include('allauth.urls')),
    # Farm app (includes login/register/logout + all CRUD + Role based dashboards)
    path('', include('farm.urls')),
]

handler403 = 'farm.views.custom_permission_denied_view'
