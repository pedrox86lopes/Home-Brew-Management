import json
import requests
from django.conf import settings
from .models import Recipe, Grain, Hop, Yeast, GrainAddition, HopAddition, YeastAddition
from core.models import BeerStyle, BrewingCalculator
import openai  # or any other AI API

class AIRecipeGenerator:
    """
    AI-powered recipe generator that creates recipes based on batch size,
    style preferences, and available ingredients.
    """
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if hasattr(settings, 'OPENAI_API_KEY') else None
    
    def generate_recipe_with_claude(self, batch_size_liters, style_name, constraints=None):
        """
        Generate recipe using Claude API (if available in your environment)
        """
        if not hasattr(window, 'claude'):
            return self.generate_recipe_with_formulas(batch_size_liters, style_name, constraints)
        
        # Get style information
        try:
            style = BeerStyle.objects.get(name__icontains=style_name)
        except BeerStyle.DoesNotExist:
            style = BeerStyle.objects.first()  # Fallback
        
        # Get available ingredients
        available_grains = list(Grain.objects.values('name', 'grain_type', 'color', 'extract_potential'))
        available_hops = list(Hop.objects.values('name', 'hop_type', 'alpha_acid'))
        available_yeasts = list(Yeast.objects.values('name', 'laboratory', 'strain_number', 'attenuation'))
        
        prompt = f"""
        Create a detailed brewing recipe for {batch_size_liters}L of {style.name} beer.
        
        Style Guidelines:
        - OG: {style.og_min}-{style.og_max}
        - FG: {style.fg_min}-{style.fg_max}
        - IBU: {style.ibu_min}-{style.ibu_max}
        - SRM: {style.srm_min}-{style.srm_max}
        - ABV: {style.abv_min}-{style.abv_max}%
        
        Available Grains: {json.dumps(available_grains[:10])}
        Available Hops: {json.dumps(available_hops[:10])}
        Available Yeasts: {json.dumps(available_yeasts[:5])}
        
        Constraints: {constraints or "None"}
        
        Respond with a JSON object containing:
        {{
            "recipe_name": "Generated Recipe Name",
            "grain_bill": [
                {{"grain_name": "name", "weight_kg": 0.0, "percentage": 0.0}}
            ],
            "hop_schedule": [
                {{"hop_name": "name", "weight_kg": 0.0, "boil_time_minutes": 0, "use": "boil"}}
            ],
            "yeast": {{"yeast_name": "name", "amount": 1.0}},
            "expected_og": 0.000,
            "expected_fg": 0.000,
            "expected_ibu": 0,
            "expected_abv": 0.0,
            "brewing_notes": "Step by step instructions"
        }}
        
        Make sure the grain bill totals approximately 100% and targets the style's OG range.
        Calculate hop additions to hit the IBU target.
        """
        
        try:
            # This would use Claude API if available
            response = window.claude.complete(prompt)
            recipe_data = json.loads(response)
            return self.create_recipe_from_ai_response(recipe_data, style, batch_size_liters)
        except:
            # Fallback to formula-based generation
            return self.generate_recipe_with_formulas(batch_size_liters, style_name, constraints)
    
    def generate_recipe_with_openai(self, batch_size_liters, style_name, constraints=None):
        """
        Generate recipe using OpenAI API
        """
        if not self.openai_client:
            return self.generate_recipe_with_formulas(batch_size_liters, style_name, constraints)
        
        try:
            style = BeerStyle.objects.get(name__icontains=style_name)
        except BeerStyle.DoesNotExist:
            style = BeerStyle.objects.first()
        
        available_grains = list(Grain.objects.values('name', 'grain_type', 'color', 'extract_potential'))
        available_hops = list(Hop.objects.values('name', 'hop_type', 'alpha_acid'))
        available_yeasts = list(Yeast.objects.values('name', 'laboratory', 'strain_number', 'attenuation'))
        
        prompt = f"""
        You are an expert brewer. Create a detailed BIAB (Brew-in-a-Bag) recipe for {batch_size_liters}L of {style.name}.
        
        Style Requirements:
        - Original Gravity: {style.og_min}-{style.og_max}
        - Final Gravity: {style.fg_min}-{style.fg_max}
        - IBU: {style.ibu_min}-{style.ibu_max}
        - Color: {style.srm_min}-{style.srm_max} SRM
        - ABV: {style.abv_min}-{style.abv_max}%
        
        Available Ingredients:
        Grains: {', '.join([g['name'] for g in available_grains[:10]])}
        Hops: {', '.join([h['name'] for h in available_hops[:10]])}
        Yeasts: {', '.join([y['name'] for y in available_yeasts[:5]])}
        
        Additional Constraints: {constraints or "None"}
        
        Provide response as JSON with exact format:
        {{
            "recipe_name": "Recipe Name",
            "grain_bill": [
                {{"grain_name": "Grain Name", "weight_kg": 4.5, "percentage": 85.0}}
            ],
            "hop_schedule": [
                {{"hop_name": "Hop Name", "weight_kg": 0.025, "boil_time_minutes": 60, "use": "boil"}}
            ],
            "yeast": {{"yeast_name": "Yeast Name", "amount": 1.0}},
            "expected_og": 1.050,
            "expected_fg": 1.012,
            "expected_ibu": 35,
            "expected_abv": 5.2,
            "brewing_notes": "Detailed brewing instructions"
        }}
        
        Calculate exact weights to hit the target OG for {batch_size_liters}L at 75% efficiency.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert brewing recipe generator. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            recipe_data = json.loads(response.choices[0].message.content)
            return self.create_recipe_from_ai_response(recipe_data, style, batch_size_liters)
            
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self.generate_recipe_with_formulas(batch_size_liters, style_name, constraints)
    
    def generate_recipe_with_formulas(self, batch_size_liters, style_name, constraints=None):
        """
        Fallback: Generate recipe using brewing formulas and algorithms
        """
        try:
            style = BeerStyle.objects.get(name__icontains=style_name)
        except BeerStyle.DoesNotExist:
            style = BeerStyle.objects.first()
        
        # Target values (middle of style range)
        target_og = (style.og_min + style.og_max) / 2
        target_ibu = (style.ibu_min + style.ibu_max) / 2
        target_srm = (style.srm_min + style.srm_max) / 2
        
        # Calculate total grain needed
        efficiency = 0.75  # 75% efficiency
        total_points_needed = (target_og - 1) * batch_size_liters * 1000
        
        # Generate grain bill
        grain_bill = self.generate_smart_grain_bill(total_points_needed, target_srm, batch_size_liters, efficiency)
        
        # Generate hop schedule
        hop_schedule = self.generate_smart_hop_schedule(target_ibu, batch_size_liters, target_og)
        
        # Select yeast
        yeast_selection = self.select_appropriate_yeast(style)
        
        # Create recipe data
        recipe_data = {
            "recipe_name": f"AI Generated {style.name}",
            "grain_bill": grain_bill,
            "hop_schedule": hop_schedule,
            "yeast": yeast_selection,
            "expected_og": target_og,
            "expected_fg": target_og - ((target_og - 1) * 0.75),  # Assume 75% attenuation
            "expected_ibu": target_ibu,
            "expected_abv": BrewingCalculator.calculate_abv(target_og, target_og - ((target_og - 1) * 0.75)),
            "brewing_notes": self.generate_brewing_notes(batch_size_liters, grain_bill)
        }
        
        return self.create_recipe_from_ai_response(recipe_data, style, batch_size_liters)
    
    def generate_smart_grain_bill(self, total_points_needed, target_srm, batch_size_liters, efficiency):
        """
        Generate an intelligent grain bill based on target parameters
        """
        grain_bill = []
        
        # Base malt (70-85% of bill)
        base_malts = Grain.objects.filter(grain_type='base', color__lte=10)
        if base_malts.exists():
            base_malt = base_malts.first()
            base_percentage = 80.0
            base_points = total_points_needed * (base_percentage / 100)
            base_weight = base_points / (base_malt.extract_potential * efficiency) / 2.2  # Convert to kg
            
            grain_bill.append({
                "grain_name": base_malt.name,
                "weight_kg": round(base_weight, 2),
                "percentage": base_percentage
            })
        
        # Specialty malts based on target color
        remaining_percentage = 20.0
        remaining_points = total_points_needed * 0.2
        
        if target_srm > 20:  # Dark beer
            dark_grains = Grain.objects.filter(grain_type__in=['roasted', 'crystal'], color__gte=100)
            if dark_grains.exists():
                dark_grain = dark_grains.first()
                dark_percentage = 5.0
                dark_weight = (remaining_points * (dark_percentage / remaining_percentage)) / (dark_grain.extract_potential * efficiency) / 2.2
                
                grain_bill.append({
                    "grain_name": dark_grain.name,
                    "weight_kg": round(dark_weight, 3),
                    "percentage": dark_percentage
                })
                remaining_percentage -= dark_percentage
        
        if target_srm > 5:  # Add crystal malt for color and flavor
            crystal_grains = Grain.objects.filter(grain_type='crystal', color__range=(30, 100))
            if crystal_grains.exists():
                crystal_grain = crystal_grains.first()
                crystal_percentage = min(15.0, remaining_percentage)
                crystal_weight = (remaining_points * (crystal_percentage / 20.0)) / (crystal_grain.extract_potential * efficiency) / 2.2
                
                grain_bill.append({
                    "grain_name": crystal_grain.name,
                    "weight_kg": round(crystal_weight, 3),
                    "percentage": crystal_percentage
                })
        
        return grain_bill
    
    def generate_smart_hop_schedule(self, target_ibu, batch_size_liters, og):
        """
        Generate hop schedule to hit target IBU
        """
        hop_schedule = []
        
        # Bittering addition (60 min) - 70% of IBU
        bittering_hops = Hop.objects.filter(hop_type__in=['bittering', 'dual']).order_by('-alpha_acid')
        if bittering_hops.exists():
            bittering_hop = bittering_hops.first()
            bittering_ibu = target_ibu * 0.7
            bittering_weight = self.calculate_hop_weight_for_ibu(
                bittering_ibu, bittering_hop.alpha_acid, 60, batch_size_liters, og
            ) / 1000  # Convert to kg
            
            hop_schedule.append({
                "hop_name": bittering_hop.name,
                "weight_kg": round(bittering_weight, 3),
                "boil_time_minutes": 60,
                "use": "boil"
            })
        
        # Flavor addition (15 min) - 20% of IBU
        flavor_hops = Hop.objects.filter(hop_type__in=['aroma', 'dual'])
        if flavor_hops.exists():
            flavor_hop = flavor_hops.first()
            flavor_ibu = target_ibu * 0.2
            flavor_weight = self.calculate_hop_weight_for_ibu(
                flavor_ibu, flavor_hop.alpha_acid, 15, batch_size_liters, og
            ) / 1000
            
            hop_schedule.append({
                "hop_name": flavor_hop.name,
                "weight_kg": round(flavor_weight, 3),
                "boil_time_minutes": 15,
                "use": "boil"
            })
        
        # Aroma addition (5 min) - 10% of IBU
        aroma_hops = Hop.objects.filter(hop_type='aroma')
        if aroma_hops.exists():
            aroma_hop = aroma_hops.first()
            aroma_ibu = target_ibu * 0.1
            aroma_weight = self.calculate_hop_weight_for_ibu(
                aroma_ibu, aroma_hop.alpha_acid, 5, batch_size_liters, og
            ) / 1000
            
            hop_schedule.append({
                "hop_name": aroma_hop.name,
                "weight_kg": round(aroma_weight, 3),
                "boil_time_minutes": 5,
                "use": "boil"
            })
        
        return hop_schedule
    
    def calculate_hop_weight_for_ibu(self, target_ibu, alpha_acid, boil_time, batch_size, og):
        """
        Calculate hop weight needed for target IBU using Tinseth formula
        """
        return BrewingCalculator.calculate_hop_weight_for_ibu(target_ibu, alpha_acid, boil_time, batch_size, og)
    
    def select_appropriate_yeast(self, style):
        """
        Select appropriate yeast for the style
        """
        # Simple yeast selection logic
        if 'lager' in style.name.lower():
            yeast = Yeast.objects.filter(yeast_type='lager').first()
        elif 'wheat' in style.name.lower():
            yeast = Yeast.objects.filter(yeast_type__in=['wheat', 'ale']).first()
        else:
            yeast = Yeast.objects.filter(yeast_type='ale').first()
        
        if yeast:
            return {
                "yeast_name": yeast.name,
                "amount": 1.0
            }
        
        return {"yeast_name": "Generic Ale Yeast", "amount": 1.0}
    
    def generate_brewing_notes(self, batch_size_liters, grain_bill):
        """
        Generate BIAB-specific brewing notes
        """
        total_grain_weight = sum(grain['weight_kg'] for grain in grain_bill)
        water_needed = batch_size_liters + (total_grain_weight * 0.96)  # Grain absorption
        strike_temp = BrewingCalculator.calculate_strike_water_temp(20, 67, water_needed/total_grain_weight)
        
        notes = f"""
        BIAB Brewing Instructions for {batch_size_liters}L batch:
        
        1. Heat {water_needed:.1f}L water to {strike_temp:.1f}°C (strike temperature)
        2. Add grain bag with {total_grain_weight:.2f}kg total grain
        3. Mash at 67°C for 60 minutes
        4. Raise temperature to 76°C for mash out (10 minutes)
        5. Remove grain bag and allow to drain
        6. Bring wort to a rolling boil
        7. Follow hop schedule for additions
        8. Cool to 20°C and transfer to fermenter
        9. Pitch yeast and ferment at appropriate temperature
        
        Expected pre-boil volume: {water_needed:.1f}L
        Expected post-boil volume: {batch_size_liters}L
        """
        
        return notes.strip()
    
    def create_recipe_from_ai_response(self, recipe_data, style, batch_size_liters, user):
        """
        Create Django recipe object from AI response
        """
        # Create the recipe
        recipe = Recipe.objects.create(
            name=recipe_data['recipe_name'],
            description=f"AI-generated recipe for {style.name}",
            style=style,
            batch_size=batch_size_liters,
            efficiency=75.0,
            created_by=user,
            notes=recipe_data.get('brewing_notes', '')
        )
        
        # Add grain additions
        for grain_data in recipe_data['grain_bill']:
            try:
                grain = Grain.objects.get(name=grain_data['grain_name'])
                GrainAddition.objects.create(
                    recipe=recipe,
                    grain=grain,
                    weight=grain_data['weight_kg'],
                    percentage=grain_data.get('percentage')
                )
            except Grain.DoesNotExist:
                print(f"Grain not found: {grain_data['grain_name']}")
        
        # Add hop additions
        for hop_data in recipe_data['hop_schedule']:
            try:
                hop = Hop.objects.get(name=hop_data['hop_name'])
                HopAddition.objects.create(
                    recipe=recipe,
                    hop=hop,
                    weight=hop_data['weight_kg'],
                    boil_time=hop_data['boil_time_minutes'],
                    use=hop_data.get('use', 'boil')
                )
            except Hop.DoesNotExist:
                print(f"Hop not found: {hop_data['hop_name']}")
        
        # Add yeast
        yeast_data = recipe_data['yeast']
        try:
            yeast = Yeast.objects.filter(name__icontains=yeast_data['yeast_name']).first()
            if yeast:
                YeastAddition.objects.create(
                    recipe=recipe,
                    yeast=yeast,
                    amount=yeast_data['amount']
                )
        except:
            print(f"Yeast not found: {yeast_data['yeast_name']}")
        
        # Calculate final recipe values
        recipe.calculate_all_values()
        
        return recipe