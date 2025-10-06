from django.core.management.base import BaseCommand

from core.utils import is_database_connected


class Command(BaseCommand):
    help = "Check database connectivity by performing a lightweight query. Returns non-zero exit on failure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--alias",
            default="default",
            help="Database alias to check (default: default)",
        )

    def handle(self, *args, **options):
        alias = options["alias"]
        if is_database_connected(alias=alias):
            self.stdout.write(self.style.SUCCESS(f"Database '{alias}' is reachable."))
            return
        self.stderr.write(self.style.ERROR(f"Database '{alias}' is NOT reachable."))
        raise SystemExit(1)


