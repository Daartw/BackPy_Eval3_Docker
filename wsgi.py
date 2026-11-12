"""Punto de entrada para gunicorn: prepara la base de datos y expone la aplicación."""
import time

from mysql.connector import Error

from app import DatabaseUnavailable, app, init_db, log

__all__ = ["app"]

# MySQL puede tardar unos segundos en aceptar conexiones cuando se levanta junto al servicio.
for attempt in range(1, 11):
    try:
        init_db()
        break
    except (DatabaseUnavailable, Error) as exc:
        log.warning("MySQL no disponible (intento %s/10): %s", attempt, exc)
        if attempt == 10:
            raise
        time.sleep(3)
