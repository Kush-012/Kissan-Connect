from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import Farmer, Crop, Buyer, PurchaseEnquiry


# ── Authentication Forms ─────────────────────────────────────────────────────

class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Enter username', 'class': 'form-input'}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter email', 'class': 'form-input'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class': 'form-input'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm password', 'class': 'form-input'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords do not match.")
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)

        return cleaned_data


# ── Farmer Forms ─────────────────────────────────────────────────────────────

class FarmerForm(forms.ModelForm):
    class Meta:
        model = Farmer
        fields = ['name', 'email', 'phone', 'state', 'district', 'farm_size']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'state': forms.TextInput(attrs={'placeholder': 'State (e.g. Punjab, Maharashtra)'}),
            'district': forms.TextInput(attrs={'placeholder': 'District (e.g. Amritsar, Pune)'}),
            'farm_size': forms.NumberInput(attrs={'placeholder': 'Size in acres', 'step': '0.01'}),
        }


# ── Crop Forms ────────────────────────────────────────────────────────────────

class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ['farmer', 'name', 'season', 'area_planted', 'expected_yield', 'expected_price', 'harvest_date']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Crop name'}),
            'area_planted': forms.NumberInput(attrs={'placeholder': 'Area in acres', 'step': '0.01'}),
            'expected_yield': forms.NumberInput(attrs={'placeholder': 'Yield in quintals', 'step': '0.01'}),
            'expected_price': forms.NumberInput(attrs={'placeholder': 'Expected price per quintal in INR', 'step': '0.01', 'min': '0'}),
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
        }


# ── Buyer Forms (Operator-managed) ────────────────────────────────────────────

class BuyerForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = ['name', 'email', 'phone', 'location', 'preferred_crops', 'budget']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Full name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'location': forms.TextInput(attrs={'placeholder': 'Location / City'}),
            'preferred_crops': forms.Textarea(attrs={'placeholder': 'e.g. Wheat, Rice, Maize', 'rows': 3}),
            'budget': forms.NumberInput(attrs={'placeholder': 'Budget in INR', 'step': '0.01'}),
        }


# ── Buyer Self-Profile Form ───────────────────────────────────────────────────

class BuyerProfileForm(forms.ModelForm):
    class Meta:
        model = Buyer
        fields = ['name', 'phone', 'location', 'preferred_crops', 'budget']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Trading / Business / Personal Name'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number'}),
            'location': forms.TextInput(attrs={'placeholder': 'City, State'}),
            'preferred_crops': forms.Textarea(attrs={'placeholder': 'e.g. Wheat, Basmati Rice, Mustard, Cotton', 'rows': 3}),
            'budget': forms.NumberInput(attrs={'placeholder': 'Procurement budget in INR', 'step': '0.01'}),
        }


# ── Operator Profile Form ─────────────────────────────────────────────────────

class OperatorProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


# ── Purchase Enquiry Forms ────────────────────────────────────────────────────

class PurchaseEnquiryForm(forms.ModelForm):
    class Meta:
        model = PurchaseEnquiry
        fields = ['required_quantity', 'quantity_unit', 'offered_price_per_quintal', 'message']
        widgets = {
            'required_quantity': forms.NumberInput(attrs={'placeholder': 'Enter required amount', 'step': '0.01', 'min': '0.01'}),
            'quantity_unit': forms.Select(attrs={'class': 'form-select'}),
            'offered_price_per_quintal': forms.NumberInput(attrs={'placeholder': 'Price offered per quintal in INR', 'step': '0.01', 'min': '1'}),
            'message': forms.Textarea(attrs={'placeholder': 'Additional specifications, delivery preferences, or questions for the farmer/operator...', 'rows': 3}),
        }


class EnquiryStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = PurchaseEnquiry
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
