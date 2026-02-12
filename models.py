from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator

class Categories(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        
    def __str__(self):
        return self.name

class Item(models.Model):
    # Remove any explicit item_id field - let Django handle the primary key
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    photo = models.ImageField(upload_to='media/images', blank=True, null=True)
    desc = models.TextField(blank=True)
    times_purchased = models.PositiveIntegerField(default=0)
    last_interacted = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(
        'Categories',  # Use string reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

class CartItem(models.Model):
    STATUS_CHOICES = (
        ('in_cart', 'In Cart'),
        ('ordered', 'Ordered'),
        ('shipped', 'Shipped'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cart_items')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='in_carts')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_cart')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # Made nullable
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # Made nullable
    
    class Meta:
        unique_together = ['user', 'item', 'status']
        
    def __str__(self):
        return f"{self.quantity}x {self.item.name} ({self.status})"
    
    @property
    def total_price(self):
        return self.item.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    items = models.ManyToManyField(CartItem)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_address = models.TextField(blank=True)  # Made optional
    phone = models.CharField(max_length=20, blank=True)  # Made optional
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)  # Made nullable
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)  # Made nullable
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class UserInteraction(models.Model):
    INTERACTION_TYPES = (
        ('view', 'View'),
        ('wishlist', 'Wishlist'),
        ('add_to_cart', 'Add to Cart'),
        ('remove_from_cart', 'Remove from Cart'),
        ('purchase', 'Purchase'),
        ('review', 'Review'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interactions')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='interactions')
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'item', 'interaction_type']),
            models.Index(fields=['timestamp']),
        ]
        
    def __str__(self):
        return f"{self.user}: {self.interaction_type} {self.item}"

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='recommended_to')
    score = models.FloatField(validators=[MinValueValidator(0.0)])
    algorithm_version = models.CharField(max_length=50, default='v1.0')
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'item']
        ordering = ['-score']
        
    def __str__(self):
        return f"Rec #{self.id}: {self.user} -> {self.item} ({self.score:.2f})"