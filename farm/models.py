from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('operator', 'Operator'),
        ('buyer', 'Buyer'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_operator(self):
        return self.role == 'operator' or self.user.is_superuser or self.user.is_staff

    @property
    def is_buyer(self):
        return self.role == 'buyer' and not (self.user.is_superuser or self.user.is_staff)


class Farmer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    state = models.CharField(max_length=100, default='', help_text="State")
    district = models.CharField(max_length=100, default='', help_text="District")
    location = models.CharField(max_length=200, blank=True, default='', help_text="Village or locality (optional)")
    farm_size = models.DecimalField(max_digits=10, decimal_places=2, help_text="Size in acres")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.location:
            parts = [p for p in [self.district, self.state] if p]
            self.location = ", ".join(parts)
        super().save(*args, **kwargs)

    @property
    def display_location(self):
        parts = [p for p in [self.district, self.state] if p]
        return ", ".join(parts) if parts else self.location

    class Meta:
        ordering = ['-created_at']


class Crop(models.Model):
    SEASON_CHOICES = [
        ('kharif', 'Kharif'),
        ('rabi', 'Rabi'),
        ('zaid', 'Zaid'),
        ('annual', 'Annual'),
    ]

    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=200)
    season = models.CharField(max_length=20, choices=SEASON_CHOICES)
    area_planted = models.DecimalField(max_digits=10, decimal_places=2, help_text="Area in acres")
    expected_yield = models.DecimalField(max_digits=10, decimal_places=2, help_text="Yield in quintals")
    expected_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Expected purchase price in INR per quintal")
    harvest_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.farmer.name})"

    class Meta:
        ordering = ['-created_at']


class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='buyer_profile')
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=200, blank=True)
    preferred_crops = models.TextField(help_text="Comma-separated list of crops", blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, help_text="Budget in INR", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']


class PurchaseEnquiry(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]

    UNIT_CHOICES = [
        ('Quintal', 'Quintal'),
        ('Ton', 'Ton'),
        ('Kg', 'Kg'),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchase_enquiries')
    farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='purchase_enquiries')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='purchase_enquiries')
    required_quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Quantity required")
    quantity_unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='Quintal')
    offered_price_per_quintal = models.DecimalField(max_digits=10, decimal_places=2, help_text="Offered price in INR per quintal")
    message = models.TextField(blank=True, help_text="Specifications or questions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Enquiry #{self.pk} - {self.crop.name} by {self.buyer.username} ({self.get_status_display()})"

    class Meta:
        ordering = ['-created_at']


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        default_role = 'operator' if (instance.is_superuser or instance.is_staff) else 'buyer'
        UserProfile.objects.get_or_create(user=instance, defaults={'role': default_role})
