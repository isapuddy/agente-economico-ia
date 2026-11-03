#########################
# Agente Económico De IA #
# Interfaz web (chat)    #
#########################
#
# Este archivo levanta una pequeña página web en tu computadora para
# conversar con el agente en una ventana de chat (como ChatGPT o Claude).
# NO modifica economic_agent.py ni economic_tools.py: solo los usa.
#
# Cómo usarlo:
#   1) Activa tu entorno virtual (venv)
#   2) Ejecuta:  python web_app.py
#   3) Se abrirá el navegador en http://127.0.0.1:5000
#   4) Para apagarlo, presiona Ctrl + C en la terminal


import os
import sys
import threading
import webbrowser

from flask import Flask, jsonify, request, send_from_directory

from basic_memory import BasicMemory
from economic_agent import EconomicAgent

MEMORY_MAX_MESSAGES = 10
PUERTO = 5000
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_INTERFAZ = "interfaz_chat.html"


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
# Arranque del agente y de la memoria
# ----------------------------------------------------------------------
try:
    agente = AgenteWeb()
except Exception as e:
    print("\nNo se pudo iniciar el agente.")
    print("Revisa que el archivo .env esté en esta carpeta y tenga tu GROQ_API_KEY.")
    print(f"Detalle: {e}\n")
    sys.exit(1)

memoria = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)

# El candado evita que dos mensajes se procesen al mismo tiempo y se
# mezclen en la memoria de la conversación.
candado = threading.Lock()

app = Flask(__name__)


@app.route("/")
def inicio():
    return send_from_directory(CARPETA, ARCHIVO_INTERFAZ, max_age=0)


@app.route("/api/chat", methods=["POST"])
def chat():
    datos = request.get_json(silent=True) or {}
    texto_usuario = (datos.get("mensaje") or "").strip()

    if not texto_usuario:
        return jsonify({"error": "Escribe una pregunta antes de enviar."}), 400

    with candado:
        try:
            respuesta = agente.enviar_mensaje(memoria.messages(), texto_usuario)
        except Exception as e:
            print(f"Error al procesar el mensaje: {e}")
            return jsonify({"error": f"El agente no pudo responder. Detalle: {e}"}), 500

        memoria.add("user", texto_usuario)
        memoria.add("assistant", respuesta)
        graficos = list(agente.graficos)

    return jsonify({"respuesta": respuesta, "graficos": graficos})


@app.route("/api/nueva-conversacion", methods=["POST"])
def nueva_conversacion():
    global memoria
    with candado:
        memoria = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)
    return jsonify({"ok": True})


if __name__ == "__main__":
    url = f"http://127.0.0.1:{PUERTO}"

    print("\n" + "=" * 56)
    print("  Agente Económico IA listo")
    print(f"  Abre en tu navegador: {url}")
    print("  Para apagarlo: presiona Ctrl + C en esta ventana")
    print("=" * 56 + "\n")

    # Abre el navegador automáticamente un segundo y medio después
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host="127.0.0.1", port=PUERTO, debug=False)
