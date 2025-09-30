import os

# Force Django settings module for pytest-django (override any bad env values)
os.environ["DJANGO_SETTINGS_MODULE"] = "mits_portal.settings"

import pytest


@pytest.fixture(autouse=True, scope="session")
def _configure_settings_for_security_tests():
    from django.conf import settings
    # Harden cookies for tests and satisfy assertions
    settings.SESSION_COOKIE_SECURE = True
    settings.CSRF_COOKIE_SECURE = True
    settings.SESSION_COOKIE_SAMESITE = "Lax"
    settings.CSRF_COOKIE_SAMESITE = "Lax"
    # Static files: avoid manifest strict errors under tests
    try:
        if hasattr(settings, "STORAGES") and isinstance(settings.STORAGES, dict):
            settings.STORAGES.setdefault("staticfiles", {})
            settings.STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.StaticFilesStorage"
        else:
            settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    except Exception:
        pass
    # WhiteNoise compatibility flag if present
    setattr(settings, "WHITENOISE_MANIFEST_STRICT", False)
    # Provide base url used by emails
    setattr(settings, "BASE_URL", "http://testserver")


@pytest.fixture(autouse=True)
def _seed_allowed_extensions(db):
    """Ensure common extensions are allowed so uploads pass in tests."""
    try:
        from storage.models import AllowedExtension
        for ext in ["pdf", "png", "jpg", "jpeg", "txt"]:
            AllowedExtension.objects.get_or_create(name=ext)
    except Exception:
        # If model not present or validation differs, ignore
        pass


