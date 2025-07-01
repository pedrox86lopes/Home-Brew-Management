# recipes/views.py - Complete corrected file

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from .models import Recipe, Grain, Hop, Yeast, GrainAddition, HopAddition, YeastAddition
from .forms import (RecipeForm, GrainAdditionFormSet, HopAdditionFormSet, 
                   YeastAdditionFormSet, RecipeGeneratorForm)
from core.models import BeerStyle
import random
import json

@login_required
def recipe_list(request):
    """List all recipes with search and filtering"""
    recipes = Recipe.objects.filter(created_by=request.user)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        recipes = recipes.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(style__name__icontains=search_query)
        )
    
    # Style filtering
    style_filter = request.GET.get('style')
    if style_filter:
        recipes = recipes.filter(style_id=style_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    recipes = recipes.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(recipes, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'style_filter': style_filter,
        'sort_by': sort_by,
        'styles': BeerStyle.objects.all(),
    }
    
    return render(request, 'recipes/recipe_list.html', context)

@login_required
def recipe_detail(request, pk):
    """Recipe detail view"""
    recipe = get_object_or_404(Recipe, pk=pk, created_by=request.user)
    
    # Get all ingredients
    grain_additions = recipe.grainaddition_set.all()
    hop_additions = recipe.hopaddition_set.all()
    yeast_additions = recipe.yeastaddition_set.all()
    
    context = {
        'recipe': recipe,
        'grain_additions': grain_additions,
        'hop_additions': hop_additions,
        'yeast_additions': yeast_additions,
        'total_cost': recipe.total_cost(),
        'cost_per_liter': recipe.total_cost() / recipe.batch_size if recipe.batch_size > 0 else 0,
    }
    
    return render(request, 'recipes/recipe_detail.html', context)

@login_required
def recipe_create(request):
    """Create new recipe"""
    if request.method == 'POST':
        form = RecipeForm(request.POST)
        grain_formset = GrainAdditionFormSet(request.POST)
        hop_formset = HopAdditionFormSet(request.POST)
        yeast_formset = YeastAdditionFormSet(request.POST)
        
        if form.is_valid() and grain_formset.is_valid() and hop_formset.is_valid() and yeast_formset.is_valid():
            recipe = form.save(commit=False)
            recipe.created_by = request.user
            recipe.save()
            
            # Save formsets
            grain_formset.instance = recipe
            grain_formset.save()
            
            hop_formset.instance = recipe
            hop_formset.save()
            
            yeast_formset.instance = recipe
            yeast_formset.save()
            
            # Calculate recipe values
            recipe.calculate_all_values()
            
            messages.success(request, f'Recipe "{recipe.name}" created successfully!')
            return redirect('recipe_detail', pk=recipe.pk)
    else:
        form = RecipeForm()
        grain_formset = GrainAdditionFormSet()
        hop_formset = HopAdditionFormSet()
        yeast_formset = YeastAdditionFormSet()
    
    context = {
        'form': form,
        'grain_formset': grain_formset,
        'hop_formset': hop_formset,
        'yeast_formset': yeast_formset,
        'is_create': True,
    }
    
    return render(request, 'recipes/recipe_form.html', context)

@login_required
def recipe_edit(request, pk):
    """Edit existing recipe"""
    recipe = get_object_or_404(Recipe, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        form = RecipeForm(request.POST, instance=recipe)
        grain_formset = GrainAdditionFormSet(request.POST, instance=recipe)
        hop_formset = HopAdditionFormSet(request.POST, instance=recipe)
        yeast_formset = YeastAdditionFormSet(request.POST, instance=recipe)
        
        if form.is_valid() and grain_formset.is_valid() and hop_formset.is_valid() and yeast_formset.is_valid():
            recipe = form.save()
            grain_formset.save()
            hop_formset.save()
            yeast_formset.save()
            
            # Recalculate recipe values
            recipe.calculate_all_values()
            
            messages.success(request, f'Recipe "{recipe.name}" updated successfully!')
            return redirect('recipe_detail', pk=recipe.pk)
    else:
        form = RecipeForm(instance=recipe)
        grain_formset = GrainAdditionFormSet(instance=recipe)
        hop_formset = HopAdditionFormSet(instance=recipe)
        yeast_formset = YeastAdditionFormSet(instance=recipe)
    
    context = {
        'form': form,
        'grain_formset': grain_formset,
        'hop_formset': hop_formset,
        'yeast_formset': yeast_formset,
        'recipe': recipe,
        'is_edit': True,
    }
    
    return render(request, 'recipes/recipe_form.html', context)

@login_required
def recipe_delete(request, pk):
    """Delete recipe"""
    recipe = get_object_or_404(Recipe, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        recipe_name = recipe.name
        recipe.delete()
        messages.success(request, f'Recipe "{recipe_name}" deleted successfully!')
        return redirect('recipe_list')
    
    return render(request, 'recipes/recipe_confirm_delete.html', {'recipe': recipe})

@login_required
def recipe_clone(request, pk):
    """Clone an existing recipe"""
    original_recipe = get_object_or_404(Recipe, pk=pk, created_by=request.user)
    
    # Create a copy of the recipe
    cloned_recipe = Recipe.objects.get(pk=original_recipe.pk)
    cloned_recipe.pk = None
    cloned_recipe.name = f"{original_recipe.name} (Copy)"
    cloned_recipe.save()
    
    # Clone grain additions
    for grain_addition in original_recipe.grainaddition_set.all():
        GrainAddition.objects.create(
            recipe=cloned_recipe,
            grain=grain_addition.grain,
            weight=grain_addition.weight,
            percentage=grain_addition.percentage
        )
    
    # Clone hop additions
    for hop_addition in original_recipe.hopaddition_set.all():
        HopAddition.objects.create(
            recipe=cloned_recipe,
            hop=hop_addition.hop,
            weight=hop_addition.weight,
            boil_time=hop_addition.boil_time,
            use=hop_addition.use
        )
    
    # Clone yeast additions
    for yeast_addition in original_recipe.yeastaddition_set.all():
        YeastAddition.objects.create(
            recipe=cloned_recipe,
            yeast=yeast_addition.yeast,
            amount=yeast_addition.amount
        )
    
    # Recalculate values
    cloned_recipe.calculate_all_values()
    
    messages.success(request, f'Recipe cloned successfully as "{cloned_recipe.name}"!')
    return redirect('recipe_detail', pk=cloned_recipe.pk)

@login_required
def recipe_generator(request):
    """Generate recipes based on style and constraints"""
    if request.method == 'POST':
        form = RecipeGeneratorForm(request.POST)
        if form.is_valid():
            generated_recipe = generate_recipe_from_form(form, request.user)
            if generated_recipe:
                messages.success(request, f'Recipe "{generated_recipe.name}" generated successfully!')
                return redirect('recipe_detail', pk=generated_recipe.pk)
            else:
                messages.error(request, 'Could not generate recipe with current constraints.')
    else:
        form = RecipeGeneratorForm()
    
    return render(request, 'recipes/recipe_generator.html', {'form': form})

def generate_recipe_from_form(form, user):
    """Generate a recipe based on form data"""
    style = form.cleaned_data['style']
    batch_size = form.cleaned_data['batch_size']
    max_cost = form.cleaned_data.get('max_cost')
    complexity = form.cleaned_data['complexity']
    use_inventory_only = form.cleaned_data['use_inventory_only']
    
    # Create base recipe
    recipe = Recipe.objects.create(
        name=f"Generated {style.name}",
        description=f"Auto-generated recipe for {style.name}",
        style=style,
        batch_size=batch_size,
        efficiency=75.0,
        created_by=user
    )
    
    try:
        # Generate grain bill
        generate_grain_bill(recipe, complexity, use_inventory_only, max_cost)
        
        # Generate hop schedule
        generate_hop_schedule(recipe, complexity, use_inventory_only, max_cost)
        
        # Generate yeast selection
        generate_yeast_selection(recipe, use_inventory_only)
        
        # Calculate final values
        recipe.calculate_all_values()
        
        return recipe
    
    except Exception as e:
        recipe.delete()
        return None

def generate_grain_bill(recipe, complexity, use_inventory_only, max_cost):
    """Generate grain bill for recipe"""
    style = recipe.style
    
    # Get available grains
    if use_inventory_only:
        # TODO: Filter by inventory
        available_grains = Grain.objects.filter(grain_type='base')
    else:
        available_grains = Grain.objects.all()
    
    # Base malt (70-85% of grain bill)
    base_malts = available_grains.filter(grain_type='base')
    if base_malts.exists():
        base_malt = random.choice(base_malts)
        base_percentage = random.uniform(70, 85)
        
        # Calculate base malt weight to hit target OG
        target_og = random.uniform(style.og_min, style.og_max)
        total_points_needed = (target_og - 1) * recipe.batch_size * 1000
        base_points = total_points_needed * (base_percentage / 100)
        base_weight = base_points / (base_malt.extract_potential * 0.75)  # 75% efficiency
        
        GrainAddition.objects.create(
            recipe=recipe,
            grain=base_malt,
            weight=base_weight / 2.2,  # Convert to kg
            percentage=base_percentage
        )
    
    # Add specialty malts based on complexity
    if complexity in ['moderate', 'complex']:
        specialty_count = 2 if complexity == 'moderate' else random.randint(3, 5)
        specialty_grains = available_grains.exclude(grain_type='base')
        
        remaining_percentage = 100 - base_percentage
        for i in range(min(specialty_count, specialty_grains.count())):
            if remaining_percentage <= 0:
                break
                
            specialty_grain = random.choice(specialty_grains)
            specialty_percentage = min(random.uniform(2, 10), remaining_percentage)
            specialty_weight = (base_weight * specialty_percentage) / base_percentage
            
            GrainAddition.objects.create(
                recipe=recipe,
                grain=specialty_grain,
                weight=specialty_weight / 2.2,  # Convert to kg
                percentage=specialty_percentage
            )
            
            remaining_percentage -= specialty_percentage

def generate_hop_schedule(recipe, complexity, use_inventory_only, max_cost):
    """Generate hop schedule for recipe"""
    style = recipe.style
    
    # Get available hops
    if use_inventory_only:
        # TODO: Filter by inventory
        available_hops = Hop.objects.all()
    else:
        available_hops = Hop.objects.all()
    
    # Target IBU
    target_ibu = random.uniform(style.ibu_min, style.ibu_max)
    
    # Bittering hop (60 min)
    bittering_hops = available_hops.filter(hop_type__in=['bittering', 'dual'])
    if bittering_hops.exists():
        bittering_hop = random.choice(bittering_hops)
        # Calculate weight needed for ~80% of target IBU
        bittering_ibu = target_ibu * 0.8
        bittering_weight = calculate_hop_weight_for_ibu(
            bittering_ibu, bittering_hop.alpha_acid, 60, recipe.batch_size, 1.050
        )
        
        HopAddition.objects.create(
            recipe=recipe,
            hop=bittering_hop,
            weight=bittering_weight / 1000,  # Convert to kg
            boil_time=60,
            use='boil'
        )
    
    # Flavor/Aroma hops based on complexity
    if complexity in ['moderate', 'complex']:
        aroma_hops = available_hops.filter(hop_type__in=['aroma', 'dual'])
        if aroma_hops.exists():
            # 15-20 min addition
            flavor_hop = random.choice(aroma_hops)
            flavor_weight = random.uniform(0.015, 0.030)  # 15-30g
            
            HopAddition.objects.create(
                recipe=recipe,
                hop=flavor_hop,
                weight=flavor_weight,
                boil_time=random.randint(15, 20),
                use='boil'
            )
            
            # Aroma addition (5 min or flameout)
            if complexity == 'complex':
                aroma_hop = random.choice(aroma_hops)
                aroma_weight = random.uniform(0.015, 0.040)  # 15-40g
                
                HopAddition.objects.create(
                    recipe=recipe,
                    hop=aroma_hop,
                    weight=aroma_weight,
                    boil_time=random.choice([5, 0]),
                    use='boil' if random.choice([True, False]) else 'flameout'
                )

def generate_yeast_selection(recipe, use_inventory_only):
    """Generate yeast selection for recipe"""
    style = recipe.style
    
    # Get available yeast
    if use_inventory_only:
        # TODO: Filter by inventory
        available_yeast = Yeast.objects.all()
    else:
        available_yeast = Yeast.objects.all()
    
    # Filter by appropriate yeast type
    if 'lager' in style.name.lower():
        yeast_candidates = available_yeast.filter(yeast_type='lager')
    elif 'wheat' in style.name.lower():
        yeast_candidates = available_yeast.filter(yeast_type__in=['wheat', 'ale'])
    else:
        yeast_candidates = available_yeast.filter(yeast_type='ale')
    
    if yeast_candidates.exists():
        selected_yeast = random.choice(yeast_candidates)
        YeastAddition.objects.create(
            recipe=recipe,
            yeast=selected_yeast,
            amount=1.0
        )

def calculate_hop_weight_for_ibu(target_ibu, alpha_acid, boil_time, batch_size, og):
    """Calculate hop weight needed for target IBU"""
    utilization = (1.65 * (0.000125 ** (og - 1))) * \
                  ((1 - 2.718 ** (-0.04 * boil_time)) / 4.15)
    
    weight_grams = (target_ibu * batch_size * 100) / (alpha_acid * utilization * 1000)
    return weight_grams

@login_required
def recipe_scale(request, pk):
    """Scale recipe to different batch size"""
    recipe = get_object_or_404(Recipe, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        new_batch_size = float(request.POST.get('new_batch_size', recipe.batch_size))
        scale_factor = new_batch_size / recipe.batch_size
        
        # Create scaled recipe
        scaled_recipe = Recipe.objects.get(pk=recipe.pk)
        scaled_recipe.pk = None
        scaled_recipe.name = f"{recipe.name} ({new_batch_size}L)"
        scaled_recipe.batch_size = new_batch_size
        scaled_recipe.save()
        
        # Scale grain additions
        for grain_addition in recipe.grainaddition_set.all():
            GrainAddition.objects.create(
                recipe=scaled_recipe,
                grain=grain_addition.grain,
                weight=grain_addition.weight * scale_factor,
                percentage=grain_addition.percentage
            )
        
        # Scale hop additions
        for hop_addition in recipe.hopaddition_set.all():
            HopAddition.objects.create(
                recipe=scaled_recipe,
                hop=hop_addition.hop,
                weight=hop_addition.weight * scale_factor,
                boil_time=hop_addition.boil_time,
                use=hop_addition.use
            )
        
        # Copy yeast additions (usually don't scale linearly)
        for yeast_addition in recipe.yeastaddition_set.all():
            YeastAddition.objects.create(
                recipe=scaled_recipe,
                yeast=yeast_addition.yeast,
                amount=yeast_addition.amount
            )
        
        scaled_recipe.calculate_all_values()
        
        messages.success(request, f'Recipe scaled to {new_batch_size}L successfully!')
        return redirect('recipe_detail', pk=scaled_recipe.pk)
    
    return render(request, 'recipes/recipe_scale.html', {'recipe': recipe})

# NEW AI RECIPE GENERATOR VIEWS

@login_required
def ai_recipe_generator_django(request):
    """Pure Django AI recipe generator view"""
    return render(request, 'recipes/ai_recipe_generator_django.html')

@login_required
@csrf_exempt
def ai_save_recipe(request):
    """Save AI-generated recipe to Django models"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'Only POST method allowed'
        })
    
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Extract basic recipe data
        recipe_name = data.get('name', 'AI Generated Recipe')
        batch_size = float(data.get('batch_size', 20))
        style_name = data.get('style_name', 'American IPA')
        constraints = data.get('constraints', '')
        
        # Get or create beer style
        style = None
        try:
            # Try to find exact match first
            style = BeerStyle.objects.get(name__iexact=style_name)
        except BeerStyle.DoesNotExist:
            try:
                # Try partial match
                style = BeerStyle.objects.filter(name__icontains=style_name).first()
            except:
                pass
        
        # If no style found, create a default one or use first available
        if not style:
            style = BeerStyle.objects.first()
            if not style:
                # Create a default style if none exists
                style = BeerStyle.objects.create(
                    name=style_name,
                    style_code='AI',
                    description=f'AI generated style for {style_name}',
                    og_min=1.040,
                    og_max=1.070,
                    fg_min=1.008,
                    fg_max=1.020,
                    ibu_min=20,
                    ibu_max=60,
                    srm_min=3,
                    srm_max=30,
                    abv_min=4.0,
                    abv_max=7.0
                )
        
        # Create the recipe
        recipe = Recipe.objects.create(
            name=recipe_name,
            description=f"AI-generated recipe for {style_name}. Constraints: {constraints}",
            style=style,
            batch_size=batch_size,
            efficiency=75.0,  # Default efficiency
            created_by=request.user,
            notes=data.get('brewing_instructions', ''),
            is_public=False
        )
        
        # Set expected calculated values if provided
        expected_stats = data.get('expected_stats', {})
        if expected_stats:
            recipe.calculated_og = expected_stats.get('og')
            recipe.calculated_fg = expected_stats.get('fg')
            recipe.calculated_ibu = expected_stats.get('ibu')
            recipe.calculated_abv = expected_stats.get('abv')
            recipe.calculated_srm = expected_stats.get('srm')
        
        # Add grain additions
        grain_bill = data.get('grain_bill', [])
        grains_added = 0
        for grain_data in grain_bill:
            grain_name = grain_data.get('name', '')
            weight_kg = float(grain_data.get('weight_kg', 0))
            percentage = grain_data.get('percentage', 0)
            
            if weight_kg <= 0:
                continue
                
            # Try to find matching grain in database
            grain = find_or_create_grain(grain_name)
            
            if grain:
                # Create grain addition
                GrainAddition.objects.create(
                    recipe=recipe,
                    grain=grain,
                    weight=weight_kg,
                    percentage=percentage
                )
                grains_added += 1
        
        # Add hop additions
        hop_schedule = data.get('hop_schedule', [])
        hops_added = 0
        for hop_data in hop_schedule:
            hop_name = hop_data.get('name', '')
            weight_g = hop_data.get('weight_g', 0)
            boil_time = hop_data.get('boil_time', 60)
            use = hop_data.get('use', 'boil')
            
            if weight_g <= 0:
                continue
            
            # Convert grams to kg
            weight_kg = weight_g / 1000.0
            
            # Try to find matching hop
            hop = find_or_create_hop(hop_name)
            
            if hop:
                # Create hop addition
                HopAddition.objects.create(
                    recipe=recipe,
                    hop=hop,
                    weight=weight_kg,
                    boil_time=boil_time,
                    use=use
                )
                hops_added += 1
        
        # Add yeast
        yeast_data = data.get('yeast', {})
        yeast_added = 0
        if yeast_data:
            yeast_name = yeast_data.get('name', 'US-05')
            amount = float(yeast_data.get('amount', '1').split()[0])  # Extract number from "1 packet"
            
            # Try to find matching yeast
            yeast = find_or_create_yeast(yeast_name)
            
            if yeast:
                # Create yeast addition
                YeastAddition.objects.create(
                    recipe=recipe,
                    yeast=yeast,
                    amount=amount
                )
                yeast_added = 1
        
        # Save recipe with updated values
        recipe.save()
        
        # Recalculate recipe values if ingredients were added
        if grains_added > 0 or hops_added > 0:
            recipe.calculate_all_values()
        
        return JsonResponse({
            'success': True,
            'recipe_id': recipe.pk,
            'message': f'Recipe "{recipe.name}" saved successfully!',
            'details': {
                'grains_added': grains_added,
                'hops_added': hops_added,
                'yeast_added': yeast_added,
                'recipe_url': f'/recipes/{recipe.pk}/'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        })
    except Exception as e:
        # Log the error for debugging
        print(f"Error saving AI recipe: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error saving recipe: {str(e)}'
        })

# UTILITY FUNCTIONS FOR AI INGREDIENT MATCHING

def find_or_create_grain(grain_name):
    """Find or create grain based on name"""
    # Try exact match first
    try:
        return Grain.objects.get(name__iexact=grain_name)
    except Grain.DoesNotExist:
        pass
    
    # Try partial match
    try:
        return Grain.objects.filter(name__icontains=grain_name.split()[0]).first()
    except:
        pass
    
    # Create new grain if not found
    try:
        # Determine grain type based on name
        grain_type = 'base'
        color = 2
        extract_potential = 37
        
        grain_lower = grain_name.lower()
        if any(word in grain_lower for word in ['crystal', 'caramel']):
            grain_type = 'crystal'
            color = 40
            extract_potential = 34
        elif any(word in grain_lower for word in ['chocolate', 'roasted', 'black']):
            grain_type = 'roasted'
            color = 300
            extract_potential = 32
        elif 'munich' in grain_lower:
            grain_type = 'base'
            color = 9
            extract_potential = 37
        
        return Grain.objects.create(
            name=grain_name,
            grain_type=grain_type,
            color=color,
            extract_potential=extract_potential,
            description=f'AI generated grain: {grain_name}'
        )
    except:
        return None

def find_or_create_hop(hop_name):
    """Find or create hop based on name"""
    # Try exact match first
    try:
        return Hop.objects.get(name__iexact=hop_name)
    except Hop.DoesNotExist:
        pass
    
    # Try partial match
    try:
        return Hop.objects.filter(name__icontains=hop_name.split()[0]).first()
    except:
        pass
    
    # Create new hop if not found
    try:
        # Determine hop type and alpha acid based on name
        hop_type = 'dual'
        alpha_acid = 5.0
        
        hop_lower = hop_name.lower()
        if any(word in hop_lower for word in ['chinook', 'magnum', 'warrior']):
            hop_type = 'bittering'
            alpha_acid = 12.0
        elif any(word in hop_lower for word in ['citra', 'mosaic', 'amarillo']):
            hop_type = 'aroma'
            alpha_acid = 8.0
        elif any(word in hop_lower for word in ['cascade', 'centennial']):
            hop_type = 'dual'
            alpha_acid = 6.0
        
        return Hop.objects.create(
            name=hop_name,
            hop_type=hop_type,
            alpha_acid=alpha_acid,
            description=f'AI generated hop: {hop_name}'
        )
    except:
        return None

def find_or_create_yeast(yeast_name):
    """Find or create yeast based on name"""
    # Try partial match first
    try:
        return Yeast.objects.filter(name__icontains=yeast_name.split()[0]).first()
    except:
        pass
    
    # Create new yeast if not found
    try:
        # Determine yeast properties based on name
        yeast_type = 'ale'
        attenuation = 75.0
        temp_min = 18
        temp_max = 24
        laboratory = 'Generic'
        strain_number = 'AI-001'
        
        yeast_lower = yeast_name.lower()
        if 'lager' in yeast_lower:
            yeast_type = 'lager'
            attenuation = 80.0
            temp_min = 10
            temp_max = 15
        elif 'wheat' in yeast_lower:
            yeast_type = 'wheat'
            attenuation = 72.0
        elif 'us-05' in yeast_lower:
            laboratory = 'Safale'
            strain_number = 'US-05'
        elif 's-04' in yeast_lower:
            laboratory = 'Safale'
            strain_number = 'S-04'
            attenuation = 78.0
        
        return Yeast.objects.create(
            name=yeast_name,
            laboratory=laboratory,
            strain_number=strain_number,
            yeast_type=yeast_type,
            attenuation=attenuation,
            temp_range_min=temp_min,
            temp_range_max=temp_max,
            description=f'AI generated yeast: {yeast_name}'
        )
    except:
        return None
    
@login_required
def save_generated_recipe(request):
    """Save a generated recipe to the database"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get or create a default beer style
            style, created = BeerStyle.objects.get_or_create(
                name=data['style_name'],
                defaults={
                    'style_code': 'GEN',
                    'description': f"Generated {data['style_name']}",
                    'og_min': data['stats']['og'] - 0.005,
                    'og_max': data['stats']['og'] + 0.005,
                    'fg_min': data['stats']['fg'] - 0.003,
                    'fg_max': data['stats']['fg'] + 0.003,
                    'ibu_min': data['stats']['ibu'] - 5,
                    'ibu_max': data['stats']['ibu'] + 5,
                    'srm_min': max(1, data['stats']['srm'] - 2),
                    'srm_max': data['stats']['srm'] + 2,
                    'abv_min': data['stats']['abv'] - 0.5,
                    'abv_max': data['stats']['abv'] + 0.5,
                }
            )
            
            # Create the recipe
            recipe = Recipe.objects.create(
                name=data['name'],
                description=f"Generated recipe: {data['style_name']}",
                style=style,
                batch_size=data['batch_size'],
                efficiency=data['efficiency'],
                created_by=request.user,
                notes="\n".join(data['instructions'])
            )
            
            # Add grain additions
            for grain_data in data['grain_bill']:
                # Try to find existing grain or create new one
                grain, created = Grain.objects.get_or_create(
                    name=grain_data['name'],
                    defaults={
                        'grain_type': get_grain_type(grain_data['name']),
                        'color': get_grain_color(grain_data['name']),
                        'extract_potential': 37,  # Default
                        'description': f"Generated grain: {grain_data['name']}"
                    }
                )
                
                GrainAddition.objects.create(
                    recipe=recipe,
                    grain=grain,
                    weight=grain_data['weight'],
                    percentage=grain_data['percentage']
                )
            
            # Add hop additions
            for hop_data in data['hop_schedule']:
                hop, created = Hop.objects.get_or_create(
                    name=hop_data['name'],
                    defaults={
                        'hop_type': get_hop_type(hop_data['name']),
                        'alpha_acid': get_hop_alpha(hop_data['name']),
                        'description': f"Generated hop: {hop_data['name']}"
                    }
                )
                
                HopAddition.objects.create(
                    recipe=recipe,
                    hop=hop,
                    weight=hop_data['weight'] / 1000,  # Convert g to kg
                    boil_time=hop_data['time'],
                    use='boil' if hop_data['time'] > 0 else 'dry_hop'
                )
            
            # Add yeast
            yeast_name = data['yeast'].split()[0] + ' ' + data['yeast'].split()[1]
            yeast, created = Yeast.objects.get_or_create(
                name=yeast_name,
                defaults={
                    'laboratory': 'Safale',
                    'strain_number': yeast_name.split()[-1],
                    'yeast_type': 'ale',
                    'attenuation': 75.0,
                    'temp_range_min': 18,
                    'temp_range_max': 24,
                    'description': f"Generated yeast: {yeast_name}"
                }
            )
            
            YeastAddition.objects.create(
                recipe=recipe,
                yeast=yeast,
                amount=1.0
            )
            
            # Calculate final recipe values
            recipe.calculate_all_values()
            
            return JsonResponse({
                'success': True,
                'recipe_id': recipe.id,
                'redirect_url': f'/recipes/{recipe.id}/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_grain_type(name):
    """Determine grain type from name"""
    name_lower = name.lower()
    if 'crystal' in name_lower or 'caramel' in name_lower:
        return 'crystal'
    elif 'chocolate' in name_lower or 'roasted' in name_lower or 'black' in name_lower:
        return 'roasted'
    elif 'munich' in name_lower or 'vienna' in name_lower:
        return 'base'
    elif 'wheat' in name_lower:
        return 'base'
    else:
        return 'base'

def get_grain_color(name):
    """Estimate grain color from name"""
    name_lower = name.lower()
    if 'black' in name_lower:
        return 500
    elif 'chocolate' in name_lower:
        return 350
    elif 'roasted' in name_lower:
        return 300
    elif 'crystal' in name_lower:
        if '120' in name_lower:
            return 120
        elif '80' in name_lower:
            return 80
        elif '60' in name_lower:
            return 60
        elif '40' in name_lower:
            return 40
        elif '20' in name_lower:
            return 20
        else:
            return 40  # Default crystal
    elif 'munich' in name_lower:
        return 9
    elif 'vienna' in name_lower:
        return 3
    else:
        return 2  # Base malt default

def get_hop_type(name):
    """Determine hop type from name"""
    bittering_hops = ['magnum', 'warrior', 'chinook', 'columbus']
    aroma_hops = ['citra', 'mosaic', 'amarillo', 'cascade']
    
    name_lower = name.lower()
    if any(h in name_lower for h in bittering_hops):
        return 'bittering'
    elif any(h in name_lower for h in aroma_hops):
        return 'aroma'
    else:
        return 'dual'

def get_hop_alpha(name):
    """Estimate alpha acid from hop name"""
    alpha_acids = {
        'magnum': 12.0,
        'warrior': 15.0,
        'chinook': 13.0,
        'columbus': 14.0,
        'cascade': 5.5,
        'centennial': 10.0,
        'citra': 12.0,
        'mosaic': 11.5,
        'amarillo': 9.0,
    }
    
    name_lower = name.lower()
    for hop, alpha in alpha_acids.items():
        if hop in name_lower:
            return alpha
    
    return 8.0  # Default