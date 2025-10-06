from typing import Optional

from django.db import connections
from django.db.utils import OperationalError


def is_database_connected(alias: str = 'default') -> bool:
    """Return True if the given database alias is reachable, else False.

    Performs a lightweight "SELECT 1" to validate connectivity and credentials.
    """
    try:
        connection = connections[alias]
        # Ensure stale/broken connections are closed before testing
        connection.close_if_unusable_or_obsolete()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except OperationalError:
        return False
    except Exception:
        return False


