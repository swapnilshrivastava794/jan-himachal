from django.core.management.base import BaseCommand
from nanhe_patrakar.models import Program


class Command(BaseCommand):
    help = 'Create default Nanhe Patrakar program'

    def handle(self, *args, **options):
        program, created = Program.objects.get_or_create(
            slug='nanhe-patrakar',
            defaults={
                'name': 'Nanhe Patrakar',
                'name_hindi': 'नन्हे पत्रकार',
                'description': 'A Golden Opportunity for Children of Himachal Pradesh to Learn Journalism',
                'description_hindi': 'हिमाचल प्रदेश के बच्चों के लिए पत्रकारिता का सुनहरा अवसर',
                'price': 599.00,
                'min_age': 8,
                'max_age': 16,
                'age_group_a_min': 8,
                'age_group_a_max': 10,
                'age_group_b_min': 11,
                'age_group_b_max': 13,
                'age_group_c_min': 14,
                'age_group_c_max': 16,
                'is_active': True,
                'registration_open': True,
                'display_order': 1,
                'terms_and_conditions': '''
1. Child must be between 8-16 years old
2. Must be a resident of Himachal Pradesh
3. Parent/Guardian consent is mandatory
4. One-time participation fee is non-refundable
5. Content submitted will be reviewed by editors
6. Published content remains property of Jan Himachal
                ''',
                'privacy_policy': '''
We respect your privacy and are committed to protecting your personal information.
All data collected will be used only for program purposes and will not be shared with third parties.
                '''
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created default program: {program.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'○ Program already exists: {program.name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ Default program setup complete!')
        )