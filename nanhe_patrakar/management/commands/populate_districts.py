from django.core.management.base import BaseCommand
from nanhe_patrakar.models import District


class Command(BaseCommand):
    help = 'Populate Himachal Pradesh districts'

    def handle(self, *args, **options):
        districts = [
            'Bilaspur',
            'Chamba',
            'Hamirpur',
            'Kangra',
            'Kinnaur',
            'Kullu',
            'Lahaul and Spiti',
            'Mandi',
            'Shimla',
            'Sirmaur',
            'Solan',
            'Una',
        ]
        
        created_count = 0
        
        for district_name in districts:
            district, created = District.objects.get_or_create(
                name=district_name,
                defaults={'is_active': True}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created district: {district_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'○ District already exists: {district_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully processed {len(districts)} districts')
        )
        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {created_count} new districts')
        )