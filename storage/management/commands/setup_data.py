from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from storage.models import Department, FileCategory, AcademicSession, UserProfile


class Command(BaseCommand):
    help = 'Set up initial data for MITS Cloud'

    def handle(self, *args, **options):
        self.stdout.write('Setting up initial data...')
        
        # Create departments
        departments = [
            {'name': 'Computer Science Engineering', 'code': 'CSE'},
            {'name': 'Electronics & Communication', 'code': 'ECE'},
            {'name': 'Mechanical Engineering', 'code': 'ME'},
            {'name': 'Civil Engineering', 'code': 'CE'},
            {'name': 'Information Technology', 'code': 'IT'},
        ]
        
        for dept_data in departments:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            if created:
                self.stdout.write(f'Created department: {dept.name}')
            else:
                self.stdout.write(f'Department already exists: {dept.name}')
        
        # Create file categories
        categories = [
            {'name': 'Syllabus', 'description': 'Course syllabus and curriculum', 'color': '#3B82F6'},
            {'name': 'Notes', 'description': 'Lecture notes and study materials', 'color': '#10B981'},
            {'name': 'Assignments', 'description': 'Student assignments and projects', 'color': '#F59E0B'},
            {'name': 'Question Papers', 'description': 'Previous year question papers', 'color': '#EF4444'},
            {'name': 'Lab Manuals', 'description': 'Laboratory manuals and guides', 'color': '#8B5CF6'},
            {'name': 'Research Papers', 'description': 'Research publications and papers', 'color': '#06B6D4'},
        ]
        
        for cat_data in categories:
            cat, created = FileCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {cat.name}')
            else:
                self.stdout.write(f'Category already exists: {cat.name}')
        
        # Create academic sessions
        sessions = [
            {'name': '2024-25', 'year': 2024, 'is_active': True},
            {'name': '2023-24', 'year': 2023, 'is_active': False},
            {'name': '2022-23', 'year': 2022, 'is_active': False},
        ]
        
        for session_data in sessions:
            session, created = AcademicSession.objects.get_or_create(
                name=session_data['name'],
                defaults=session_data
            )
            if created:
                self.stdout.write(f'Created session: {session.name}')
            else:
                self.stdout.write(f'Session already exists: {session.name}')
        
        # Create user profile for admin if it doesn't exist
        try:
            admin_user = User.objects.get(username='admin')
            profile, created = UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={'is_faculty': True}
            )
            if created:
                self.stdout.write('Created admin user profile')
            else:
                self.stdout.write('Admin user profile already exists')
        except User.DoesNotExist:
            self.stdout.write('Admin user not found, skipping profile creation')
        
        self.stdout.write(self.style.SUCCESS('Initial data setup completed successfully!'))
        self.stdout.write('\nYou can now:')
        self.stdout.write('1. Visit /admin/ to manage the system')
        self.stdout.write('2. Create more departments, categories, and sessions')
        self.stdout.write('3. Upload files and organize them')
        self.stdout.write('4. Test the search and sharing functionality')
