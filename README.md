# Sestibalsa Monitor

Pequeño servicio para Unraid que inicia sesión en la web de Sestibalsa, lee los trabajos pendientes y expone un JSON sencillo para Home Assistant.

## Endpoints

- `/health` — comprobación básica del servicio.
- `/turnos` — devuelve los turnos pendientes. Requiere la cabecera `X-API-Key`.

## Variables de entorno

- `SESTIBALSA_USER`
- `SESTIBALSA_PASSWORD`
- `API_KEY`
- `CACHE_SECONDS` (opcional, por defecto `180`)
- `CONFIG_DIR` (opcional, por defecto `/config`)

## Unraid

Puerto recomendado: `8765:8765`.

Ruta persistente recomendada:

```text
/mnt/user/appdata/sestibalsa-monitor -> /config
```

## Home Assistant

Ejemplo:

```yaml
rest:
  - resource: "http://192.168.1.11:8765/turnos"
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

## Icono para Unraid

Usa esta URL en `Docker -> Sestibalsa -> Edit -> Icon URL`:

```text
https://raw.githubusercontent.com/Rit4lin/sestibalsa-monitor/main/assets/icon.png
```

Las credenciales no deben almacenarse en el repositorio. Configúralas como variables de entorno en Unraid.
