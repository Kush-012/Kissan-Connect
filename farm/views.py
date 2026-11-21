from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Avg, Max, Min, Count

from .models import Farmer, Crop, Buyer, PurchaseEnquiry, UserProfile
from .forms import (
    RegisterForm, FarmerForm, CropForm, BuyerForm,
    BuyerProfileForm, OperatorProfileForm, PurchaseEnquiryForm, EnquiryStatusUpdateForm
)
from .services import fetch_mandi_prices
from .decorators import operator_required, buyer_required, get_user_profile


# ══════════════════════════════════════════════════════════════════════════════
#  Authentication Views
# ══════════════════════════════════════════════════════════════════════════════

def register_view(request):
    """
    User registration. All newly registered users are assigned the Buyer role.
    Operator accounts can only be created or assigned by the administrator.
    """
    if request.user.is_authenticated:
        return redirect('home')

    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            from django.contrib.auth.models import User
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
            )
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'buyer'})
            profile.role = 'buyer'
            profile.save()

            # Create an associated Buyer profile for this user
            Buyer.objects.get_or_create(
                user=user,
                defaults={
                    'name': user.username,
                    'email': user.email,
                    'phone': '',
                    'location': '',
                    'preferred_crops': '',
                    'budget': 0,
                }
            )

            messages.success(request, "Account created successfully as a Buyer! Please log in.")
            return redirect('login')

    return render(request, 'farm/register.html', {'form': form})


def login_view(request):
    """
    Manual login. Redirects users directly to Home where navigation reflects their role.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Allow login with email as well
        from django.contrib.auth.models import User
        if '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                username = user_obj.username
            except User.DoesNotExist:
                pass

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")

    return render(request, 'farm/login.html')


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Flushes session whenever user logs out from anywhere (including Django Admin & allauth)."""
    if request and hasattr(request, 'session'):
        try:
            request.session.flush()
        except Exception:
            pass


def logout_view(request):
    """
    Logout view that cleanly logs out the user, flushes the session,
    and explicitly deletes session and authentication cookies so that
    no stale admin or buyer session remains.
    Handles both POST and GET to ensure user is always logged out.
    """
    logout(request)
    try:
        request.session.flush()
    except Exception:
        pass

    response = redirect('login')
    session_cookie = getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')
    csrf_cookie = getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken')

    # Explicitly delete session, CSRF, and message cookies from client browser
    response.delete_cookie(session_cookie, path='/')
    response.delete_cookie(csrf_cookie, path='/')
    response.delete_cookie('messages', path='/')

    # Prevent browser caching of previous authenticated pages in browser history
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    messages.success(request, "You have been logged out successfully.")
    return response


def google_login_wrapper(request):
    """
    Safely handles Google login to prevent DoesNotExist crashes
    when Google OAuth credentials (Client ID & Secret) have not been configured yet.
    """
    from allauth.socialaccount.models import SocialApp
    if not SocialApp.objects.filter(provider='google').exists():
        messages.error(
            request,
            "Google Login is not configured yet! Please add your Google Client ID and Secret in Django Admin (Admin > Social Applications > Add)."
        )
        return redirect('login')

    from allauth.socialaccount.providers.google.views import oauth2_login
    return oauth2_login(request)


# ══════════════════════════════════════════════════════════════════════════════
#  Home & Role-Based Dashboards
# ══════════════════════════════════════════════════════════════════════════════

def home_view(request):
    """
    Public and member Home page for Kisan Connect.
    Presents platform overview, crop offerings, and live mandi highlights
    without treating the view as an administrative dashboard.
    """
    recent_crops = Crop.objects.select_related('farmer').order_by('-created_at')[:6]
    total_farmers = Farmer.objects.count()
    total_crops = Crop.objects.count()
    total_buyers = Buyer.objects.count()

    is_operator = False
    is_buyer = False
    if request.user.is_authenticated:
        profile = get_user_profile(request.user)
        is_operator = request.user.is_superuser or request.user.is_staff or profile.role == 'operator'
        is_buyer = profile.role == 'buyer' and not is_operator

    return render(request, 'farm/home.html', {
        'recent_crops': recent_crops,
        'total_farmers': total_farmers,
        'total_crops': total_crops,
        'total_buyers': total_buyers,
        'is_operator': is_operator,
        'is_buyer': is_buyer,
    })


def dashboard_redirect(request):
    """
    Clean redirect: The modernized Homepage is the central landing page for all users.
    """
    return redirect('home')


# ══════════════════════════════════════════════════════════════════════════════
#  Farmer CRUD (Operator Only)
# ══════════════════════════════════════════════════════════════════════════════

@operator_required
def farmer_list(request):
    q = request.GET.get('q', '').strip()
    farmers = Farmer.objects.all()
    if q:
        farmers = farmers.filter(
            Q(name__icontains=q) |
            Q(district__icontains=q) |
            Q(state__icontains=q) |
            Q(location__icontains=q) |
            Q(email__icontains=q)
        )
    return render(request, 'farm/farmer_list.html', {'farmers': farmers, 'q': q})


@operator_required
def farmer_create(request):
    form = FarmerForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Farmer added successfully.")
        return redirect('farmer_list')
    return render(request, 'farm/farmer_form.html', {'form': form, 'title': 'Add Farmer'})


@operator_required
def farmer_detail(request, pk):
    farmer = get_object_or_404(Farmer, pk=pk)
    crops = farmer.crops.all()
    return render(request, 'farm/farmer_detail.html', {'farmer': farmer, 'crops': crops})


@operator_required
def farmer_update(request, pk):
    farmer = get_object_or_404(Farmer, pk=pk)
    form = FarmerForm(request.POST or None, instance=farmer)
    if form.is_valid():
        form.save()
        messages.success(request, "Farmer updated successfully.")
        return redirect('farmer_list')
    return render(request, 'farm/farmer_form.html', {'form': form, 'title': 'Edit Farmer', 'farmer': farmer})


@operator_required
def farmer_delete(request, pk):
    farmer = get_object_or_404(Farmer, pk=pk)
    if request.method == 'POST':
        farmer.delete()
        messages.success(request, "Farmer deleted.")
        return redirect('farmer_list')
    return render(request, 'farm/confirm_delete.html', {'object': farmer, 'object_type': 'Farmer'})


# ══════════════════════════════════════════════════════════════════════════════
#  Crop CRUD (Operator Only)
# ══════════════════════════════════════════════════════════════════════════════

@operator_required
def crop_list(request):
    q = request.GET.get('q', '')
    season = request.GET.get('season', '')
    crops = Crop.objects.select_related('farmer').prefetch_related('purchase_enquiries').all()
    if q:
        crops = crops.filter(Q(name__icontains=q) | Q(farmer__name__icontains=q))
    if season:
        crops = crops.filter(season=season)

    recent_enquiries = PurchaseEnquiry.objects.select_related('buyer', 'crop', 'farmer').order_by('-created_at')[:8]
    pending_enquiries_count = PurchaseEnquiry.objects.filter(status='pending').count()

    return render(request, 'farm/crop_list.html', {
        'crops': crops,
        'q': q,
        'season': season,
        'season_choices': Crop.SEASON_CHOICES,
        'recent_enquiries': recent_enquiries,
        'pending_enquiries_count': pending_enquiries_count,
        'total_enquiries_count': PurchaseEnquiry.objects.count(),
    })


@operator_required
def crop_create(request):
    form = CropForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Crop listing added.")
        return redirect('crop_list')
    return render(request, 'farm/crop_form.html', {'form': form, 'title': 'Add Crop'})


@operator_required
def crop_detail(request, pk):
    crop = get_object_or_404(Crop, pk=pk)
    enquiries = PurchaseEnquiry.objects.filter(crop=crop).select_related('buyer').order_by('-created_at')
    return render(request, 'farm/crop_detail.html', {
        'crop': crop,
        'enquiries': enquiries,
    })


@operator_required
def crop_update(request, pk):
    crop = get_object_or_404(Crop, pk=pk)
    form = CropForm(request.POST or None, instance=crop)
    if form.is_valid():
        form.save()
        messages.success(request, "Crop updated.")
        return redirect('crop_list')
    return render(request, 'farm/crop_form.html', {'form': form, 'title': 'Edit Crop', 'crop': crop})


@operator_required
def crop_delete(request, pk):
    crop = get_object_or_404(Crop, pk=pk)
    if request.method == 'POST':
        crop.delete()
        messages.success(request, "Crop deleted.")
        return redirect('crop_list')
    return render(request, 'farm/confirm_delete.html', {'object': crop, 'object_type': 'Crop'})


# ══════════════════════════════════════════════════════════════════════════════
#  Buyer CRUD (Operator Only)
# ══════════════════════════════════════════════════════════════════════════════

@operator_required
def buyer_list(request):
    q = request.GET.get('q', '')
    buyers = Buyer.objects.all()
    if q:
        buyers = buyers.filter(
            Q(name__icontains=q) | Q(location__icontains=q) | Q(preferred_crops__icontains=q)
        )
    return render(request, 'farm/buyer_list.html', {'buyers': buyers, 'q': q})


@operator_required
def buyer_create(request):
    form = BuyerForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Buyer record added.")
        return redirect('buyer_list')
    return render(request, 'farm/buyer_form.html', {'form': form, 'title': 'Add Buyer'})


@operator_required
def buyer_detail(request, pk):
    buyer = get_object_or_404(Buyer, pk=pk)
    return render(request, 'farm/buyer_detail.html', {'buyer': buyer})


@operator_required
def buyer_update(request, pk):
    buyer = get_object_or_404(Buyer, pk=pk)
    form = BuyerForm(request.POST or None, instance=buyer)
    if form.is_valid():
        form.save()
        messages.success(request, "Buyer record updated.")
        return redirect('buyer_list')
    return render(request, 'farm/buyer_form.html', {'form': form, 'title': 'Edit Buyer', 'buyer': buyer})


@operator_required
def buyer_delete(request, pk):
    buyer = get_object_or_404(Buyer, pk=pk)
    if request.method == 'POST':
        buyer.delete()
        messages.success(request, "Buyer record deleted.")
        return redirect('buyer_list')
    return render(request, 'farm/confirm_delete.html', {'object': buyer, 'object_type': 'Buyer'})


# ══════════════════════════════════════════════════════════════════════════════
#  Buyer Crop Browsing & Purchase Enquiry Submission (Buyer & Operator)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def buyer_crop_list(request):
    """
    Allows buyers (and operators) to browse available crops, search by name,
    state, district, and season, and view yields, expected price, harvest dates and initiate enquiries.
    """
    q = request.GET.get('q', '').strip()
    season = request.GET.get('season', '').strip()
    state = request.GET.get('state', '').strip()
    district = request.GET.get('district', '').strip()

    crops = Crop.objects.select_related('farmer').all()

    if q:
        crops = crops.filter(Q(name__icontains=q) | Q(farmer__name__icontains=q))
    if season:
        crops = crops.filter(season=season)
    if state:
        crops = crops.filter(farmer__state__icontains=state)
    if district:
        crops = crops.filter(farmer__district__icontains=district)

    states = Farmer.objects.exclude(state='').values_list('state', flat=True).distinct().order_by('state')
    districts = Farmer.objects.exclude(district='').values_list('district', flat=True).distinct().order_by('district')

    return render(request, 'farm/buyer_crop_list.html', {
        'crops': crops,
        'q': q,
        'season': season,
        'state': state,
        'district': district,
        'season_choices': Crop.SEASON_CHOICES,
        'states': states,
        'districts': districts,
    })


@buyer_required
def submit_enquiry(request, crop_id):
    """
    Buyer submits a purchase enquiry for a specific crop.
    """
    crop = get_object_or_404(Crop.objects.select_related('farmer'), pk=crop_id)

    if request.method == 'POST':
        form = PurchaseEnquiryForm(request.POST)
        if form.is_valid():
            enquiry = form.save(commit=False)
            enquiry.buyer = request.user
            enquiry.farmer = crop.farmer
            enquiry.crop = crop
            enquiry.status = 'pending'
            enquiry.save()
            messages.success(request, f"Your enquiry for {crop.name} has been submitted successfully!")
            return redirect('buyer_enquiry_list')
    else:
        # Pre-fill offered price with farmer's expected price if available
        initial_data = {}
        if crop.expected_price > 0:
            initial_data['offered_price_per_quintal'] = crop.expected_price
        form = PurchaseEnquiryForm(initial=initial_data)

    return render(request, 'farm/buyer_enquiry_form.html', {
        'crop': crop,
        'farmer': crop.farmer,
        'form': form,
    })


@buyer_required
def buyer_enquiry_list(request):
    """
    Buyers view their own submitted purchase enquiries.
    """
    status_filter = request.GET.get('status', '').strip()
    enquiries = PurchaseEnquiry.objects.filter(buyer=request.user).select_related('crop', 'farmer')

    if status_filter:
        enquiries = enquiries.filter(status=status_filter)

    return render(request, 'farm/buyer_enquiry_list.html', {
        'enquiries': enquiries,
        'status_filter': status_filter,
        'status_choices': PurchaseEnquiry.STATUS_CHOICES,
    })


@buyer_required
def buyer_enquiry_detail(request, pk):
    """
    Buyer views their own enquiry details. Prevents accessing other buyers' enquiries.
    """
    enquiry = get_object_or_404(PurchaseEnquiry.objects.select_related('crop', 'farmer', 'buyer'), pk=pk)
    if enquiry.buyer != request.user and not request.user.is_superuser:
        raise PermissionDenied("You are not authorized to view another buyer's enquiry.")

    return render(request, 'farm/buyer_enquiry_detail.html', {'enquiry': enquiry})


# ══════════════════════════════════════════════════════════════════════════════
#  Operator Enquiry Management
# ══════════════════════════════════════════════════════════════════════════════

@operator_required
def operator_enquiry_list(request):
    """
    Operator views and manages all purchase enquiries across the platform.
    """
    status_filter = request.GET.get('status', '').strip()
    q = request.GET.get('q', '').strip()

    enquiries = PurchaseEnquiry.objects.select_related('buyer', 'buyer__buyer_profile', 'crop', 'farmer').all()

    if status_filter:
        enquiries = enquiries.filter(status=status_filter)
    if q:
        enquiries = enquiries.filter(
            Q(crop__name__icontains=q) |
            Q(buyer__username__icontains=q) |
            Q(buyer__email__icontains=q) |
            Q(farmer__name__icontains=q)
        )

    return render(request, 'farm/operator_enquiry_list.html', {
        'enquiries': enquiries,
        'status_filter': status_filter,
        'q': q,
        'status_choices': PurchaseEnquiry.STATUS_CHOICES,
        'total_count': PurchaseEnquiry.objects.count(),
        'pending_count': PurchaseEnquiry.objects.filter(status='pending').count(),
    })


@operator_required
def operator_enquiry_detail(request, pk):
    """
    Operator views full enquiry details and updates its status.
    """
    enquiry = get_object_or_404(PurchaseEnquiry.objects.select_related('buyer', 'crop', 'farmer'), pk=pk)
    form = EnquiryStatusUpdateForm(instance=enquiry)

    if request.method == 'POST':
        form = EnquiryStatusUpdateForm(request.POST, instance=enquiry)
        if form.is_valid():
            form.save()
            messages.success(request, f"Enquiry #{enquiry.pk} status updated to {enquiry.get_status_display()}.")
            return redirect('operator_enquiry_detail', pk=enquiry.pk)

    buyer_profile = Buyer.objects.filter(user=enquiry.buyer).first()

    return render(request, 'farm/operator_enquiry_detail.html', {
        'enquiry': enquiry,
        'buyer_profile': buyer_profile,
        'form': form,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Profile Management (Operator & Buyer)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def profile_dispatch(request):
    """
    Routes to the appropriate profile view based on the user's role.
    """
    profile = get_user_profile(request.user)
    if profile.role == 'buyer' and not (request.user.is_superuser or request.user.is_staff):
        return redirect('buyer_profile')

    # Operator / Administrator Profile
    if request.method == 'POST':
        form = OperatorProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = OperatorProfileForm(instance=request.user)

    return render(request, 'farm/operator_profile.html', {
        'form': form,
        'user': request.user,
        'profile': profile,
    })


@buyer_required
def buyer_profile_view(request):
    """
    Allows a Buyer to view and edit their own trading profile and crop preferences.
    """
    buyer_obj, _ = Buyer.objects.get_or_create(
        user=request.user,
        defaults={
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
            'phone': '',
            'location': '',
            'preferred_crops': '',
            'budget': 0,
        }
    )

    if request.method == 'POST':
        form = BuyerProfileForm(request.POST, instance=buyer_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile and crop preferences have been updated successfully.")
            return redirect('buyer_profile')
    else:
        form = BuyerProfileForm(instance=buyer_obj)

    enquiries_count = PurchaseEnquiry.objects.filter(buyer=request.user).count()

    return render(request, 'farm/buyer_profile.html', {
        'form': form,
        'buyer': buyer_obj,
        'enquiries_count': enquiries_count,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  Mandi Prices
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def price_discovery(request):
    """
    Redirects to Market Crop Prices discovery.
    """
    return redirect('market_crop_prices')


@login_required
def market_crop_prices(request):
    """
    Market Crop Prices.
    Wholesale APMC market rates across agricultural trading centers.
    Supports separate filtering by Commodity, State, and District.
    """
    commodity = request.GET.get('commodity', '').strip()
    state = request.GET.get('state', '').strip()
    district = request.GET.get('district', '').strip()
    page = int(request.GET.get('page', 1))
    limit = 20
    offset = (page - 1) * limit

    result = fetch_mandi_prices(
        commodity=commodity if commodity else None,
        state=state if state else None,
        district=district if district else None,
        limit=limit,
        offset=offset,
    )

    records = result['records']
    total = result['total']
    error = result['error']
    report_date = records[0].get('arrival_date') if records and records[0].get('arrival_date') else None

    total_pages = max(1, (total + limit - 1) // limit)
    has_next = page < total_pages
    has_prev = page > 1

    return render(request, 'farm/market_crop_prices.html', {
        'records': records,
        'total': total,
        'error': error,
        'report_date': report_date,
        'commodity': commodity,
        'state': state,
        'district': district,
        'page': page,
        'total_pages': total_pages,
        'has_next': has_next,
        'has_prev': has_prev,
        'next_page': page + 1,
        'prev_page': page - 1,
    })


# Backwards compatibility alias
live_mandi_prices = market_crop_prices


import json
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from .chatbot import query_groq_chatbot


@ensure_csrf_cookie
def chatbot_api(request):
    """
    API endpoint for the Kisan Connect Kisan AI Groq-powered chatbot.
    Receives JSON POST with user's message and optional recent history.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required', 'status': 'error'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON body', 'status': 'error'}, status=400)

    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty', 'status': 'error'}, status=400)

    if len(user_message) > 1200:
        user_message = user_message[:1200]

    result = query_groq_chatbot(user_message=user_message, history=history)
    return JsonResponse({
        'reply': result.get('reply', ''),
        'success': result.get('success', False),
    })


def custom_permission_denied_view(request, exception=None):
    """Custom 403 Forbidden handler."""
    return render(request, 'farm/403.html', {'message': str(exception) if exception else 'Access Restricted'}, status=403)

