#!/usr/bin/env python
"""
Standalone tenant bootstrapper.

Usage examples:
  python tools/create_sample_org.py --name "NeuroMed Aira (Demo)" --slug neuromed --domain neuromed.neuromedai.org --owner-email founder@neuromedai.org --owner-staff --seed-demo --send-email
  python tools/create_sample_org.py --name "Neuromed Local" --slug neurolocal --domain http://neurolocal.localtest.me:8000 --owner-email you@example.com --seed-demo --http
"""

import os
import sys
import argparse
import secrets
import string
from contextlib import suppress
from urllib.parse import urlparse

# ---------------- Django bootstrap ----------------
# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myProject.settings")

import django  # noqa: E402
django.setup()  # noqa: E402

from django.conf import settings  # noqa: E402
from django.core.mail import send_mail  # noqa: E402
from django.core.management.base import CommandError  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.db import transaction  # noqa: E402

from myApp.models import Org, OrgDomain, OrgMembership, Patient, Encounter  # noqa: E402

User = get_user_model()

# ---------------- Helpers ----------------

def gen_password(length=14) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def sanitize_domain(value: str) -> str:
    """
    Accepts:
      - neuromed.neuromedai.org
      - https://neuromed.neuromedai.org/
      - http://localhost:8000
    Returns just the host (no scheme/port/path), lowercased.
    """
    v = (value or "").strip()
    if "://" in v:
        p = urlparse(v)
        host = (p.netloc or "").split("@")[-1]  # strip potential creds
    else:
        host = v
    host = host.strip().lower()
    host = host.split("/")[0].split(":")[0]  # strip path/port
    if not host:
        raise CommandError("Domain/host cannot be empty.")
    return host

def choose_scheme(host: str, force_http: bool = False) -> str:
    if force_http:
        return "http"
    # local/dev hosts default to http
    if host in {"localhost", "127.0.0.1"} or host.endswith(".localtest.me"):
        return "http"
    return "https"

def portal_login_url(host: str, force_http: bool = False) -> str:
    return f"{choose_scheme(host, force_http=force_http)}://{host}/portal/login/"

def email_credentials(to_email: str, org: Org, login_url: str, password: str | None):
    """Safe best-effort: never crash provisioning over email issues."""
    try:
        subject = f"Your NeuroMed Aira Portal Access – {org.name}"
        if password:
            body = (
                f"Welcome to {org.name} on NeuroMed Aira.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n"
                f"Temporary Password: {password}\n\n"
                "For security, please sign in and change your password."
            )
        else:
            body = (
                f"Your NeuroMed Aira portal is ready for {org.name}.\n\n"
                f"Portal: {login_url}\n"
                f"Email: {to_email}\n\n"
                "If you need a password reset, reply to this email."
            )
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception:
        pass

# ---------------- Core op ----------------

@transaction.atomic
def create_org_and_owner(
    name: str,
    slug: str,
    raw_domain: str,
    owner_email: str,
    owner_staff: bool = False,
    send_email_flag: bool = False,
    seed_demo: bool = False,
    force_http: bool = False,
    explicit_password: str | None = None,
):
    if not name or not slug or not owner_email:
        raise CommandError("Please provide --name, --slug and --owner-email.")

    host = sanitize_domain(raw_domain)
    temp_pw = explicit_password or gen_password()

    # Org
    org, created_org = Org.objects.get_or_create(slug=slug, defaults={"name": name})
    if not created_org:
        org.name = name
        org.is_active = True
        org.save()

    # Domain (ensure unique binding)
    existing = OrgDomain.objects.filter(domain=host).first()
    if existing and existing.org_id != org.id:
        raise CommandError(f"Domain '{host}' already belongs to another org: {existing.org.name}")

    OrgDomain.objects.update_or_create(org=org, domain=host, defaults={"is_primary": True})

    # Owner user
    user, user_created = User.objects.get_or_create(
        email=owner_email,
        defaults={"username": owner_email}
    )
    # Only set password if newly created or explicit override requested
    if user_created or explicit_password:
        user.set_password(temp_pw)
    if owner_staff:
        user.is_staff = True
    with suppress(AttributeError):
        user.is_active = True
    user.save()

    # Membership
    OrgMembership.objects.get_or_create(
        org=org, user=user, defaults={"role": "OWNER", "is_active": True}
    )

    # Seed demo data (bypass thread-local manager with all_objects)
    if seed_demo:
        p1 = Patient.all_objects.create(org=org, first_name="Maria",  last_name="Reyes",  mrn="MRN1001")
        p2 = Patient.all_objects.create(org=org, first_name="Jared",  last_name="Cruz",   mrn="MRN1002")
        p3 = Patient.all_objects.create(org=org, first_name="Elaine", last_name="Santos", mrn="MRN1003")

        Encounter.all_objects.create(org=org, user=user, patient=p1, reason="Knee pain",          status="new",       priority="medium")
        Encounter.all_objects.create(org=org, user=user, patient=p2, reason="Diabetes follow-up", status="screening", priority="low")
        Encounter.all_objects.create(org=org, user=user, patient=p3, reason="MRI review",         status="ready",     priority="high")

    login_url = portal_login_url(host, force_http=force_http)

    if send_email_flag:
        email_credentials(owner_email, org, login_url, temp_pw if (user_created or explicit_password) else None)

    # Console summary
    print("")
    print("✅ Tenant ready!")
    print(f"  Org:        {org.name} (slug: {org.slug})")
    print(f"  Domain:     {host}")
    print(f"  Portal:     {login_url}")
    print(f"  Owner:      {owner_email}")
    if user_created or explicit_password:
        print(f"  Temp Pass:  {temp_pw}  (change on first login)")
    else:
        print("  Password:   (unchanged; user already existed)")
    if seed_demo:
        print("  Demo Data:  Seeded 3 patients + 3 encounters")
    print("")

# ---------------- CLI ----------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Create an Org + primary domain + owner user (optional demo data).")
    p.add_argument("--name", default="NeuroMed Aira (Demo)", help="Org display name (e.g., 'Green Valley Clinic').")
    p.add_argument("--slug", default="neuromed", help="Unique slug (e.g., 'greenvalley').")
    p.add_argument("--domain", default="neuromed.neuromedai.org", help="Primary host or URL (e.g., 'greenvalley.neuromedai.org' or 'http://neurolocal.localtest.me:8000').")
    p.add_argument("--owner-email", default="founder@neuromedai.org", help="Email for the owner account.")
    p.add_argument("--owner-staff", action="store_true", help="Mark owner as is_staff (useful for internal testing).")
    p.add_argument("--send-email", action="store_true", help="Email credentials to the owner (requires SMTP).")
    p.add_argument("--seed-demo", action="store_true", help="Seed a few demo patients and encounters.")
    p.add_argument("--password", default=None, help="Set a specific temp password. If omitted and user exists, password is unchanged.")
    p.add_argument("--http", action="store_true", help="Force http scheme in the printed login URL (useful for local dev).")
    return p.parse_args(argv)

def main():
    args = parse_args()
    try:
        create_org_and_owner(
            name=(args.name or "").strip(),
            slug=(args.slug or "").strip(),
            raw_domain=(args.domain or "").strip(),
            owner_email=(args.owner_email or "").strip().lower(),
            owner_staff=bool(args.owner_staff),
            send_email_flag=bool(args.send_email),
            seed_demo=bool(args.seed_demo),
            force_http=bool(args.http),
            explicit_password=args.password,
        )
    except CommandError as e:
        print(f"❌ Error: {e}")
        sys.exit(2)
    except Exception as e:
        # Unexpected error: show message and non-zero exit
        print(f"❌ Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()
