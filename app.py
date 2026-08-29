import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

app = Flask(__name__)

BASE = "https://www.sestibalsa.es"
LOGIN = BASE + "/trab/logon.aspx?ReturnUrl=%2ftrab%2fdefault.aspx"
TURNOS = BASE + "/trab/trabpend.aspx"

USERNAME = os.environ["SESTIBALSA_USER"]
PASSWORD = os.environ["SESTIBALSA_PASSWORD"]
API_KEY = os.environ["API_KEY"]
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "180"))
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", "/config"))
CACHE_FILE = CONFIG_DIR / "cache.json"
TZ = ZoneInfo("Europe/Madrid")

cache = None
cache_timestamp = 0
cache_lock = Lock()


def cargar_cache_disco():
    global cache
    try:
        if CACHE_FILE.exists():
            with CACHE_FILE.open("r", encoding="utf-8") as f:
                cache = json.load(f)
    except Exception as e:
        print(f"No se pudo cargar cache.json: {e}", flush=True)


def guardar_cache_disco(datos):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with CACHE_FILE.open("w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"No se pudo guardar cache.json: {e}", flush=True)


def hidden_value(soup, name):
    elemento = soup.find("input", {"name": name})
    if not elemento:
        raise RuntimeError(f"No se encuentra {name}")
    return elemento.get("value", "")


def limpiar_texto(texto):
    if texto is None:
        return None
    return " ".join(texto.split())


def obtener_horario(jornada):
    if not jornada:
        return None
    match = re.search(r"(\d{1,2})\s*[-–]\s*(\d{1,2})", jornada)
    if not match:
        return None
    inicio = int(match.group(1))
    fin = int(match.group(2))
    return f"{inicio:02d}-{fin:02d}"


def parse_jornada(fecha, jornada):
    resultado = {"inicio": None, "fin": None}
    horario = obtener_horario(jornada)
    if not horario:
        return resultado
    try:
        inicio_h, fin_h = [int(x) for x in horario.split("-")]
        fecha_dt = datetime.strptime(fecha, "%d/%m/%Y")
        inicio = fecha_dt.replace(hour=inicio_h, minute=0, second=0, microsecond=0, tzinfo=TZ)
        fin = fecha_dt.replace(hour=fin_h, minute=0, second=0, microsecond=0, tzinfo=TZ)
        if fin <= inicio:
            fin += timedelta(days=1)
        resultado["inicio"] = inicio.isoformat()
        resultado["fin"] = fin.isoformat()
    except Exception:
        pass
    return resultado


def obtener_turnos():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/152 Safari/537.36"
    })

    response = session.get(LOGIN, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    datos_login = {
        "__VIEWSTATE": hidden_value(soup, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": hidden_value(soup, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": hidden_value(soup, "__EVENTVALIDATION"),
        "TextBox1": USERNAME,
        "TextBox2": PASSWORD,
        "Button1": "Entrar",
    }

    response = session.post(LOGIN, data=datos_login, timeout=20, allow_redirects=True)
    response.raise_for_status()
    if "logon.aspx" in response.url.lower():
        raise RuntimeError("Login de Sestibalsa incorrecto")

    response = session.get(TURNOS, timeout=20)
    response.raise_for_status()
    if "logon.aspx" in response.url.lower():
        raise RuntimeError("La sesión de Sestibalsa no es válida")

    soup = BeautifulSoup(response.text, "html.parser")
    tabla = soup.find("table", id="dg")
    if tabla is None:
        raise RuntimeError("No encuentro la tabla #dg")

    ultimo = soup.find("span", id="lInfo")
    ultimo_nombramiento = limpiar_texto(ultimo.get_text(" ", strip=True)) if ultimo else None

    turnos = []
    filas = tabla.find_all("tr")

    for fila in filas[1:]:
        celdas = [limpiar_texto(celda.get_text(" ", strip=True)) for celda in fila.find_all("td")]
        if len(celdas) < 10:
            continue

        turno = {
            "peticion": celdas[0],
            "fecha": celdas[1],
            "jornada": celdas[2],
            "orden": celdas[3],
            "categoria": celdas[4],
            "mano": celdas[5],
            "empresa": celdas[6],
            "muelle": celdas[7],
            "buque": celdas[8],
            "capataz": celdas[9],
        }

        horario = obtener_horario(turno["jornada"])
        turno["horario"] = horario
        turno.update(parse_jornada(turno["fecha"], turno["jornada"]))
        turno["resumen"] = f'{turno["fecha"]} {horario or turno["jornada"]}'
        turnos.append(turno)

    turnos.sort(key=lambda x: x["inicio"] if x["inicio"] else "9999")
    resumen_turnos = [turno["resumen"] for turno in turnos]

    return {
        "actualizado": datetime.now(TZ).isoformat(),
        "ultimo_nombramiento": ultimo_nombramiento,
        "total": len(turnos),
        "resumen": resumen_turnos[0] if resumen_turnos else "Sin turno",
        "resumen_turnos": resumen_turnos,
        "proximo": turnos[0] if turnos else None,
        "turnos": turnos,
        "stale": False,
    }


def datos():
    global cache, cache_timestamp
    ahora = time.time()

    with cache_lock:
        if cache is not None and ahora - cache_timestamp < CACHE_SECONDS:
            return cache

        try:
            nuevos_datos = obtener_turnos()
            cache = nuevos_datos
            cache_timestamp = ahora
            guardar_cache_disco(cache)
            return cache
        except Exception as e:
            if cache is not None:
                datos_cache = dict(cache)
                datos_cache["stale"] = True
                datos_cache["error_actualizacion"] = str(e)
                return datos_cache
            raise


@app.before_request
def comprobar_api_key():
    if request.path == "/health":
        return None
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/turnos")
def turnos():
    try:
        return jsonify(datos())
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/")
def index():
    return jsonify({"servicio": "Sestibalsa Monitor", "endpoints": ["/health", "/turnos"]})


cargar_cache_disco()
