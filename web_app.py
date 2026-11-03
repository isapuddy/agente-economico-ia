#########################
# Agente Económico De IA #
# Interfaz web (chat)    #
#########################
#
# Este archivo levanta la página de chat del agente. Funciona de dos formas:
#
#   EN TU LAPTOP:   python web_app.py   (se abre en http://127.0.0.1:5000)
#   EN INTERNET:    Render lo ejecuta con gunicorn (ver guía de publicación)
#
# NO modifica economic_agent.py ni economic_tools.py: solo los usa.
# Como en internet varias personas pueden usar el agente al mismo tiempo,
# cada visitante tiene su propia conversación y su propia memoria.


import os
import sys
import time
import threading
import webbrowser
from collections import defaultdict, deque

from flask import Flask, jsonify, request, send_from_directory
from groq import APIConnectionError, AuthenticationError, RateLimitError

from basic_memory import BasicMemory
from economic_agent import EconomicAgent

# ----------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------
MEMORY_MAX_MESSAGES = 10          # mensajes que recuerda cada conversación
MAX_CARACTERES = 1500             # largo máximo de una pregunta
MENSAJES_POR_MINUTO = 12          # límite por visitante, para cuidar tu clave de Groq
CONVERSACION_EXPIRA_SEG = 2 * 60 * 60   # una conversación sin uso se borra a las 2 horas
MAX_CONVERSACIONES = 300          # conversaciones guardadas a la vez como máximo

PUERTO = int(os.environ.get("PORT", 5000))
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_INTERFAZ = "interfaz_chat.html"

# La clave se lee del archivo .env en tu laptop (lo hace economic_agent.py),
# o de las variables de entorno de Render cuando está en internet.
if not os.environ.get("GROQ_API_KEY"):
    print("\nFalta la variable GROQ_API_KEY.")
    print("  En tu laptop: revisa que el archivo .env esté en esta carpeta.")
    print("  En Render: agrégala en la pestaña Environment del servicio.\n")
    sys.exit(1)


class AgenteWeb(EconomicAgent):
    """
    Versión del agente para la web. Hereda TODO de EconomicAgent y solo
    agrega una lista de gráficos: así, si en una misma pregunta el agente
    consulta varios países (por ejemplo, "compara Guatemala con México"),
    la interfaz puede dibujar todas las series y no solo la última.
    """

    def __init__(self):
        super().__init__()
        self.graficos = []

    def _ejecutar_herramienta(self, nombre, argumentos):
        resultado = super()._ejecutar_herramienta(nombre, argumentos)

        if isinstance(resultado, dict) and "serie_anios" in resultado:
            self.graficos.append(
                {
                    "pais": resultado.get("pais"),
                    "indicador": resultado.get("indicador"),
                    "unidad": resultado.get("unidad"),
                    "anios": resultado.get("serie_anios"),
                    "valores": resultado.get("serie_valores"),
                }
            )

        return resultado

    def enviar_mensaje(self, memoria_mensajes, texto_usuario):
        self.graficos = []
        return super().enviar_mensaje(memoria_mensajes, texto_usuario)


# ----------------------------------------------------------------------
# Conversaciones: una por cada visitante (identificada por un código que
# genera el navegador al abrir la página)
# ----------------------------------------------------------------------
conversaciones = {}
candado_general = threading.Lock()
historial_por_ip = defaultdict(deque)


def _limpiar_conversaciones(ahora):
    vencidas = [
        clave for clave, conv in conversaciones.items()
        if ahora - conv["ultimo_uso"] > CONVERSACION_EXPIRA_SEG
    ]
    for clave in vencidas:
        del conversaciones[clave]

    # Si aún hay demasiadas, se eliminan las más antiguas
    if len(conversaciones) >= MAX_CONVERSACIONES:
        ordenadas = sorted(conversaciones.items(), key=lambda par: par[1]["ultimo_uso"])
        for clave, _ in ordenadas[: len(conversaciones) - MAX_CONVERSACIONES + 1]:
            del conversaciones[clave]


def obtener_conversacion(id_conversacion):
    ahora = time.time()
    with candado_general:
        conv = conversaciones.get(id_conversacion)
        if conv is None:
            _limpiar_conversaciones(ahora)
            conv = {
                "memoria": BasicMemory(max_messages=MEMORY_MAX_MESSAGES),
                "agente": AgenteWeb(),
                "candado": threading.Lock(),
                "ultimo_uso": ahora,
            }
            conversaciones[id_conversacion] = conv
        conv["ultimo_uso"] = ahora
        return conv


def id_valido(texto):
    texto = (texto or "").strip()
    if 8 <= len(texto) <= 64 and all(c.isalnum() or c == "-" for c in texto):
        return texto
    return None


def ip_visitante():
    reenviada = request.headers.get("X-Forwarded-For", "")
    return reenviada.split(",")[0].strip() or request.remote_addr or "desconocida"


def supera_limite(ip):
    ahora = time.time()
    with candado_general:
        registro = historial_por_ip[ip]
        while registro and ahora - registro[0] > 60:
            registro.popleft()
        if len(registro) >= MENSAJES_POR_MINUTO:
            return True
        registro.append(ahora)
        return False


# ----------------------------------------------------------------------
# Rutas de la página
# ----------------------------------------------------------------------
app = Flask(__name__)


@app.route("/")
def inicio():
    return send_from_directory(CARPETA, ARCHIVO_INTERFAZ, max_age=0)


@app.route("/salud")
def salud():
    return jsonify({"estado": "ok"})


@app.route("/api/chat", methods=["POST"])
def chat():
    datos = request.get_json(silent=True) or {}
    texto_usuario = (datos.get("mensaje") or "").strip()
    id_conversacion = id_valido(datos.get("conversacion"))

    if not texto_usuario:
        return jsonify({"error": "Escribe una pregunta antes de enviar."}), 400
    if len(texto_usuario) > MAX_CARACTERES:
        return jsonify({"error": f"La pregunta es muy larga. Usa menos de {MAX_CARACTERES} caracteres."}), 400
    if not id_conversacion:
        return jsonify({"error": "Recarga la página para iniciar una conversación nueva."}), 400
    if supera_limite(ip_visitante()):
        return jsonify({"error": "Enviaste muchas preguntas seguidas. Espera un minuto y vuelve a intentarlo."}), 429

    conv = obtener_conversacion(id_conversacion)

    with conv["candado"]:
        try:
            respuesta = conv["agente"].enviar_mensaje(conv["memoria"].messages(), texto_usuario)
        except RateLimitError:
            return jsonify({"error": "El servicio de IA alcanzó su límite de uso por ahora. Espera un minuto y vuelve a intentarlo."}), 429
        except AuthenticationError:
            print("Groq rechazó la clave: revisa GROQ_API_KEY.")
            return jsonify({"error": "La clave del servicio de IA no es válida. Hay que revisar la configuración del agente."}), 500
        except APIConnectionError:
            return jsonify({"error": "No se pudo conectar con el servicio de IA. Intenta de nuevo en unos segundos."}), 502
        except Exception as e:
            print(f"Error al procesar el mensaje: {e}")
            return jsonify({"error": "El agente no pudo responder esta vez. Intenta de nuevo o reformula la pregunta."}), 500

        conv["memoria"].add("user", texto_usuario)
        conv["memoria"].add("assistant", respuesta)
        graficos = list(conv["agente"].graficos)

    return jsonify({"respuesta": respuesta, "graficos": graficos})


@app.route("/api/nueva-conversacion", methods=["POST"])
def nueva_conversacion():
    datos = request.get_json(silent=True) or {}
    id_conversacion = id_valido(datos.get("conversacion"))
    if id_conversacion:
        with candado_general:
            conversaciones.pop(id_conversacion, None)
    return jsonify({"ok": True})


# ----------------------------------------------------------------------
# Arranque en tu laptop (en Render no se usa esta parte, usa gunicorn)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    url = f"http://127.0.0.1:{PUERTO}"

    print("\n" + "=" * 56)
    print("  Agente Económico IA listo")
    print(f"  Abre en tu navegador: {url}")
    print("  Para apagarlo: presiona Ctrl + C en esta ventana")
    print("=" * 56 + "\n")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
