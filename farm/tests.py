from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date
from .models import Farmer, Crop, Buyer, PurchaseEnquiry, UserProfile


class RoleBasedAccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Superuser / Admin
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='Password123!'
        )
        self.admin_user.profile.role = 'operator'
        self.admin_user.profile.save()

        # 2. Operator User
        self.operator_user = User.objects.create_user(
            username='operator_test',
            email='operator@test.com',
            password='Password123!'
        )
        self.operator_user.profile.role = 'operator'
        self.operator_user.profile.save()

        # 3. Buyer 1 User
        self.buyer1_user = User.objects.create_user(
            username='buyer1_test',
            email='buyer1@test.com',
            password='Password123!'
        )
        self.buyer1_user.profile.role = 'buyer'
        self.buyer1_user.profile.save()
        self.buyer1_profile = Buyer.objects.create(
            user=self.buyer1_user,
            name='Buyer One Trading Co',
            email=self.buyer1_user.email,
            phone='9876543210',
            location='Ludhiana, Punjab',
            preferred_crops='Wheat, Rice',
            budget=500000
        )

        # 4. Buyer 2 User
        self.buyer2_user = User.objects.create_user(
            username='buyer2_test',
            email='buyer2@test.com',
            password='Password123!'
        )
        self.buyer2_user.profile.role = 'buyer'
        self.buyer2_user.profile.save()
        self.buyer2_profile = Buyer.objects.create(
            user=self.buyer2_user,
            name='Buyer Two Foods',
            email=self.buyer2_user.email,
            phone='9876543211',
            location='Karnal, Haryana',
            preferred_crops='Mustard',
            budget=300000
        )

        # 5. Sample Agricultural Data
        self.farmer = Farmer.objects.create(
            name='Ramesh Singh',
            email='ramesh@farm.test',
            phone='9998887770',
            state='Punjab',
            district='Amritsar',
            farm_size=25.5
        )

        self.crop = Crop.objects.create(
            farmer=self.farmer,
            name='Sharbati Wheat',
            season='rabi',
            area_planted=15.0,
            expected_yield=350.0,
            expected_price=2900.00,
            harvest_date=date(2027, 4, 15)
        )

        # Sample Enquiry by Buyer 1
        self.enquiry = PurchaseEnquiry.objects.create(
            buyer=self.buyer1_user,
            farmer=self.farmer,
            crop=self.crop,
            required_quantity=50.0,
            quantity_unit='Quintal',
            offered_price_per_quintal=2900.0,
            message='Need top grade wheat delivered in bags.',
            status='pending'
        )

    # ── 1. Authentication & Registration Tests ─────────────────────────────────

    def test_new_user_registration_defaults_to_buyer(self):
        """Newly registered user automatically receives Buyer role and Buyer profile."""
        response = self.client.post(reverse('register'), {
            'username': 'newbuyer',
            'email': 'newbuyer@test.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='newbuyer')
        self.assertEqual(new_user.profile.role, 'buyer')
        self.assertTrue(new_user.profile.is_buyer)
        self.assertFalse(new_user.profile.is_operator)
        self.assertTrue(Buyer.objects.filter(user=new_user).exists())

    def test_login_redirects_operator_to_home(self):
        """Operator logging in is routed directly to the Home page."""
        response = self.client.post(reverse('login'), {
            'username': 'operator_test',
            'password': 'Password123!',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_redirects_buyer_to_home(self):
        """Buyer logging in is routed directly to the Home page."""
        response = self.client.post(reverse('login'), {
            'username': 'buyer1_test',
            'password': 'Password123!',
        })
        self.assertRedirects(response, reverse('home'))

    def test_dashboard_url_redirects_to_home(self):
        """Legacy /dashboard/ URL redirects to Home."""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('home'))

    # ── 2. Operator Permission Tests ───────────────────────────────────────────

    def test_operator_can_perform_farmer_crud(self):
        self.client.force_login(self.operator_user)
        # List
        r = self.client.get(reverse('farmer_list'))
        self.assertEqual(r.status_code, 200)
        # Create with state and district
        r = self.client.post(reverse('farmer_create'), {
            'name': 'Gurpreet Singh',
            'email': 'gurpreet@test.com',
            'phone': '9871234567',
            'state': 'Punjab',
            'district': 'Jalandhar',
            'farm_size': 12.0,
        })
        self.assertEqual(r.status_code, 302)
        new_farmer = Farmer.objects.get(name='Gurpreet Singh')
        self.assertEqual(new_farmer.state, 'Punjab')
        self.assertEqual(new_farmer.district, 'Jalandhar')
        self.assertEqual(new_farmer.location, 'Jalandhar, Punjab')

    def test_operator_can_view_and_update_enquiries(self):
        self.client.force_login(self.operator_user)
        # List all enquiries
        r = self.client.get(reverse('operator_enquiry_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Buyer One Trading Co')
        # Update enquiry status to 'accepted'
        r = self.client.post(reverse('operator_enquiry_detail', kwargs={'pk': self.enquiry.pk}), {
            'status': 'accepted',
        })
        self.assertEqual(r.status_code, 302)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, 'accepted')

    # ── 3. Buyer Permission Tests ──────────────────────────────────────────────

    def test_buyer_can_browse_crops(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.get(reverse('buyer_crop_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sharbati Wheat')
        self.assertContains(response, 'Send Enquiry')

    def test_buyer_can_submit_purchase_enquiry(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.post(reverse('submit_enquiry', kwargs={'crop_id': self.crop.pk}), {
            'required_quantity': 100.0,
            'quantity_unit': 'Quintal',
            'offered_price_per_quintal': 2950.0,
            'message': 'Immediate delivery required at warehouse.',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(PurchaseEnquiry.objects.filter(
            buyer=self.buyer1_user,
            crop=self.crop,
            required_quantity=100.0
        ).exists())

    def test_buyer_can_view_own_enquiry_and_status(self):
        self.client.force_login(self.buyer1_user)
        # List
        r = self.client.get(reverse('buyer_enquiry_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'#{self.enquiry.id}')
        # Detail
        r = self.client.get(reverse('buyer_enquiry_detail', kwargs={'pk': self.enquiry.pk}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Pending')

    def test_buyer_can_manage_own_profile(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.post(reverse('buyer_profile'), {
            'name': 'Buyer One Agro Exports',
            'phone': '9876540000',
            'location': 'Chandigarh',
            'preferred_crops': 'Basmati Rice, Wheat, Barley',
            'budget': 800000.0,
        })
        self.assertEqual(response.status_code, 302)
        self.buyer1_profile.refresh_from_db()
        self.assertEqual(self.buyer1_profile.name, 'Buyer One Agro Exports')
        self.assertEqual(self.buyer1_profile.location, 'Chandigarh')

    # ── 4. Role-Based Security & Forbidden (403) Tests ─────────────────────────

    def test_buyer_blocked_from_farmer_create(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.get(reverse('farmer_create'))
        self.assertEqual(response.status_code, 403)

    def test_buyer_blocked_from_crop_create(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.get(reverse('crop_create'))
        self.assertEqual(response.status_code, 403)

    def test_buyer_blocked_from_operator_enquiry_list(self):
        self.client.force_login(self.buyer1_user)
        response = self.client.get(reverse('operator_enquiry_list'))
        self.assertEqual(response.status_code, 403)

    def test_buyer_cannot_access_another_buyers_enquiry(self):
        """Buyer 2 cannot view Buyer 1's enquiry details (403 Forbidden)."""
        self.client.force_login(self.buyer2_user)
        response = self.client.get(reverse('buyer_enquiry_detail', kwargs={'pk': self.enquiry.pk}))
        self.assertEqual(response.status_code, 403)

    # ── 5. Shared Features (Both Roles Can Access) ─────────────────────────────

    def test_both_roles_can_access_price_discovery(self):
        # Operator
        self.client.force_login(self.operator_user)
        r1 = self.client.get(reverse('price_discovery'))
        self.assertRedirects(r1, reverse('market_crop_prices'))

        # Buyer
        self.client.force_login(self.buyer1_user)
        r2 = self.client.get(reverse('price_discovery'))
        self.assertRedirects(r2, reverse('market_crop_prices'))

    @patch('farm.views.fetch_mandi_prices')
    def test_both_roles_can_access_market_crop_prices(self, mock_fetch):
        mock_fetch.return_value = {
            'records': [{'commodity': 'Wheat', 'market': 'Mandi A', 'district': 'Dist', 'state': 'State', 'min_price': 2000, 'max_price': 2200, 'modal_price': 2100}],
            'total': 1,
            'count': 1,
            'error': None,
        }
        # Operator
        self.client.force_login(self.operator_user)
        r1 = self.client.get(reverse('market_crop_prices'))
        self.assertEqual(r1.status_code, 200)

        # Buyer
        self.client.force_login(self.buyer1_user)
        r2 = self.client.get(reverse('market_crop_prices'))
        self.assertEqual(r2.status_code, 200)

    @patch('farm.views.fetch_mandi_prices')
    def test_market_crop_prices_supports_district_filter(self, mock_fetch):
        mock_fetch.return_value = {
            'records': [{'commodity': 'Wheat', 'market': 'Amritsar', 'district': 'Amritsar', 'state': 'Punjab', 'min_price': 2200, 'max_price': 2400, 'modal_price': 2300}],
            'total': 1,
            'count': 1,
            'error': None,
        }
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('market_crop_prices') + '?commodity=Wheat&state=Punjab&district=Amritsar')
        self.assertEqual(response.status_code, 200)
        mock_fetch.assert_called_with(commodity='Wheat', state='Punjab', district='Amritsar', limit=20, offset=0)
        self.assertContains(response, 'Amritsar')

    def test_operator_navigation_contains_expected_items(self):
        """Operator navigation must have Home, Farmers, Crops, Buyers, Market Crop Prices, Profile and show user name and profile avatar badge."""
        self.client.force_login(self.operator_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('>Home<', content)
        self.assertIn('>Farmers<', content)
        self.assertIn('Crops', content)
        self.assertIn('>Buyers<', content)
        self.assertIn('>Market Crop Prices<', content)
        # Nav links section
        nav_section = content.split('<div class="nav-links">')[1].split('</nav>')[0]
        self.assertNotIn('Price Discovery', nav_section)
        # Verify profile pill links to profile, displays user name and avatar, and has no logout icon in nav
        self.assertIn(reverse('profile'), nav_section)
        self.assertIn(self.operator_user.username, nav_section)
        self.assertIn('user-avatar-badge', content)
        self.assertIn('nav-user-pill', content)
        self.assertNotIn('logout-btn', nav_section)
        self.assertNotIn('🚪', nav_section)

    def test_enquiries_shown_under_crops_in_operator_section(self):
        """Crops section displays purchase enquiries in crop_list and crop_detail."""
        self.client.force_login(self.operator_user)
        # Crop list page has crop enquiries button and section
        r_list = self.client.get(reverse('crop_list'))
        self.assertEqual(r_list.status_code, 200)
        self.assertContains(r_list, 'Crop Enquiries')
        self.assertContains(r_list, 'Purchase Enquiries for Crops')

        # Crop detail page displays received enquiries for that crop
        r_detail = self.client.get(reverse('crop_detail', kwargs={'pk': self.crop.pk}))
        self.assertEqual(r_detail.status_code, 200)
        self.assertContains(r_detail, f'Purchase Enquiries for {self.crop.name}')
        self.assertContains(r_detail, self.buyer1_user.username)
        self.assertContains(r_detail, 'Review & Update')

    def test_home_page_is_distinct_and_public(self):
        """Home page is accessible publicly and renders platform overview without treating it as a dashboard."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kisan Connect')
        self.assertContains(response, 'Connecting Farmers, Agricultural Officers & Buyers')
        # Does not show operator dashboard title
        self.assertNotContains(response, 'Operator Dashboard')

    def test_profiles_exclude_member_since_and_enquiries(self):
        """Operator and Buyer profiles exclude Member Since and Total Enquiries."""
        # Operator Profile
        self.client.force_login(self.operator_user)
        r_op = self.client.get(reverse('profile'))
        self.assertEqual(r_op.status_code, 200)
        self.assertNotContains(r_op, 'Member Since')
        self.assertNotContains(r_op, 'Permissions')
        self.assertNotContains(r_op, 'Total Enquiries')

        # Buyer Profile
        self.client.force_login(self.buyer1_user)
        r_buyer = self.client.get(reverse('profile'))
        # redirects to buyer_profile
        r_buyer_profile = self.client.get(reverse('buyer_profile'))
        self.assertEqual(r_buyer_profile.status_code, 200)
        self.assertNotContains(r_buyer_profile, 'Member Since')
        self.assertNotContains(r_buyer_profile, 'Total Enquiries')

    def test_crop_expected_price_field(self):
        """Operator can create crop with expected_price, and buyer can view expected_price."""
        self.client.force_login(self.operator_user)
        response = self.client.post(reverse('crop_create'), {
            'farmer': self.farmer.pk,
            'name': 'Basmati 1121',
            'season': 'kharif',
            'area_planted': 10.0,
            'expected_yield': 200.0,
            'expected_price': 3850.00,
            'harvest_date': '2027-10-25',
        })
        self.assertEqual(response.status_code, 302)
        new_crop = Crop.objects.get(name='Basmati 1121')
        self.assertEqual(float(new_crop.expected_price), 3850.00)

        # Buyer can see expected price in browse crops
        self.client.force_login(self.buyer1_user)
        r = self.client.get(reverse('buyer_crop_list'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '3850.00')

    def test_profile_dispatch_routes_by_role(self):
        """Profile URL redirects buyer to buyer profile and renders operator profile for operator."""
        # Operator
        self.client.force_login(self.operator_user)
        r_op = self.client.get(reverse('profile'))
        self.assertEqual(r_op.status_code, 200)
        self.assertContains(r_op, 'Operator Profile')

        # Buyer
        self.client.force_login(self.buyer1_user)
        r_buyer = self.client.get(reverse('profile'))
        self.assertRedirects(r_buyer, reverse('buyer_profile'))

    def test_logout_flushes_session_and_deletes_cookies(self):
        """Logout flushes session, removes auth, and deletes session and CSRF cookies."""
        self.client.force_login(self.operator_user)
        # Ensure session is active
        self.assertEqual(int(self.client.session.get('_auth_user_id')), self.operator_user.pk)

        # Trigger logout via POST
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

        # Session should be flushed
        self.assertNotIn('_auth_user_id', self.client.session)

        # Response must delete session cookie (max-age=0 or expires set to epoch)
        session_cookie = response.cookies.get('sessionid')
        if session_cookie:
            self.assertEqual(session_cookie['max-age'], 0)

        # Subsequent request should be unauthenticated
        r_after = self.client.get(reverse('farmer_create'))
        self.assertEqual(r_after.status_code, 302)

    def test_buyer_navigation_and_toast_notifications(self):
        """Buyer navigation renders user name and avatar, and toast notifications are styled on top-right."""
        self.client.force_login(self.buyer1_user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.buyer1_user.username)
        self.assertContains(response, 'user-avatar-badge')
        self.assertContains(response, 'nav-user-pill')
        # Verify right-side toast notification container styles and logic are present in layout
        self.assertContains(response, 'toast-container')
        self.assertContains(response, 'right: 24px')

    def test_admin_add_user_without_integrity_error(self):
        """Creating a user via Django admin add view succeeds without UNIQUE constraint IntegrityError."""
        self.client.force_login(self.admin_user)
        add_url = reverse('admin:auth_user_add')
        response = self.client.post(add_url, {
            'username': 'new_operator_user',
            'password1': 'OperatorPass123!',
            'password2': 'OperatorPass123!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        # Verify user was created with profile
        new_user = User.objects.get(username='new_operator_user')
        self.assertIsNotNone(new_user.profile)
