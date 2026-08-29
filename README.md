# Sestibalsa Monitor

Pequeño servicio Docker que inicia sesión en la web de Sestibalsa, lee los trabajos pendientes y expone un JSON sencillo para integrarlo con Home Assistant u otros sistemas.

Puede ejecutarse en cualquier host compatible con Docker, por ejemplo Linux, Unraid, Synology, TrueNAS SCALE, Proxmox mediante una VM/LXC con Docker, un VPS o un servidor doméstico.

## Imagen Docker

La imagen se construye y publica automáticamente en GitHub Container Registry cada vez que hay cambios en `main`.

Imagen recomendada:

```text
ghcr.io/rit4lin/sestibalsa-monitor:latest
```

También se publican etiquetas por commit con formato `sha-...` para poder fijar o recuperar una versión concreta si fuera necesario.

La imagen se publica para:

- `linux/amd64`
- `linux/arm64`

## Endpoints

- `/health` — comprobación básica del servicio.
- `/turnos` — devuelve los turnos pendientes. Requiere la cabecera `X-API-Key`.

## Variables de entorno

- `SESTIBALSA_USER`
- `SESTIBALSA_PASSWORD`
- `API_KEY`
- `CACHE_SECONDS` (opcional, por defecto `180`)
- `CONFIG_DIR` (opcional, por defecto `/config`)

## Crear la API key

`API_KEY` es una clave privada que protege el endpoint `/turnos`. Debe ser una cadena larga y aleatoria y utilizarse tanto en el contenedor como en el cliente que consulte la API, por ejemplo Home Assistant.

En Linux, Unraid, macOS o cualquier sistema con OpenSSL puedes generar una clave de 256 bits con:

```bash
openssl rand -hex 32
```

Obtendrás un valor parecido a:

```text
7c391a932a4da42fcb311af84a1f0fd993fbd34f01065ccb2b0d5c36213d95f1
```

Copia ese valor y úsalo como variable de entorno:

```text
API_KEY=7c391a932a4da42fcb311af84a1f0fd993fbd34f01065ccb2b0d5c36213d95f1
```

También puedes generarla con Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

No reutilices contraseñas personales ni la contraseña de Sestibalsa como `API_KEY`.

## Docker

Puerto recomendado:

```text
8765:8765
```

Volumen persistente recomendado:

```text
./config:/config
```

Ejemplo con `docker run` usando la imagen publicada:

```bash
docker run -d \
  --name sestibalsa-monitor \
  --restart unless-stopped \
  -p 8765:8765 \
  -v ./config:/config \
  -e SESTIBALSA_USER="tu_usuario" \
  -e SESTIBALSA_PASSWORD="tu_contraseña" \
  -e API_KEY="tu_api_key" \
  -e CACHE_SECONDS="180" \
  ghcr.io/rit4lin/sestibalsa-monitor:latest
```

En plataformas con interfaz gráfica para Docker, configura esos mismos puertos, variables y el volumen `/config` desde la interfaz.

### Ejemplo en Unraid

En `Repository` usa:

```text
ghcr.io/rit4lin/sestibalsa-monitor:latest
```

Puedes mapear:

```text
/mnt/user/appdata/sestibalsa-monitor -> /config
```

Y configurar las variables de entorno directamente desde la plantilla del contenedor.

## Home Assistant

Ejemplo:

```yaml
rest:
  - resource: "http://IP_DEL_HOST_DOCKER:8765/turnos"
    method: GET
    headers:
      X-API-Key: !secret sestibalsa_api_key
    scan_interval: 60
    timeout: 10
    sensor:
      - name: "Turnos Sestibalsa"
        unique_id: turnos_sestibalsa
        value_template: >
          {{ value_json.resumen | default('Sin turno') }}
        icon: mdi:calendar-clock
        json_attributes:
          - total
          - resumen_turnos
          - turnos
          - actualizado
          - ultimo_nombramiento
          - stale
```

La misma clave configurada en `API_KEY` debe guardarse en `secrets.yaml`:

```yaml
sestibalsa_api_key: "TU_API_KEY"
```

## Icono

El icono del proyecto está disponible en:

```text
https://raw.githubusercontent.com/Rit4lin/sestibalsa-monitor/main/assets/icon.png
```

En Unraid puedes usar esa URL en `Docker -> Sestibalsa -> Edit -> Icon URL`. En otras plataformas puedes reutilizarla donde admitan un icono personalizado.

## Actualizaciones

Los cambios enviados a `main` activan GitHub Actions, que construye y publica automáticamente una nueva imagen `latest` en GHCR.

En un host Docker puedes actualizar con:

```bash
docker pull ghcr.io/rit4lin/sestibalsa-monitor:latest
```

Después recrea o reinicia el contenedor con la nueva imagen según la plataforma utilizada.

## Seguridad

No almacenes las credenciales de Sestibalsa ni la `API_KEY` dentro del repositorio. Configúralas como variables de entorno o mediante el sistema de secretos de tu plataforma Docker.
