from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from myApp.emailer import send_via_resend

class Command(BaseCommand):
    help = "Send a test email via Resend to verify configuration"

    def add_arguments(self, parser):
        parser.add_argument("--to", required=False, help="Recipient email address")
        parser.add_argument("--subject", default="[NeuroMed] Resend test OK")
        parser.add_argument("--text", default="This is a Resend test email from Django.")
        parser.add_argument("--html", default="<p>This is a <b>Resend</b> test email from Django.</p>")

    def handle(self, *args, **opts):
        to = opts["to"] or settings.DEFAULT_FROM_EMAIL
        ok = send_via_resend(
            to=[to],
            subject=opts["subject"],
            text=opts["text"],
            html=opts["html"],
            fail_silently=True,
        )
        if ok:
            self.stdout.write(self.style.SUCCESS(f"Sent Resend test to {to}"))
        else:
            raise CommandError("Failed to send via Resend. Check logs and RESEND_ env vars.")
