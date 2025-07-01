from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.validators import MinValueValidator
from core.models import TimeStampedModel
from recipes.models import Grain, Hop, Yeast

class Supplier(TimeStampedModel):
    """
    Suppliers for ingredients
    """
    name = models.CharField(max_length=100)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class InventoryItem(TimeStampedModel):
    """
    Items in inventory with current stock and pricing
    """
    INGREDIENT_TYPES = [
        ('grain', 'Grain/Malt'),
        ('hop', 'Hop'),
        ('yeast', 'Yeast'),
        ('other', 'Other'),
    ]
    
    UNITS = [
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
        ('lb', 'Pounds'),
        ('oz', 'Ounces'),
        ('unit', 'Units/Packages'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ingredient_type = models.CharField(max_length=20, choices=INGREDIENT_TYPES)
    
    # Generic foreign keys to different ingredient types
    ingredient_id = models.PositiveIntegerField()
    ingredient_name = models.CharField(max_length=200)  # Denormalized for easier querying
    
    # Stock information
    current_stock = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=10, choices=UNITS, default='kg')
    
    # Pricing
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cost_per_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Purchase information
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    last_purchase_date = models.DateField(null=True, blank=True)
    last_purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Inventory management
    minimum_stock = models.FloatField(default=0.0, help_text="Minimum stock level for alerts")
    location = models.CharField(max_length=100, blank=True, help_text="Storage location")
    
    # Expiration
    expiry_date = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['ingredient_name']
        unique_together = ['user', 'ingredient_type', 'ingredient_id']
    
    def __str__(self):
        return f"{self.ingredient_name} ({self.current_stock} {self.unit})"
    
    def get_absolute_url(self):
        return reverse('inventory_detail', kwargs={'pk': self.pk})
    
    @property
    def is_low_stock(self):
        """Check if item is below minimum stock level"""
        return self.current_stock <= self.minimum_stock
    
    @property
    def is_expired(self):
        """Check if item is expired"""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
    
    @property
    def ingredient_object(self):
        """Get the actual ingredient object"""
        if self.ingredient_type == 'grain':
            try:
                return Grain.objects.get(id=self.ingredient_id)
            except Grain.DoesNotExist:
                return None
        elif self.ingredient_type == 'hop':
            try:
                return Hop.objects.get(id=self.ingredient_id)
            except Hop.DoesNotExist:
                return None
        elif self.ingredient_type == 'yeast':
            try:
                return Yeast.objects.get(id=self.ingredient_id)
            except Yeast.DoesNotExist:
                return None
        return None
    
    def convert_to_kg(self):
        """Convert current stock to kg for calculations"""
        conversion_factors = {
            'kg': 1.0,
            'g': 0.001,
            'lb': 0.453592,
            'oz': 0.0283495,
            'unit': 1.0,  # Assume 1 unit = 1 kg for calculations
        }
        return self.current_stock * conversion_factors.get(self.unit, 1.0)
    
    def update_stock(self, quantity_used, unit='kg'):
        """Update stock after using ingredients"""
        if unit == 'kg' and self.unit != 'kg':
            # Convert kg to current unit
            if self.unit == 'g':
                quantity_used *= 1000
            elif self.unit == 'lb':
                quantity_used *= 2.20462
            elif self.unit == 'oz':
                quantity_used *= 35.274
        
        self.current_stock = max(0, self.current_stock - quantity_used)
        self.save()

class InventoryTransaction(TimeStampedModel):
    """
    Track inventory changes
    """
    TRANSACTION_TYPES = [
        ('purchase', 'Purchase'),
        ('use', 'Used in Recipe'),
        ('waste', 'Waste/Loss'),
        ('adjustment', 'Stock Adjustment'),
    ]
    
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.FloatField()
    unit = models.CharField(max_length=10)
    
    # Optional references
    recipe = models.ForeignKey('recipes.Recipe', on_delete=models.SET_NULL, null=True, blank=True)
    brew_session = models.ForeignKey('brewing.BrewSession', on_delete=models.SET_NULL, null=True, blank=True)
    
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.quantity} {self.unit} {self.inventory_item.ingredient_name}"

class ShoppingList(TimeStampedModel):
    """
    Shopping list for ingredients
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, default="Shopping List")
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def total_estimated_cost(self):
        """Calculate total estimated cost"""
        return sum(item.estimated_cost() for item in self.shoppinglistitem_set.all())

class ShoppingListItem(TimeStampedModel):
    """
    Items in shopping list
    """
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE)
    ingredient_type = models.CharField(max_length=20, choices=InventoryItem.INGREDIENT_TYPES)
    ingredient_id = models.PositiveIntegerField(null=True, blank=True)
    ingredient_name = models.CharField(max_length=200)
    
    quantity_needed = models.FloatField()
    unit = models.CharField(max_length=10, choices=InventoryItem.UNITS)
    
    estimated_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    
    is_purchased = models.BooleanField(default=False)
    purchased_date = models.DateField(null=True, blank=True)
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    priority = models.IntegerField(default=1, help_text="1=High, 2=Medium, 3=Low")
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['priority', 'ingredient_name']
    
    def __str__(self):
        return f"{self.quantity_needed} {self.unit} {self.ingredient_name}"
    
    def estimated_cost(self):
        """Calculate estimated cost"""
        if self.estimated_price:
            return float(self.estimated_price) * self.quantity_needed
        return 0.0