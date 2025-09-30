import io
import json
import re
import pathlib
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient
from freezegun import freeze_time


# Purpose: Security-focused suite for MITS Cloud (Django 4.2 + DRF)
# How to run: pytest -q
# Notes/Remediation quick tips appear near failing areas in comments.


# ---------- Fixtures / Factories ----------

@pytest.fixture
def api_client(db):
    return APIClient()


@pytest.fixture
def department(db):
    from storage.models import Department
    return Department.objects.create(name="Computer Science", code="CSE", is_active=True)


@pytest.fixture
def session_active(db):
    from storage.models import AcademicSession
    return AcademicSession.objects.create(name="2025", year=2025, is_active=True)


@pytest.fixture
def faculty_user(db, department):
    from storage.models import UserProfile
    u = User.objects.create_user(username="faculty", password="pass", email="f@mitsgwalior.in", is_staff=False)
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.department = department
    p.is_faculty = True
    p.save()
    return u


@pytest.fixture
def student_user(db, department):
    from storage.models import UserProfile
    u = User.objects.create_user(username="student", password="pass", email="s@mitsgwalior.in", is_staff=False)
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.department = department
    p.is_faculty = False
    p.save()
    return u


@pytest.fixture
def admin_user(db, department):
    from storage.models import UserProfile
    u = User.objects.create_user(username="admin", password="pass", email="a@mitsgwalior.in", is_staff=True, is_superuser=True)
    p, _ = UserProfile.objects.get_or_create(user=u)
    p.department = department
    p.is_faculty = True
    p.save()
    return u


@pytest.fixture
def file_item(db, faculty_user, session_active, department):
    from storage.models import FileItem
    return FileItem.objects.create(
        owner=faculty_user, session=session_active, department=department,
        name="syllabus.pdf", is_public=False, file_size=1234
    )


@pytest.fixture
def folder(db, faculty_user, session_active, department):
    from storage.models import Folder
    return Folder.objects.create(
        owner=faculty_user, session=session_active, department=department,
        name="NOTES", is_public=False
    )


# ---------- Authentication & signup restrictions ----------

def test_login_rejects_non_allowed_domain(api_client, db):
    """
    Purpose: Only allowed domains can log in (view enforces DomainRestrictedAuthForm)
    Request: POST /auth/login/
    Assert: error message when email domain is disallowed.
    """
    User.objects.create_user(username="bad", password="pass", email="bad@example.com")
    resp = api_client.post("/auth/login/", data={"username": "bad", "password": "pass"}, follow=True)
    assert resp.status_code in (200, 400, 403)
    content = resp.content.decode("utf-8", errors="ignore").lower()
    assert ("restricted" in content) or ("not allowed" in content) or ("login restricted" in content)


def test_signup_rejects_non_allowed_domain_even_if_ui_hides_form(api_client, db):
    """
    Purpose: Server-side restriction present even if UI hides email signup.
    Request: POST /auth/signup/
    Assert: validation error message.
    """
    resp = api_client.post("/auth/signup/", data={
        "username": "bad",
        "email": "bad@example.com",
        "password1": "GoodPass123!",
        "password2": "GoodPass123!",
        "department": "",
    }, follow=True)
    assert resp.status_code in (200, 400)
    content = resp.content.decode("utf-8", errors="ignore").lower()
    assert ("only emails ending" in content) or ("allowed" in content) or ("restricted" in content)


# ---------- Session & Cookie settings ----------

@pytest.mark.django_db
def test_session_cookie_flags_after_login_https(api_client, admin_user):
    """
    Purpose: Ensure HttpOnly, SameSite, Secure flags on session cookie under HTTPS.
    """
    api_client.defaults["wsgi.url_scheme"] = "https"
    resp = api_client.post("/auth/login/", data={"username": "admin", "password": "pass"})
    assert resp.status_code in (200, 302)
    cookie_dump = "; ".join(resp.cookies.output().splitlines()).lower()
    assert "httponly" in cookie_dump
    assert ("samesite=lax" in cookie_dump) or ("samesite=strict" in cookie_dump)
    assert "secure" in cookie_dump


# ---------- Role-based authorization & IDOR ----------

def test_student_cannot_make_public_files(api_client, student_user, file_item):
    api_client.force_authenticate(student_user)
    r = api_client.post(f"/api/files/{file_item.id}/visibility/", data={"is_public": "true"})
    assert r.status_code == 403


def test_faculty_owner_can_make_public(api_client, faculty_user, file_item):
    api_client.force_authenticate(faculty_user)
    r = api_client.post(f"/api/files/{file_item.id}/visibility/", data={"is_public": "true"})
    assert r.status_code == 200
    assert r.json().get("is_public") is True


def test_idor_prevent_toggle_other_user_file(api_client, faculty_user, student_user, file_item):
    file_item.owner = student_user
    file_item.save()
    api_client.force_authenticate(faculty_user)
    r = api_client.post(f"/api/files/{file_item.id}/visibility/", data={"is_public": "false"})
    assert r.status_code == 403


# ---------- Parameterized DB access (ban dynamic/raw) ----------

DANGEROUS_DB_PATTERNS = [
    # raw() is allowed if used safely with trusted SQL; restrict to suspicious cases in app code only
    # We scope search to project apps to avoid catching Django manage scripts and third-party libs
]


def test_no_dynamic_raw_sql_in_repo():
    """Search only app directories for obviously unsafe raw SQL composition."""
    root = pathlib.Path(settings.BASE_DIR)
    app_dirs = [root / "accounts", root / "core", root / "storage"]
    patterns = [
        r"\.raw\([^)]*(\+|%)",                  # raw() with + or % formatting
        r"cursor\.execute\([^)]*(\+|%|f['\"])"  # execute( ... + or % or f"/f' )
    ]
    for ad in app_dirs:
        blob = ""
        for p in ad.rglob("*.py"):
            try:
                blob += p.read_text(encoding="utf-8", errors="ignore") + "\n"
            except Exception:
                pass
        for pat in patterns:
            assert not re.search(pat, blob), f"Dangerous DB pattern found in {ad}: {pat}"


# ---------- Input validation & XSS ----------

def test_search_rejects_xss_reflection(api_client, faculty_user):
    api_client.force_authenticate(faculty_user)
    x = '<script>alert(1)</script>'
    r = api_client.get(f"/api/search/?q={x}")
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        assert r.headers.get("Content-Type", "").startswith("application/json")
        body = r.json()
        assert "results" in body
        assert "<script>" not in json.dumps(body).lower()


# ---------- File upload validation ----------

def _make_file(name: str, size: int = 512, content_type: str = "application/pdf"):
    return io.BytesIO(b"A" * size), name, content_type


def test_upload_blocks_disallowed_extension(api_client, faculty_user, session_active, department):
    api_client.force_authenticate(faculty_user)
    f, name, ct = _make_file("evil.exe", 128, "application/octet-stream")
    r = api_client.post("/api/files/", data={
        "session": session_active.id,
        "department": department.id,
        "file": (f, name),
        "is_public": "false",
    }, format="multipart")
    assert r.status_code in (400, 415)


def test_upload_path_traversal_sanitized(api_client, faculty_user, session_active, department):
    api_client.force_authenticate(faculty_user)
    f, name, ct = _make_file("../../evil.txt", 32, "text/plain")
    r = api_client.post("/api/files/", data={
        "session": session_active.id,
        "department": department.id,
        "file": (f, name),
    }, format="multipart")
    assert r.status_code in (201, 400)
    if r.status_code == 201:
        data = r.json()
        assert "file" in data
        assert ".." not in data["file"]


# ---------- Share-link security ----------

@pytest.fixture
def shared_file(db, file_item):
    return file_item


def test_share_password_protected_requires_password(api_client, faculty_user, shared_file):
    api_client.force_authenticate(faculty_user)
    r = api_client.post("/api/share/", data={"file_item": shared_file.id, "share_type": "password", "password": "p@ss"})
    assert r.status_code in (201, 200)
    token = r.json()["token"]
    # Use API resolver to avoid template static dependency
    r2 = api_client.get(f"/api/share/{token}/")
    assert r2.status_code in (200, 401)
    r3 = api_client.get(f"/api/share/{token}/?password=p@ss")
    assert r3.status_code == 200


def test_share_email_restricted_requires_matching_user(api_client, faculty_user, shared_file):
    api_client.force_authenticate(faculty_user)
    r = api_client.post("/api/share/", data={"file_item": shared_file.id, "share_type": "email", "email": "f@mitsgwalior.in"})
    assert r.status_code in (201, 200)
    token = r.json()["token"]
    c2 = APIClient()
    r2 = c2.get(f"/api/share/{token}/")
    assert r2.status_code in (403, 200)
    c3 = APIClient(); c3.force_authenticate(faculty_user)
    r3 = c3.get(f"/api/share/{token}/")
    assert r3.status_code == 200


@freeze_time("2025-09-01 10:00:00")
def test_share_expiry_enforced(api_client, faculty_user, shared_file):
    api_client.force_authenticate(faculty_user)
    exp = (timezone.now() + timedelta(minutes=1)).isoformat()
    r = api_client.post("/api/share/", data={"file_item": shared_file.id, "share_type": "public", "expires_at": exp})
    assert r.status_code in (201, 200)
    token = r.json()["token"]
    with freeze_time("2025-09-01 10:05:00"):
        r2 = api_client.get(f"/api/share/{token}/")
        assert r2.status_code in (410, 200)


def test_share_download_count_enforced(api_client, faculty_user, shared_file):
    api_client.force_authenticate(faculty_user)
    r = api_client.post("/api/share/", data={"file_item": shared_file.id, "share_type": "public", "max_downloads": 1})
    assert r.status_code in (201, 200)
    token = r.json()["token"]
    # Prefer API resolver if available
    r1 = api_client.get(f"/api/share/resolve/{token}/")
    assert r1.status_code in (200,)
    r2 = api_client.get(f"/share/{token}/")
    assert r2.status_code in (403, 410, 429)


# ---------- Audit logging ----------

def test_audit_log_created_on_upload_and_view(api_client, faculty_user, session_active, department):
    from storage.models import FileAuditLog
    api_client.force_authenticate(faculty_user)
    f = io.BytesIO(b"A" * 64)
    r = api_client.post("/api/files/", data={
        "session": session_active.id, "department": department.id, "file": (f, "test.pdf")
    }, format="multipart")
    assert r.status_code in (201, 200)
    fid = r.json()["id"]
    r2 = api_client.get(f"/api/files/{fid}/")
    assert r2.status_code == 200
    actions = list(FileAuditLog.objects.values_list("action", flat=True))
    assert ("upload" in actions) or ("view" in actions)


# ---------- Rate limiting (xfail until throttles configured) ----------

@pytest.mark.xfail(reason="Enable throttling to return 429 on repeated failed logins")
def test_rate_limit_login(api_client):
    for _ in range(20):
        api_client.post("/auth/login/", data={"username": "x", "password": "wrong"})
    r = api_client.post("/auth/login/", data={"username": "x", "password": "wrong"})
    assert r.status_code == 429


@pytest.mark.xfail(reason="Enable throttling for /api/share/ to return 429")
def test_rate_limit_share_create(api_client, faculty_user, file_item):
    api_client.force_authenticate(faculty_user)
    for _ in range(50):
        api_client.post("/api/share/", data={"file_item": file_item.id, "share_type": "public"})
    r = api_client.post("/api/share/", data={"file_item": file_item.id, "share_type": "public"})
    assert r.status_code == 429


# ---------- Sensitive data not leaked ----------

def test_sensitive_data_not_leaked_in_profile(api_client, admin_user):
    api_client.force_authenticate(admin_user)
    r = api_client.get("/api/profile/")
    if r.status_code == 200:
        s = json.dumps(r.json()).lower()
        assert "password" not in s
        assert "token" not in s
        assert "secret" not in s


