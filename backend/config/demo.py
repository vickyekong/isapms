import fcntl
import io

from django.conf import settings
from django.core.management import call_command


def prepare_demo_database():
    """Create and fill the throwaway demo database once per server instance."""
    lock_path = f"{settings.DATABASES['default']['NAME']}.lock"
    with open(lock_path, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        call_command("migrate", interactive=False, verbosity=0)

        from apps.accounts.models import User

        if not User.objects.filter(is_sample=True).exists():
            call_command("seed_sample_data", stdout=io.StringIO())
