from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from brewing.models import BrewSession, TemperatureReading, GravityReading
from recipes.models import Recipe
from inventory.models import InventoryItem
from core.models import BeerStyle
from .models import BrewingStats
import json

@login_required
def analytics_dashboard(request):
    """Main analytics dashboard"""
    # Get or create brewing stats
    stats, created = BrewingStats.objects.get_or_create(user=request.user)
    if created or stats.last_updated < timezone.now() - timedelta(hours=24):
        stats.update_stats()
    
    # Recent activity
    recent_sessions = BrewSession.objects.filter(
        brewer=request.user
    ).order_by('-brew_date')[:5]
    
    # Monthly brewing activity
    monthly_data = get_monthly_brewing_data(request.user)
    
    # Style breakdown
    style_data = get_style_breakdown(request.user)
    
    # Efficiency trends
    efficiency_data = get_efficiency_trends(request.user)
    
    context = {
        'stats': stats,
        'recent_sessions': recent_sessions,
        'monthly_data': json.dumps(monthly_data),
        'style_data': json.dumps(style_data),
        'efficiency_data': json.dumps(efficiency_data),
    }
    
    return render(request, 'analytics/dashboard.html', context)

def get_monthly_brewing_data(user):
    """Get monthly brewing activity data"""
    # Get data for last 12 months
    end_date = timezone.now()
    start_date = end_date - timedelta(days=365)
    
    monthly_data = []
    current_date = start_date
    
    while current_date <= end_date:
        month_start = current_date.replace(day=1)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)
        
        brew_count = BrewSession.objects.filter(
            brewer=user,
            brew_date__gte=month_start,
            brew_date__lt=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%Y-%m'),
            'brews': brew_count,
            'label': month_start.strftime('%b %Y')
        })
        
        current_date = month_end
    
    return monthly_data

def get_style_breakdown(user):
    """Get breakdown of brews by style"""
    style_counts = BrewSession.objects.filter(
        brewer=user
    ).values('recipe__style__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return [
        {'style': item['recipe__style__name'], 'count': item['count']}
        for item in style_counts
    ]

def get_efficiency_trends(user):
    """Get efficiency trends over time"""
    sessions = BrewSession.objects.filter(
        brewer=user,
        status='completed',
        actual_efficiency__isnull=False
    ).order_by('brew_date')[:20]  # Last 20 completed brews
    
    return [
        {
            'date': session.brew_date.strftime('%Y-%m-%d'),
            'efficiency': float(session.actual_efficiency),
            'batch_name': session.batch_name
        }
        for session in sessions
    ]

@login_required
def brewing_performance(request):
    """Detailed brewing performance analytics"""
    # Get completed sessions
    sessions = BrewSession.objects.filter(
        brewer=request.user,
        status='completed'
    ).order_by('-brew_date')
    
    # Performance metrics
    performance_data = {
        'total_sessions': sessions.count(),
        'avg_efficiency': sessions.aggregate(Avg('actual_efficiency'))['actual_efficiency__avg'],
        'avg_og': sessions.aggregate(Avg('actual_og'))['actual_og__avg'],
        'avg_fg': sessions.aggregate(Avg('actual_fg'))['actual_fg__avg'],
        'avg_abv': sessions.aggregate(Avg('actual_abv'))['actual_abv__avg'],
    }
    
    # Efficiency by style
    efficiency_by_style = sessions.values(
        'recipe__style__name'
    ).annotate(
        avg_efficiency=Avg('actual_efficiency'),
        count=Count('id')
    ).filter(count__gte=2).order_by('-avg_efficiency')
    
    # OG vs Target analysis
    og_analysis = []
    for session in sessions.filter(actual_og__isnull=False)[:20]:
        target_og = session.recipe.calculated_og
        actual_og = session.actual_og
        if target_og:
            difference = actual_og - target_og
            og_analysis.append({
                'batch_name': session.batch_name,
                'target': float(target_og),
                'actual': float(actual_og),
                'difference': float(difference)
            })
    
    context = {
        'sessions': sessions[:20],
        'performance_data': performance_data,
        'efficiency_by_style': efficiency_by_style,
        'og_analysis': json.dumps(og_analysis),
    }
    
    return render(request, 'analytics/brewing_performance.html', context)

@login_required
def cost_analysis(request):
    """Cost analysis and trends"""
    # Recipe costs
    recipes = Recipe.objects.filter(created_by=request.user)
    
    cost_data = []
    for recipe in recipes:
        total_cost = recipe.total_cost()
        cost_per_liter = total_cost / recipe.batch_size if recipe.batch_size > 0 else 0
        cost_data.append({
            'name': recipe.name,
            'total_cost': float(total_cost),
            'cost_per_liter': float(cost_per_liter),
            'batch_size': recipe.batch_size,
            'style': recipe.style.name
        })
    
    # Inventory value
    inventory_items = InventoryItem.objects.filter(user=request.user)
    total_inventory_value = sum(
        float(item.current_stock * item.cost_per_unit)
        for item in inventory_items
    )
    
    # Cost by ingredient type
    ingredient_costs = {}
    for item in inventory_items:
        ingredient_type = item.get_ingredient_type_display()
        if ingredient_type not in ingredient_costs:
            ingredient_costs[ingredient_type] = 0
        ingredient_costs[ingredient_type] += float(item.current_stock * item.cost_per_unit)
    
    # Average costs by style
    style_costs = {}
    for recipe in recipes:
        style = recipe.style.name
        cost_per_liter = recipe.total_cost() / recipe.batch_size if recipe.batch_size > 0 else 0
        
        if style not in style_costs:
            style_costs[style] = []
        style_costs[style].append(float(cost_per_liter))
    
    # Calculate averages
    avg_style_costs = {
        style: sum(costs) / len(costs)
        for style, costs in style_costs.items()
        if costs
    }
    
    context = {
        'cost_data': json.dumps(cost_data),
        'total_inventory_value': total_inventory_value,
        'ingredient_costs': json.dumps(ingredient_costs),
        'avg_style_costs': json.dumps(avg_style_costs),
        'recipes_count': recipes.count(),
    }
    
    return render(request, 'analytics/cost_analysis.html', context)

@login_required
def fermentation_tracking(request):
    """Fermentation tracking and temperature analysis"""
    # Get active fermentation sessions
    active_fermentations = BrewSession.objects.filter(
        brewer=request.user,
        status='fermenting'
    )
    
    # Temperature data for active fermentations
    temp_data = {}
    for session in active_fermentations:
        readings = TemperatureReading.objects.filter(
            brew_session=session,
            reading_type='fermentation'
        ).order_by('timestamp')[:50]
        
        temp_data[session.id] = {
            'batch_name': session.batch_name,
            'readings': [
                {
                    'timestamp': reading.timestamp.isoformat(),
                    'temperature': float(reading.temperature)
                }
                for reading in readings
            ]
        }
    
    # Gravity progression for active fermentations
    gravity_data = {}
    for session in active_fermentations:
        readings = GravityReading.objects.filter(
            brew_session=session
        ).order_by('timestamp')
        
        gravity_data[session.id] = [
            {
                'timestamp': reading.timestamp.isoformat(),
                'gravity': float(reading.gravity),
                'type': reading.reading_type
            }
            for reading in readings
        ]
    
    # Fermentation statistics
    completed_fermentations = BrewSession.objects.filter(
        brewer=request.user,
        status='completed',
        fermentation_start__isnull=False,
        fermentation_end__isnull=False
    )
    
    fermentation_stats = {
        'avg_fermentation_days': 0,
        'shortest_fermentation': 0,
        'longest_fermentation': 0,
    }
    
    if completed_fermentations.exists():
        fermentation_times = [
            (session.fermentation_end - session.fermentation_start).days
            for session in completed_fermentations
        ]
        
        fermentation_stats = {
            'avg_fermentation_days': sum(fermentation_times) / len(fermentation_times),
            'shortest_fermentation': min(fermentation_times),
            'longest_fermentation': max(fermentation_times),
        }
    
    context = {
        'active_fermentations': active_fermentations,
        'temp_data': json.dumps(temp_data),
        'gravity_data': json.dumps(gravity_data),
        'fermentation_stats': fermentation_stats,
    }
    
    return render(request, 'analytics/fermentation_tracking.html', context)

@login_required
def inventory_analytics(request):
    """Inventory analytics and usage patterns"""
    inventory_items = InventoryItem.objects.filter(user=request.user)
    
    # Low stock alerts
    low_stock_items = inventory_items.filter(
        current_stock__lte=models.F('minimum_stock')
    )
    
    # Inventory value by type
    inventory_by_type = {}
    for item in inventory_items:
        item_type = item.get_ingredient_type_display()
        value = float(item.current_stock * item.cost_per_unit)
        
        if item_type not in inventory_by_type:
            inventory_by_type[item_type] = {'count': 0, 'value': 0}
        
        inventory_by_type[item_type]['count'] += 1
        inventory_by_type[item_type]['value'] += value
    
    # Usage trends (simplified - would need transaction history)
    usage_data = []
    for item in inventory_items.filter(current_stock__gt=0)[:10]:
        # This is a simplified calculation
        usage_data.append({
            'name': item.ingredient_name,
            'current_stock': float(item.current_stock),
            'minimum_stock': float(item.minimum_stock),
            'unit': item.unit,
            'value': float(item.current_stock * item.cost_per_unit)
        })
    
    context = {
        'inventory_items': inventory_items,
        'low_stock_items': low_stock_items,
        'inventory_by_type': json.dumps(inventory_by_type),
        'usage_data': json.dumps(usage_data),
        'total_items': inventory_items.count(),
        'total_value': sum(float(item.current_stock * item.cost_per_unit) for item in inventory_items),
    }
    
    return render(request, 'analytics/inventory_analytics.html', context)
