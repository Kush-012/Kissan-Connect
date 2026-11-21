from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Farmer, Crop, Buyer, PurchaseEnquiry


class CustomUserCreationForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial='operator',
        required=False,
        help_text="Designate user role: Operator has full staff management rights; Buyer has market access."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role') or 'operator'
        if role == 'operator':
            user.is_staff = True
        if commit:
            user.save()
            UserProfile.objects.update_or_create(user=user, defaults={'role': role})
        return user


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Role & Profile'
    fk_name = 'user'
    extra = 0
    max_num = 1


class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'role', 'password1', 'password2'),
        }),
    )
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('profile__role', 'is_staff', 'is_superuser', 'is_active')

    def get_inline_instances(self, request, obj=None):
        # Do not load inlines during initial user creation (prevents UNIQUE constraint conflict with post_save signal)
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

    def get_role(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.get_role_display()
        return "Not Set"
    get_role.short_description = 'Assigned Role'


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at', 'updated_at')
    list_editable = ('role',)
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email')


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'district', 'state', 'farm_size', 'created_at')
    search_fields = ('name', 'email', 'district', 'state', 'phone')
    list_filter = ('state', 'district', 'created_at')


@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ('name', 'farmer', 'season', 'area_planted', 'expected_yield', 'expected_price', 'harvest_date')
    search_fields = ('name', 'farmer__name')
    list_filter = ('season', 'harvest_date')


@admin.register(Buyer)
class BuyerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'location', 'budget', 'user', 'created_at')
    search_fields = ('name', 'email', 'phone', 'location', 'preferred_crops')
    list_filter = ('location', 'created_at')


@admin.register(PurchaseEnquiry)
class PurchaseEnquiryAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'crop', 'farmer', 'required_quantity', 'quantity_unit', 'offered_price_per_quintal', 'status', 'created_at')
    list_filter = ('status', 'quantity_unit', 'created_at')
    search_fields = ('buyer__username', 'buyer__email', 'crop__name', 'farmer__name')
    list_editable = ('status',)
