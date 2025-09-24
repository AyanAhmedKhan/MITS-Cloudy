"""
Email utilities for MITS Cloud file sharing notifications
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_file_shared_email(share_link, recipient_email=None, recipient_name=None):
    """
    Send email notification when a file is shared
    
    Args:
        share_link: ShareLink instance
        recipient_email: Email address to send to (if None, uses share_link.email)
        recipient_name: Name of recipient (optional)
    """
    try:
        # Get the shared item (file or folder)
        if share_link.file_item:
            item = share_link.file_item
            item_type = "File"
        elif share_link.folder:
            item = share_link.folder
            item_type = "Folder"
        else:
            logger.error(f"No file or folder found for share link {share_link.id}")
            return False

        # Prepare email data
        recipient_email = recipient_email or share_link.email
        if not recipient_email:
            logger.warning(f"No recipient email for share link {share_link.id}")
            return False

        # Build share URL
        share_url = f"{settings.BASE_URL or 'http://127.0.0.1:8000'}{reverse('share-view', args=[share_link.token])}"
        
        # Prepare context for email template
        context = {
            'recipient_name': recipient_name,
            'shared_by': share_link.created_by.get_full_name() or share_link.created_by.username,
            'file_name': item.name,
            'file_extension': getattr(item, 'file_extension', '') if hasattr(item, 'file_extension') else '',
            'file_size': getattr(item, 'file_size_display', '') if hasattr(item, 'file_size_display') else '',
            'department_name': item.department.name,
            'session_name': item.session.name,
            'shared_date': share_link.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'share_type': share_link.get_share_type_display(),
            'password': share_link.password if share_link.share_type == 'password' else None,
            'max_downloads': share_link.max_downloads,
            'expires_at': share_link.expires_at.strftime('%B %d, %Y at %I:%M %p') if share_link.expires_at else None,
            'share_url': share_url,
            'base_url': settings.BASE_URL or 'http://127.0.0.1:8000',
        }

        # Render email templates
        html_content = render_to_string('emails/file_shared.html', context)
        text_content = render_to_string('emails/file_shared.txt', context)

        # Create email subject
        subject = f"MITS Cloud: {item_type} Shared - {item.name}"

        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send()
        
        logger.info(f"File sharing email sent successfully to {recipient_email} for share link {share_link.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send file sharing email: {str(e)}")
        return False

def send_bulk_file_shared_emails(share_link, email_list):
    """
    Send email notifications to multiple recipients
    
    Args:
        share_link: ShareLink instance
        email_list: List of email addresses
    """
    success_count = 0
    for email in email_list:
        if send_file_shared_email(share_link, recipient_email=email):
            success_count += 1
    
    logger.info(f"Sent {success_count}/{len(email_list)} file sharing emails for share link {share_link.id}")
    return success_count

def send_public_file_notification(share_link, notification_emails=None):
    """
    Send notification when a file is made public
    
    Args:
        share_link: ShareLink instance
        notification_emails: List of emails to notify (optional)
    """
    if not notification_emails:
        # Get admin emails or other relevant emails
        from django.contrib.auth.models import User
        admin_emails = list(User.objects.filter(is_staff=True).values_list('email', flat=True))
        notification_emails = [email for email in admin_emails if email]
    
    if not notification_emails:
        return False
    
    try:
        # Get the shared item
        if share_link.file_item:
            item = share_link.file_item
        elif share_link.folder:
            item = share_link.folder
        else:
            return False

        # Build share URL
        share_url = f"{settings.BASE_URL or 'http://127.0.0.1:8000'}{reverse('share-view', args=[share_link.token])}"
        
        # Create notification email
        subject = f"MITS Cloud: New Public {item.__class__.__name__} - {item.name}"
        
        message = f"""
A new public {item.__class__.__name__.lower()} has been shared on MITS Cloud:

{item.__class__.__name__}: {item.name}
Department: {item.department.name}
Session: {item.session.name}
Shared by: {share_link.created_by.get_full_name() or share_link.created_by.username}
Shared on: {share_link.created_at.strftime('%B %d, %Y at %I:%M %p')}

Access URL: {share_url}

This is an automated notification from MITS Cloud.
        """.strip()

        # Send to all notification emails
        from django.core.mail import send_mail
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=notification_emails,
            fail_silently=False,
        )
        
        logger.info(f"Public file notification sent to {len(notification_emails)} recipients for share link {share_link.id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send public file notification: {str(e)}")
        return False
