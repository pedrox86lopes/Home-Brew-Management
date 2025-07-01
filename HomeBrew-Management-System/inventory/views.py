from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F 
from django.db import models  
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from .models import InventoryItem, InventoryTransaction, ShoppingList, ShoppingListItem, Supplier
from recipes.models import Grain, Hop, Yeast

@login_required
def inventory_list(request):
    """List all inventory items"""
    items = InventoryItem.objects.filter(user=request.user)
    
    # Filter by ingredient type
    ingredient_type = request.GET.get('type')
    if ingredient_type:
        items = items.filter(ingredient_type=ingredient_type)
    
    # Filter by low stock
    if request.GET.get('low_stock'):
        items = items.filter(current_stock__lte=F('minimum_stock'))
    
    # Filter by expired
    if request.GET.get('expired'):
        items = items.filter(expiry_date__lt=timezone.now().date())
    
    # Search
    search_query = request.GET.get('search')
    if search_query:
        items = items.filter(ingredient_name__icontains=search_query)
    
    # Statistics
    total_value = sum(float(item.current_stock * item.cost_per_unit) for item in items)
    low_stock_count = items.filter(current_stock__lte=F('minimum_stock')).count()
    
    # Pagination
    paginator = Paginator(items, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_value': total_value,
        'low_stock_count': low_stock_count,
        'search_query': search_query,
        'ingredient_type': ingredient_type,
    }
    
    return render(request, 'inventory/inventory_list.html', context)

@login_required
def inventory_detail(request, pk):
    """Inventory item detail view"""
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    
    # Get recent transactions
    transactions = InventoryTransaction.objects.filter(
        inventory_item=item
    ).order_by('-created_at')[:10]
    
    # Get usage stats
    usage_last_30_days = InventoryTransaction.objects.filter(
        inventory_item=item,
        transaction_type='use',
        created_at__gte=timezone.now() - timedelta(days=30)
    ).aggregate(total_used=Sum('quantity'))['total_used'] or 0
    
    context = {
        'item': item,
        'transactions': transactions,
        'usage_last_30_days': usage_last_30_days,
        'ingredient_object': item.ingredient_object,
    }
    
    return render(request, 'inventory/inventory_detail.html', context)

@login_required
def ingredient_add(request):
    """Add new ingredient to inventory"""
    if request.method == 'POST':
        ingredient_type = request.POST.get('ingredient_type')
        ingredient_id = request.POST.get('ingredient_id')
        current_stock = float(request.POST.get('current_stock', 0))
        unit = request.POST.get('unit', 'kg')
        cost_per_unit = float(request.POST.get('cost_per_unit', 0))
        minimum_stock = float(request.POST.get('minimum_stock', 0))
        location = request.POST.get('location', '')
        
        # Get ingredient name
        ingredient_name = ""
        if ingredient_type == 'grain':
            try:
                ingredient = Grain.objects.get(id=ingredient_id)
                ingredient_name = ingredient.name
            except Grain.DoesNotExist:
                messages.error(request, 'Selected grain not found.')
                return redirect('ingredient_add')
        elif ingredient_type == 'hop':
            try:
                ingredient = Hop.objects.get(id=ingredient_id)
                ingredient_name = ingredient.name
            except Hop.DoesNotExist:
                messages.error(request, 'Selected hop not found.')
                return redirect('ingredient_add')
        elif ingredient_type == 'yeast':
            try:
                ingredient = Yeast.objects.get(id=ingredient_id)
                ingredient_name = ingredient.name
            except Yeast.DoesNotExist:
                messages.error(request, 'Selected yeast not found.')
                return redirect('ingredient_add')
        
        # Check if item already exists
        existing_item = InventoryItem.objects.filter(
            user=request.user,
            ingredient_type=ingredient_type,
            ingredient_id=ingredient_id
        ).first()
        
        if existing_item:
            # Update existing item
            existing_item.current_stock += current_stock
            existing_item.cost_per_unit = cost_per_unit
            existing_item.minimum_stock = minimum_stock
            existing_item.location = location
            existing_item.save()
            
            # Create transaction
            InventoryTransaction.objects.create(
                inventory_item=existing_item,
                transaction_type='purchase',
                quantity=current_stock,
                unit=unit,
                cost=current_stock * cost_per_unit,
                notes=f"Added to existing inventory"
            )
            
            messages.success(request, f'Updated {ingredient_name} inventory.')
        else:
            # Create new item
            item = InventoryItem.objects.create(
                user=request.user,
                ingredient_type=ingredient_type,
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                current_stock=current_stock,
                unit=unit,
                cost_per_unit=cost_per_unit,
                minimum_stock=minimum_stock,
                location=location
            )
            
            # Create transaction
            InventoryTransaction.objects.create(
                inventory_item=item,
                transaction_type='purchase',
                quantity=current_stock,
                unit=unit,
                cost=current_stock * cost_per_unit,
                notes=f"Initial inventory"
            )
            
            messages.success(request, f'Added {ingredient_name} to inventory.')
        
        return redirect('inventory_list')
    
    # Get available ingredients
    grains = Grain.objects.all()
    hops = Hop.objects.all()
    yeasts = Yeast.objects.all()
    
    context = {
        'grains': grains,
        'hops': hops,
        'yeasts': yeasts,
    }
    
    return render(request, 'inventory/ingredient_add.html', context)

@login_required
def inventory_update_stock(request, pk):
    """Update inventory stock"""
    item = get_object_or_404(InventoryItem, pk=pk, user=request.user)
    
    if request.method == 'POST':
        transaction_type = request.POST.get('transaction_type')
        quantity = float(request.POST.get('quantity', 0))
        notes = request.POST.get('notes', '')
        
        # Update stock based on transaction type
        if transaction_type in ['purchase', 'adjustment']:
            if transaction_type == 'adjustment':
                # For adjustments, set to exact amount
                old_stock = item.current_stock
                item.current_stock = quantity
                quantity = quantity - old_stock  # For transaction record
            else:
                # For purchases, add to current stock
                item.current_stock += quantity
        else:
            # For use/waste, subtract from stock
            item.current_stock = max(0, item.current_stock - quantity)
        
        item.save()
        
        # Create transaction record
        InventoryTransaction.objects.create(
            inventory_item=item,
            transaction_type=transaction_type,
            quantity=abs(quantity),
            unit=item.unit,
            notes=notes
        )
        
        messages.success(request, f'Updated stock for {item.ingredient_name}.')
        return redirect('inventory_detail', pk=item.pk)
    
    return render(request, 'inventory/update_stock.html', {'item': item})

@login_required
def shopping_list_view(request):
    """View shopping lists"""
    shopping_lists = ShoppingList.objects.filter(user=request.user)
    
    # Get or create active shopping list
    active_list = shopping_lists.filter(is_active=True).first()
    if not active_list:
        active_list = ShoppingList.objects.create(
            user=request.user,
            name="My Shopping List"
        )
    
    # Get items for active list
    items = ShoppingListItem.objects.filter(shopping_list=active_list)
    
    context = {
        'shopping_lists': shopping_lists,
        'active_list': active_list,
        'items': items,
        'total_cost': active_list.total_estimated_cost(),
    }
    
    return render(request, 'inventory/shopping_list.html', context)

@login_required
def add_to_shopping_list(request):
    """Add item to shopping list"""
    if request.method == 'POST':
        shopping_list_id = request.POST.get('shopping_list_id')
        ingredient_type = request.POST.get('ingredient_type')
        ingredient_id = request.POST.get('ingredient_id')
        quantity = float(request.POST.get('quantity', 0))
        unit = request.POST.get('unit', 'kg')
        
        shopping_list = get_object_or_404(ShoppingList, id=shopping_list_id, user=request.user)
        
        # Get ingredient name
        ingredient_name = ""
        if ingredient_type == 'grain':
            ingredient = get_object_or_404(Grain, id=ingredient_id)
            ingredient_name = ingredient.name
        elif ingredient_type == 'hop':
            ingredient = get_object_or_404(Hop, id=ingredient_id)
            ingredient_name = ingredient.name
        elif ingredient_type == 'yeast':
            ingredient = get_object_or_404(Yeast, id=ingredient_id)
            ingredient_name = ingredient.name
        
        # Check for existing item
        existing_item = ShoppingListItem.objects.filter(
            shopping_list=shopping_list,
            ingredient_type=ingredient_type,
            ingredient_id=ingredient_id
        ).first()
        
        if existing_item:
            existing_item.quantity_needed += quantity
            existing_item.save()
            messages.success(request, f'Updated {ingredient_name} quantity in shopping list.')
        else:
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                ingredient_type=ingredient_type,
                ingredient_id=ingredient_id,
                ingredient_name=ingredient_name,
                quantity_needed=quantity,
                unit=unit
            )
            messages.success(request, f'Added {ingredient_name} to shopping list.')
        
        return redirect('shopping_list')
    
    return redirect('shopping_list')

@login_required
def generate_shopping_list_from_recipe(request, recipe_id):
    """Generate shopping list from recipe"""
    from recipes.models import Recipe
    
    recipe = get_object_or_404(Recipe, id=recipe_id, created_by=request.user)
    
    # Get or create active shopping list
    shopping_list = ShoppingList.objects.filter(user=request.user, is_active=True).first()
    if not shopping_list:
        shopping_list = ShoppingList.objects.create(
            user=request.user,
            name=f"Shopping List - {recipe.name}"
        )
    
    items_added = 0
    
    # Add grains
    for grain_addition in recipe.grainaddition_set.all():
        # Check current inventory
        inventory_item = InventoryItem.objects.filter(
            user=request.user,
            ingredient_type='grain',
            ingredient_id=grain_addition.grain.id
        ).first()
        
        needed_quantity = grain_addition.weight
        if inventory_item:
            available = inventory_item.convert_to_kg()
            needed_quantity = max(0, needed_quantity - available)
        
        if needed_quantity > 0:
            ShoppingListItem.objects.update_or_create(
                shopping_list=shopping_list,
                ingredient_type='grain',
                ingredient_id=grain_addition.grain.id,
                defaults={
                    'ingredient_name': grain_addition.grain.name,
                    'quantity_needed': needed_quantity,
                    'unit': 'kg'
                }
            )
            items_added += 1
    
    # Add hops
    for hop_addition in recipe.hopaddition_set.all():
        inventory_item = InventoryItem.objects.filter(
            user=request.user,
            ingredient_type='hop',
            ingredient_id=hop_addition.hop.id
        ).first()
        
        needed_quantity = hop_addition.weight
        if inventory_item:
            available = inventory_item.convert_to_kg()
            needed_quantity = max(0, needed_quantity - available)
        
        if needed_quantity > 0:
            ShoppingListItem.objects.update_or_create(
                shopping_list=shopping_list,
                ingredient_type='hop',
                ingredient_id=hop_addition.hop.id,
                defaults={
                    'ingredient_name': hop_addition.hop.name,
                    'quantity_needed': needed_quantity,
                    'unit': 'kg'
                }
            )
            items_added += 1
    
    # Add yeast
    for yeast_addition in recipe.yeastaddition_set.all():
        inventory_item = InventoryItem.objects.filter(
            user=request.user,
            ingredient_type='yeast',
            ingredient_id=yeast_addition.yeast.id
        ).first()
        
        needed_quantity = yeast_addition.amount
        if inventory_item:
            needed_quantity = max(0, needed_quantity - inventory_item.current_stock)
        
        if needed_quantity > 0:
            ShoppingListItem.objects.update_or_create(
                shopping_list=shopping_list,
                ingredient_type='yeast',
                ingredient_id=yeast_addition.yeast.id,
                defaults={
                    'ingredient_name': yeast_addition.yeast.name,
                    'quantity_needed': needed_quantity,
                    'unit': 'unit'
                }
            )
            items_added += 1
    
    if items_added > 0:
        messages.success(request, f'Added {items_added} items to shopping list from recipe "{recipe.name}".')
    else:
        messages.info(request, 'All ingredients are already in stock!')
    
    return redirect('shopping_list')