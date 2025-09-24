"""
Simple script to run the media file scanner
This can be run manually or scheduled as a cron job
"""

import os
import sys
import django

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mits_portal.settings')
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    print("🔄 Scanning media directory for manually added files...")
    try:
        call_command('scan_media_files', verbosity=1)
        print("✅ Media scan completed successfully!")
    except Exception as e:
        print(f"❌ Error during media scan: {e}")
        sys.exit(1)
