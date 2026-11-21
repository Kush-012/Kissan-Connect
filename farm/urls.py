from django.urls import path
from . import views

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ── Home & Profile ────────────────────────────────────────────────────────
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('profile/', views.profile_dispatch, name='profile'),

    # ── Farmers (Operator) ────────────────────────────────────────────────────
    path('farmers/', views.farmer_list, name='farmer_list'),
    path('farmers/new/', views.farmer_create, name='farmer_create'),
    path('farmers/<int:pk>/', views.farmer_detail, name='farmer_detail'),
    path('farmers/<int:pk>/edit/', views.farmer_update, name='farmer_update'),
    path('farmers/<int:pk>/delete/', views.farmer_delete, name='farmer_delete'),

    # ── Crops (Operator CRUD) ─────────────────────────────────────────────────
    path('crops/', views.crop_list, name='crop_list'),
    path('crops/new/', views.crop_create, name='crop_create'),
    path('crops/<int:pk>/', views.crop_detail, name='crop_detail'),
    path('crops/<int:pk>/edit/', views.crop_update, name='crop_update'),
    path('crops/<int:pk>/delete/', views.crop_delete, name='crop_delete'),

    # ── Buyers (Operator CRUD) ────────────────────────────────────────────────
    path('buyers/', views.buyer_list, name='buyer_list'),
    path('buyers/new/', views.buyer_create, name='buyer_create'),
    path('buyers/<int:pk>/', views.buyer_detail, name='buyer_detail'),
    path('buyers/<int:pk>/edit/', views.buyer_update, name='buyer_update'),
    path('buyers/<int:pk>/delete/', views.buyer_delete, name='buyer_delete'),

    # ── Buyer Portal & Crop Browsing ──────────────────────────────────────────
    path('buyer/crops/', views.buyer_crop_list, name='buyer_crop_list'),
    path('buyer/crops/<int:crop_id>/enquiry/', views.submit_enquiry, name='submit_enquiry'),
    path('buyer/enquiries/', views.buyer_enquiry_list, name='buyer_enquiry_list'),
    path('buyer/enquiries/<int:pk>/', views.buyer_enquiry_detail, name='buyer_enquiry_detail'),
    path('buyer/profile/', views.buyer_profile_view, name='buyer_profile'),

    # ── Operator Purchase Enquiry Management ──────────────────────────────────
    path('enquiries/', views.operator_enquiry_list, name='operator_enquiry_list'),
    path('enquiries/<int:pk>/', views.operator_enquiry_detail, name='operator_enquiry_detail'),

    # ── Shared Price Features (Both Roles) ────────────────────────────────────
    path('price-discovery/', views.price_discovery, name='price_discovery'),
    path('market-crop-prices/', views.market_crop_prices, name='market_crop_prices'),
    # Backwards compatibility alias
    path('live-mandi-prices/', views.market_crop_prices, name='live_mandi_prices'),

    # ── Groq AI Chatbot ───────────────────────────────────────────────────────
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),
]
