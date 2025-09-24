"""
Management command to test email functionality
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from storage.email_utils import send_file_shared_email
from storage.models import ShareLink
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Test email functionality for file sharing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test email to',
            default='test@example.com'
        )
        parser.add_argument(
            '--share-id',
            type=int,
            help='ShareLink ID to use for testing (optional)',
        )

    def handle(self, *args, **options):
        test_email = options['email']
        share_id = options.get('share_id')

        self.stdout.write(f"Testing email functionality...")
        self.stdout.write(f"Email backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"SMTP host: {getattr(settings, 'EMAIL_HOST', 'Not configured')}")

        if share_id:
            # Test with existing share link
            try:
                share_link = ShareLink.objects.get(id=share_id)
                self.stdout.write(f"Testing with ShareLink ID: {share_id}")
                
                success = send_file_shared_email(share_link, recipient_email=test_email)
                if success:
                    self.stdout.write(self.style.SUCCESS(f"Email sent successfully to {test_email}"))
                else:
                    self.stdout.write(self.style.ERROR("Failed to send email"))
                    
            except ShareLink.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"ShareLink with ID {share_id} not found"))
        else:
            # Test basic email sending
            try:
                send_mail(
                    subject='MITS Cloud - Email Test',
                    message='This is a test email from MITS Cloud to verify email configuration.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[test_email],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS(f"Test email sent successfully to {test_email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to send test email: {str(e)}"))
                self.stdout.write("Make sure to configure EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in settings.py")

        self.stdout.write("\nTo configure email settings:")
        self.stdout.write("1. Set EMAIL_HOST_USER to your Gmail address")
        self.stdout.write("2. Set EMAIL_HOST_PASSWORD to your Gmail app password")
        self.stdout.write("3. For development, you can use: EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'")
