from django.core.management.base import BaseCommand
from recipes.models import Grain, Hop, Yeast
from core.models import BeerStyle

class Command(BaseCommand):
    help = 'Populate database with common brewing ingredients and beer styles'

    def handle(self, *args, **options):
        self.stdout.write('Populating brewing ingredients...')
        
        # Create beer styles
        self.create_beer_styles()
        
        # Create grains
        self.create_grains()
        
        # Create hops
        self.create_hops()
        
        # Create yeasts
        self.create_yeasts()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated brewing ingredients!')
        )

    def create_beer_styles(self):
        """Create common beer styles"""
        styles = [
            {
                'name': 'American IPA',
                'style_code': '21A',
                'description': 'A decidedly hoppy and bitter, moderately strong American pale ale.',
                'og_min': 1.056, 'og_max': 1.070,
                'fg_min': 1.008, 'fg_max': 1.014,
                'ibu_min': 40, 'ibu_max': 70,
                'srm_min': 6, 'srm_max': 14,
                'abv_min': 5.5, 'abv_max': 7.5
            },
            {
                'name': 'American Pale Ale',
                'style_code': '18B',
                'description': 'A pale, refreshing and hoppy ale, yet with sufficient supporting malt to make the beer balanced and drinkable.',
                'og_min': 1.045, 'og_max': 1.060,
                'fg_min': 1.010, 'fg_max': 1.015,
                'ibu_min': 30, 'ibu_max': 50,
                'srm_min': 5, 'srm_max': 10,
                'abv_min': 4.5, 'abv_max': 6.2
            },
            {
                'name': 'American Wheat Beer',
                'style_code': '1D',
                'description': 'Refreshing wheat beers that can display more hop character than traditional European wheat beers.',
                'og_min': 1.040, 'og_max': 1.055,
                'fg_min': 1.008, 'fg_max': 1.013,
                'ibu_min': 15, 'ibu_max': 30,
                'srm_min': 3, 'srm_max': 6,
                'abv_min': 4.0, 'abv_max': 5.5
            },
            {
                'name': 'American Porter',
                'style_code': '20A',
                'description': 'A substantial, malty dark beer with a complex and flavorful dark malt character.',
                'og_min': 1.050, 'og_max': 1.070,
                'fg_min': 1.012, 'fg_max': 1.018,
                'ibu_min': 25, 'ibu_max': 50,
                'srm_min': 22, 'srm_max': 40,
                'abv_min': 4.8, 'abv_max': 6.5
            },
            {
                'name': 'American Stout',
                'style_code': '20B',
                'description': 'A fairly strong, highly roasted, bitter, hoppy dark stout.',
                'og_min': 1.050, 'og_max': 1.075,
                'fg_min': 1.010, 'fg_max': 1.022,
                'ibu_min': 35, 'ibu_max': 75,
                'srm_min': 30, 'srm_max': 40,
                'abv_min': 5.0, 'abv_max': 9.0
            }
        ]
        
        for style_data in styles:
            style, created = BeerStyle.objects.get_or_create(
                style_code=style_data['style_code'],
                defaults=style_data
            )
            if created:
                self.stdout.write(f'Created beer style: {style.name}')

    def create_grains(self):
        """Create common grains"""
        grains = [
            # Base Malts
            {'name': '2-Row Pale Malt', 'grain_type': 'base', 'color': 2, 'extract_potential': 37},
            {'name': '6-Row Pale Malt', 'grain_type': 'base', 'color': 2, 'extract_potential': 35},
            {'name': 'Pilsner Malt', 'grain_type': 'base', 'color': 2, 'extract_potential': 37},
            {'name': 'Wheat Malt', 'grain_type': 'base', 'color': 2, 'extract_potential': 38},
            {'name': 'Munich Malt', 'grain_type': 'base', 'color': 9, 'extract_potential': 37},
            {'name': 'Vienna Malt', 'grain_type': 'base', 'color': 3, 'extract_potential': 36},
            
            # Crystal/Caramel Malts
            {'name': 'Crystal 20L', 'grain_type': 'crystal', 'color': 20, 'extract_potential': 35},
            {'name': 'Crystal 40L', 'grain_type': 'crystal', 'color': 40, 'extract_potential': 34},
            {'name': 'Crystal 60L', 'grain_type': 'crystal', 'color': 60, 'extract_potential': 34},
            {'name': 'Crystal 80L', 'grain_type': 'crystal', 'color': 80, 'extract_potential': 34},
            {'name': 'Crystal 120L', 'grain_type': 'crystal', 'color': 120, 'extract_potential': 33},
            
            # Specialty Malts
            {'name': 'Chocolate Malt', 'grain_type': 'roasted', 'color': 350, 'extract_potential': 32},
            {'name': 'Black Patent Malt', 'grain_type': 'roasted', 'color': 500, 'extract_potential': 30},
            {'name': 'Roasted Barley', 'grain_type': 'roasted', 'color': 300, 'extract_potential': 30},
            {'name': 'Special B', 'grain_type': 'crystal', 'color': 180, 'extract_potential': 33},
            {'name': 'Biscuit Malt', 'grain_type': 'specialty', 'color': 23, 'extract_potential': 35},
            {'name': 'Victory Malt', 'grain_type': 'specialty', 'color': 25, 'extract_potential': 34},
            {'name': 'Honey Malt', 'grain_type': 'specialty', 'color': 25, 'extract_potential': 37},
            
            # Adjuncts
            {'name': 'Flaked Oats', 'grain_type': 'adjunct', 'color': 1, 'extract_potential': 33},
            {'name': 'Flaked Wheat', 'grain_type': 'adjunct', 'color': 2, 'extract_potential': 36},
            {'name': 'Rice Hulls', 'grain_type': 'adjunct', 'color': 1, 'extract_potential': 0},
        ]
        
        for grain_data in grains:
            grain_data['description'] = f"Common brewing grain: {grain_data['name']}"
            grain, created = Grain.objects.get_or_create(
                name=grain_data['name'],
                defaults=grain_data
            )
            if created:
                self.stdout.write(f'Created grain: {grain.name}')

    def create_hops(self):
        """Create common hops"""
        hops = [
            # Bittering Hops
            {'name': 'Magnum', 'hop_type': 'bittering', 'alpha_acid': 12.0},
            {'name': 'Warrior', 'hop_type': 'bittering', 'alpha_acid': 15.0},
            {'name': 'Chinook', 'hop_type': 'bittering', 'alpha_acid': 13.0},
            {'name': 'Columbus', 'hop_type': 'bittering', 'alpha_acid': 14.0},
            
            # Aroma Hops
            {'name': 'Cascade', 'hop_type': 'aroma', 'alpha_acid': 5.5},
            {'name': 'Centennial', 'hop_type': 'aroma', 'alpha_acid': 10.0},
            {'name': 'Citra', 'hop_type': 'aroma', 'alpha_acid': 12.0},
            {'name': 'Mosaic', 'hop_type': 'aroma', 'alpha_acid': 11.5},
            {'name': 'Amarillo', 'hop_type': 'aroma', 'alpha_acid': 9.0},
            {'name': 'Simcoe', 'hop_type': 'aroma', 'alpha_acid': 13.0},
            {'name': 'Galaxy', 'hop_type': 'aroma', 'alpha_acid': 13.0},
            {'name': 'Nelson Sauvin', 'hop_type': 'aroma', 'alpha_acid': 12.0},
            
            # Dual Purpose
            {'name': 'Willamette', 'hop_type': 'dual', 'alpha_acid': 5.0},
            {'name': 'Fuggle', 'hop_type': 'dual', 'alpha_acid': 4.5},
            {'name': 'East Kent Goldings', 'hop_type': 'dual', 'alpha_acid': 5.0},
            {'name': 'Hallertau', 'hop_type': 'dual', 'alpha_acid': 4.0},
            {'name': 'Saaz', 'hop_type': 'dual', 'alpha_acid': 3.5},
            
            # Modern Varieties
            {'name': 'Azacca', 'hop_type': 'aroma', 'alpha_acid': 14.0},
            {'name': 'El Dorado', 'hop_type': 'aroma', 'alpha_acid': 15.0},
            {'name': 'Idaho 7', 'hop_type': 'dual', 'alpha_acid': 13.0},
        ]
        
        for hop_data in hops:
            hop_data['description'] = f"Common brewing hop: {hop_data['name']}"
            hop, created = Hop.objects.get_or_create(
                name=hop_data['name'],
                defaults=hop_data
            )
            if created:
                self.stdout.write(f'Created hop: {hop.name}')

    def create_yeasts(self):
        """Create common yeasts"""
        yeasts = [
            # Ale Yeasts
            {
                'name': 'American Ale',
                'laboratory': 'Safale',
                'strain_number': 'US-05',
                'yeast_type': 'ale',
                'attenuation': 78.0,
                'temp_range_min': 15,
                'temp_range_max': 24
            },
            {
                'name': 'English Ale',
                'laboratory': 'Safale',
                'strain_number': 'S-04',
                'yeast_type': 'ale',
                'attenuation': 75.0,
                'temp_range_min': 15,
                'temp_range_max': 22
            },
            {
                'name': 'Belgian Ale',
                'laboratory': 'Safale',
                'strain_number': 'T-58',
                'yeast_type': 'ale',
                'attenuation': 80.0,
                'temp_range_min': 15,
                'temp_range_max': 25
            },
            
            # Wheat Yeasts
            {
                'name': 'Wheat Beer',
                'laboratory': 'Safale',
                'strain_number': 'WB-06',
                'yeast_type': 'wheat',
                'attenuation': 73.0,
                'temp_range_min': 15,
                'temp_range_max': 24
            },
            
            # Lager Yeasts
            {
                'name': 'Lager',
                'laboratory': 'Saflager',
                'strain_number': 'S-23',
                'yeast_type': 'lager',
                'attenuation': 82.0,
                'temp_range_min': 9,
                'temp_range_max': 15
            },
            {
                'name': 'Lager West European',
                'laboratory': 'Saflager',
                'strain_number': 'W-34/70',
                'yeast_type': 'lager',
                'attenuation': 83.0,
                'temp_range_min': 9,
                'temp_range_max': 15
            },
            
            # Liquid Yeasts (Wyeast)
            {
                'name': 'American Ale',
                'laboratory': 'Wyeast',
                'strain_number': '1056',
                'yeast_type': 'ale',
                'attenuation': 77.0,
                'temp_range_min': 16,
                'temp_range_max': 22
            },
            {
                'name': 'California Ale',
                'laboratory': 'Wyeast',
                'strain_number': '1214',
                'yeast_type': 'ale',
                'attenuation': 73.0,
                'temp_range_min': 16,
                'temp_range_max': 21
            },
            
            # Liquid Yeasts (White Labs)
            {
                'name': 'California Ale',
                'laboratory': 'White Labs',
                'strain_number': 'WLP001',
                'yeast_type': 'ale',
                'attenuation': 76.0,
                'temp_range_min': 18,
                'temp_range_max': 23
            },
            {
                'name': 'English Ale',
                'laboratory': 'White Labs',
                'strain_number': 'WLP002',
                'yeast_type': 'ale',
                'attenuation': 68.0,
                'temp_range_min': 18,
                'temp_range_max': 21
            },
        ]
        
        for yeast_data in yeasts:
            yeast_data['description'] = f"Common brewing yeast: {yeast_data['name']}"
            yeast, created = Yeast.objects.get_or_create(
                laboratory=yeast_data['laboratory'],
                strain_number=yeast_data['strain_number'],
                defaults=yeast_data
            )
            if created:
                self.stdout.write(f'Created yeast: {yeast.laboratory} {yeast.strain_number}')