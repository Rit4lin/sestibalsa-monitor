# Sestibalsa Monitor

Pequeño servicio Docker que inicia sesión en la web de Sestibalsa, lee los trabajos pendientes y expone un JSON sencillo para integrarlo con Home Assistant u otros sistemas.

Puede ejecutarse en cualquier host compatible con Docker, por ejemplo Linux, Unraid, Synology, TrueNAS SCALE, Proxmox mediante una VM/LXC con Docker, un VPS o un servidor doméstico.

## Endpoints

- `/health` — comprobación básica del servicio.
- `/turnos` — devuelve los turnos pendientes. Requiere la cabecera `X-API-Key`.

## Variables de entorno

- `SESTIBALSA_USER`
- `SESTIBALSA_PASSWORD`
- `API_KEY`
- `CACHE_SECONDS` (opcional, por defecto `180`)
- `CONFIG_DIR` (opcional, por defecto `/config`)

## Docker

Puerto recomendado:

```text
8765:8765
```

Volumen persistente recomendado:

```text
./config:/config
```

Ejemplo con `docker run`:

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
  sestibalsa-monitor
```

En plataformas con interfaz gráfica para Docker, configura esos mismos puertos, variables y el volumen `/config` desde la interfaz.

### Ejemplo en Unraid

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

## Icono

El icono del proyecto está disponible en:

```text
https://raw.githubusercontent.com/Rit4lin/sestibalsa-monitor/main/assets/icon.png
```

En Unraid puedes usar esa URL en `Docker -> Sestibalsa -> Edit -> Icon URL`. En otras plataformas puedes reutilizarla donde admitan un icono personalizado.

## Seguridad

No almacenes las credenciales de Sestibalsa ni la `API_KEY` dentro del repositorio. Configúralas como variables de entorno o mediante el sistema de secretos de tu plataforma Docker.
