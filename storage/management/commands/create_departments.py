from django.core.management.base import BaseCommand
from storage.models import Department

class Command(BaseCommand):
    help = 'Create sample departments for MITS'

    def handle(self, *args, **options):
        departments = [
            {'name': 'Computer Science and Engineering', 'code': 'CSE'},
            {'name': 'Information Technology', 'code': 'IT'},
            {'name': 'Electronics and Communication Engineering', 'code': 'ECE'},
            {'name': 'Mechanical Engineering', 'code': 'ME'},
            {'name': 'Civil Engineering', 'code': 'CE'},
            {'name': 'Electrical Engineering', 'code': 'EE'},
            {'name': 'Management Studies', 'code': 'MS'},
            {'name': 'Applied Sciences', 'code': 'AS'},
            {'name': 'Administration', 'code': 'ADMIN'},
        ]
        
        created_count = 0
        for dept_data in departments:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults={'name': dept_data['name']}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created department: {dept.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Department already exists: {dept.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new departments')
        )
