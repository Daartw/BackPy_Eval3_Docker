# Política de seguridad

## Reportar una vulnerabilidad

Si encuentras un problema de seguridad, **no abras un issue público**. Usa
**Security → Report a vulnerability** en este repositorio o escribe a
**danie.arayar@duocuc.cl** con:

- Descripción del problema y su impacto.
- Pasos para reproducirlo.
- Versión o commit afectado.

Responderé dentro de 7 días.

## Medidas implementadas

- El contenedor usa **gunicorn**; el modo debug de Flask está apagado por defecto.
- Crear, editar y eliminar productos exige `X-API-Key` (rutas cerradas si no hay clave configurada).
- Consultas SQL parametrizadas y validación de tipos, rangos y largo en la entrada.
- Los errores no entregan detalles internos al cliente; el detalle queda en el log.
- Cabeceras de seguridad, CORS restringido en producción y límite de tamaño de las peticiones.
- Contenedor sin privilegios de root, dependencias con versión fija y `pip-audit` en CI.

## Al desplegar

- Define `ADMIN_API_KEY`, `CORS_ORIGINS` y las credenciales de MySQL como variables de entorno; nunca las subas al repositorio.
- Usa un usuario de MySQL propio del servicio, sin privilegios de administrador (no `root`).
- Publica el servicio detrás de HTTPS (proxy inverso).
