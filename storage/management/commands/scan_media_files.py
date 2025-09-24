"""
Management command to scan media directory and create database entries
for manually added files and folders that follow the MITS Cloud structure.
"""

import os
import mimetypes
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from storage.models import (
    AcademicSession, Department, Folder, FileItem, 
    FileCategory, UserProfile
)


class Command(BaseCommand):
    help = 'Scan media directory and create database entries for manually added files/folders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating database entries',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if files already exist in database',
        )
        parser.add_argument(
            '--session-year',
            type=int,
            help='Only process files for a specific session year',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force = options['force']
        self.session_year = options['session_year']
        
        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f'Media directory does not exist: {media_root}')

        self.stdout.write(f'Scanning media directory: {media_root}')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get or create a default user for manual files
        self.default_user = self.get_default_user()
        
        # Process all session directories
        self.process_media_directory(media_root)
        
        self.stdout.write(self.style.SUCCESS('Scan completed successfully!'))

    def get_default_user(self):
        """Get or create a default user for manually added files"""
        try:
            # Try to get the first superuser
            user = User.objects.filter(is_superuser=True).first()
            if user:
                return user
        except Exception:
            pass
        
        try:
            # Try to get the first staff user
            user = User.objects.filter(is_staff=True).first()
            if user:
                return user
        except Exception:
            pass
        
        # Create a default system user if none exists
        user, created = User.objects.get_or_create(
            username='system_admin',
            defaults={
                'email': 'admin@mitsgwalior.in',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        if created:
            self.stdout.write(f'Created default system user: {user.username}')
        
        return user

    def process_media_directory(self, media_root):
        """Process the media directory structure"""
        total_files = 0
        total_folders = 0
        
        for item in media_root.iterdir():
            if item.is_dir() and self.is_session_directory(item.name):
                session_name = item.name
                session_year = self.extract_year_from_session(session_name)
                
                # Skip if specific year filter is set
                if self.session_year and session_year != self.session_year:
                    continue
                
                self.stdout.write(f'\nProcessing session: {session_name}')
                
                # Get or create academic session
                session = self.get_or_create_session(session_name, session_year)
                
                # Process department directories
                for dept_item in item.iterdir():
                    if dept_item.is_dir():
                        dept_code = dept_item.name
                        department = self.get_or_create_department(dept_code)
                        
                        self.stdout.write(f'  Processing department: {dept_code}')
                        
                        # Process files and folders in department
                        files_created, folders_created = self.process_department_directory(
                            dept_item, session, department
                        )
                        
                        total_files += files_created
                        total_folders += folders_created
        
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  Files processed: {total_files}')
        self.stdout.write(f'  Folders processed: {total_folders}')

    def is_session_directory(self, dirname):
        """Check if directory name follows session pattern"""
        # Pattern: YYYY_SESSION_NAME or YYYY_SESSION_NAME (YEAR)
        return '_' in dirname and any(char.isdigit() for char in dirname)

    def extract_year_from_session(self, session_name):
        """Extract year from session directory name"""
        try:
            # Extract year from patterns like "2024_2024-25" or "2023_2023-24 (2023)"
            year_part = session_name.split('_')[0]
            return int(year_part)
        except (ValueError, IndexError):
            return None

    def get_or_create_session(self, session_name, year):
        """Get or create academic session"""
        if not year:
            self.stdout.write(f'    Warning: Could not extract year from {session_name}')
            return None
        
        session, created = AcademicSession.objects.get_or_create(
            year=year,
            defaults={
                'name': session_name,
                'is_active': False,  # Manual sessions are inactive by default
                'description': f'Auto-created from media directory: {session_name}',
                'created_by': self.default_user,
            }
        )
        
        if created:
            self.stdout.write(f'    Created session: {session_name} ({year})')
        else:
            self.stdout.write(f'    Found existing session: {session_name} ({year})')
        
        return session

    def get_or_create_department(self, dept_code):
        """Get or create department"""
        dept_name_map = {
            'CSE': 'Computer Science Engineering',
            'IT': 'Information Technology',
            'ECE': 'Electronics and Communication Engineering',
            'ME': 'Mechanical Engineering',
            'CE': 'Civil Engineering',
            'IO': 'Industrial Engineering',
            'ADMIN': 'Administration',
        }
        
        dept_name = dept_name_map.get(dept_code, dept_code)
        
        department, created = Department.objects.get_or_create(
            code=dept_code,
            defaults={
                'name': dept_name,
                'description': f'Auto-created department: {dept_name}',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(f'    Created department: {dept_name} ({dept_code})')
        
        return department

    def process_department_directory(self, dept_dir, session, department):
        """Process files and folders in department directory"""
        files_created = 0
        folders_created = 0
        
        # Process root level files first
        for item in dept_dir.iterdir():
            if item.is_file():
                if self.create_file_entry(item, session, department, None):
                    files_created += 1
        
        # Process folders recursively
        for item in dept_dir.iterdir():
            if item.is_dir():
                folder_created = self.process_folder_recursive(
                    item, session, department, None
                )
                if folder_created:
                    folders_created += 1
        
        return files_created, folders_created

    def process_folder_recursive(self, folder_path, session, department, parent_folder):
        """Process folder and its contents recursively"""
        folder_name = folder_path.name
        
        # Create folder entry
        folder = self.create_folder_entry(folder_path, session, department, parent_folder)
        if not folder:
            return False
        
        # Process files in this folder
        for item in folder_path.iterdir():
            if item.is_file():
                self.create_file_entry(item, session, department, folder)
        
        # Process subfolders
        for item in folder_path.iterdir():
            if item.is_dir():
                self.process_folder_recursive(item, session, department, folder)
        
        return True

    def create_folder_entry(self, folder_path, session, department, parent_folder):
        """Create database entry for folder"""
        folder_name = folder_path.name
        
        # Check if folder already exists
        existing_folder = Folder.objects.filter(
            session=session,
            department=department,
            name=folder_name,
            parent=parent_folder
        ).first()
        
        if existing_folder and not self.force:
            self.stdout.write(f'    Folder already exists: {folder_name}')
            return existing_folder
        
        if self.dry_run:
            self.stdout.write(f'    [DRY RUN] Would create folder: {folder_name}')
            return None
        
        try:
            folder = Folder.objects.create(
                session=session,
                department=department,
                name=folder_name,
                parent=parent_folder,
                owner=self.default_user,
                is_public=False,  # Manual folders are private by default
                is_manual=True,   # Mark as manually added folder
                description=f'Auto-created from media directory: {folder_path}',
            )
            
            self.stdout.write(f'    Created folder: {folder_name}')
            return folder
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    Error creating folder {folder_name}: {e}')
            )
            return None

    def create_file_entry(self, file_path, session, department, folder):
        """Create database entry for file"""
        file_name = file_path.name
        
        # Check if file already exists
        existing_file = FileItem.objects.filter(
            session=session,
            department=department,
            folder=folder,
            name=file_name
        ).first()
        
        if existing_file and not self.force:
            self.stdout.write(f'    File already exists: {file_name}')
            return False
        
        if self.dry_run:
            self.stdout.write(f'    [DRY RUN] Would create file: {file_name}')
            return True
        
        try:
            # Get file size
            file_size = file_path.stat().st_size
            
            # Determine file category based on extension
            category = self.get_file_category(file_path)
            
            file_item = FileItem.objects.create(
                session=session,
                department=department,
                folder=folder,
                name=file_name,
                original_filename=file_name,
                owner=self.default_user,
                is_public=False,  # Manual files are private by default
                is_manual=True,   # Mark as manually added file
                category=category,
                description=f'Auto-created from media directory: {file_path}',
                file_size=file_size,
                download_count=0,
            )
            
            # Update the file field to point to the actual file
            file_item.file.name = str(file_path.relative_to(settings.MEDIA_ROOT))
            file_item.save()
            
            self.stdout.write(f'    Created file: {file_name}')
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'    Error creating file {file_name}: {e}')
            )
            return False

    def get_file_category(self, file_path):
        """Get appropriate file category based on file extension"""
        extension = file_path.suffix.lower()
        
        category_map = {
            '.pdf': 'Documents',
            '.doc': 'Documents',
            '.docx': 'Documents',
            '.ppt': 'Presentations',
            '.pptx': 'Presentations',
            '.xls': 'Spreadsheets',
            '.xlsx': 'Spreadsheets',
            '.txt': 'Text Files',
            '.jpg': 'Images',
            '.jpeg': 'Images',
            '.png': 'Images',
            '.gif': 'Images',
            '.zip': 'Archives',
            '.rar': 'Archives',
        }
        
        category_name = category_map.get(extension, 'Other')
        
        # Get or create category
        category, created = FileCategory.objects.get_or_create(
            name=category_name,
            defaults={
                'description': f'Auto-created category for {extension} files',
                'color': '#3B82F6',
            }
        )
        
        return category
