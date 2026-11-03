#########################
# Agente Económico De IA #
# Agente                 #
#########################
#


import os
import json
from dotenv import load_dotenv
from groq import Groq

from economic_tools import EconomicTools

# Cargar la clave de la API de Groq desde el archivo .env
load_dotenv()

# Nombre del modelo de Groq a usar (igual que en la base original)
MODELO_GROQ = "openai/gpt-oss-120b"

# Lista de herramientas en el formato que espera Groq (function calling).
# Nota: se conserva "consultar_tipo_cambio_api" tal cual estaba en la base,
# y se agregan las 4 herramientas económicas nuevas.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consultar_tipo_cambio_api",
            "description": (
                "Consulta el tipo de cambio actual de una moneda respecto a otras monedas. "
                "Se debe enviar como argumento el código de la moneda que se desea consultar, "
                "por ejemplo USD, EUR, GTQ."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "moneda": {
                        "type": "string",
                        "description": "Código de la moneda a consultar, por ejemplo USD",
                    }
                },
                "required": ["moneda"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_poblacion_total",
            "description": (
                "Consulta la población total de un país usando datos del Banco Mundial. "
                "Regresa el último valor disponible, la variación respecto al dato anterior "
                "y la tendencia (creciente, decreciente o estable)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": (
                            "Código ISO de 3 letras del país, por ejemplo GTM (Guatemala), "
                            "MEX (México), USA (Estados Unidos). Si no se indica, se usa GTM."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pib_per_capita",
            "description": (
                "Consulta el PIB per cápita (en dólares) de un país usando datos del "
                "Banco Mundial. Regresa el último valor disponible, la variación respecto "
                "al dato anterior y la tendencia (creciente, decreciente o estable)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": (
                            "Código ISO de 3 letras del país, por ejemplo GTM (Guatemala), "
                            "MEX (México), USA (Estados Unidos). Si no se indica, se usa GTM."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_exportaciones",
            "description": (
                "Consulta el valor de las exportaciones de bienes y servicios (en dólares) "
                "de un país usando datos del Banco Mundial. Regresa el último valor disponible, "
                "la variación respecto al dato anterior y la tendencia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": (
                            "Código ISO de 3 letras del país, por ejemplo GTM (Guatemala), "
                            "MEX (México), USA (Estados Unidos). Si no se indica, se usa GTM."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_gasto_educacion",
            "description": (
                "Consulta el gasto público en educación como porcentaje del PIB de un país "
                "usando datos del Banco Mundial. Regresa el último valor disponible, "
                "la variación respecto al dato anterior y la tendencia."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pais": {
                        "type": "string",
                        "description": (
                            "Código ISO de 3 letras del país, por ejemplo GTM (Guatemala), "
                            "MEX (México), USA (Estados Unidos). Si no se indica, se usa GTM."
                        ),
                    }
                },
                "required": [],
            },
        },
    },
]

SYSTEM_PROMPT = """
Eres un asistente económico que habla siempre en español, de forma clara y breve.

Cuentas con estas herramientas:
- consultar_tipo_cambio_api: da el tipo de cambio actual de una moneda. La moneda es obligatoria.
- consultar_poblacion_total: da la población total de un país (Banco Mundial).
- consultar_pib_per_capita: da el PIB per cápita en dólares de un país (Banco Mundial).
- consultar_exportaciones: da el valor de las exportaciones de bienes y servicios de un país (Banco Mundial).
- consultar_gasto_educacion: da el gasto público en educación como % del PIB de un país (Banco Mundial).

Para las 4 herramientas del Banco Mundial, el parámetro "pais" es opcional: si el usuario no
indica un país, usa GTM (Guatemala) por defecto. El país siempre debe ser un código ISO de
3 letras (GTM, MEX, USA, SLV, HND, etc.); si el usuario da un nombre de país, conviértelo
tú mismo al código ISO-3 correspondiente antes de llamar a la herramienta.

Cuando una herramienta regrese un resultado con los campos ultimo_valor, variacion_porcentual
y tendencia, explica el dato al usuario de forma sencilla y objetiva: menciona el último valor
y su año, cómo cambió respecto al dato anterior, y la tendencia general. No inventes cifras
que la herramienta no haya dado. Si una herramienta regresa un campo "error", explica ese
error al usuario en español sin inventar datos.
"""


class EconomicAgent:
    """
    Encapsula la conexión con Groq, el system prompt, la lista de
    herramientas y el ciclo de tool calling. La memoria de la
    conversación (BasicMemory) se maneja fuera de esta clase, igual
    que en los ejemplos de la base.
    """

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        self.client = Groq(api_key=api_key)
        self.tools = EconomicTools()

        # Aquí se guarda la última serie de datos (años/valores) que haya
        # devuelto una herramienta económica, para que la interfaz gráfica
        # pueda dibujarla en el panel del gráfico.
        self.ultimo_grafico = None

    def _ejecutar_herramienta(self, nombre: str, argumentos: dict):
        """Ejecuta la función correspondiente de EconomicTools según el
        nombre que pidió el modelo, y guarda los datos de serie si aplica
        para poder graficarlos después."""

        if nombre == "consultar_tipo_cambio_api":
            return self.tools.consultar_tipo_cambio_api(
                moneda=argumentos.get("moneda", "")
            )

        elif nombre == "consultar_poblacion_total":
            resultado = self.tools.consultar_poblacion_total(
                pais=argumentos.get("pais", "GTM")
            )

        elif nombre == "consultar_pib_per_capita":
            resultado = self.tools.consultar_pib_per_capita(
                pais=argumentos.get("pais", "GTM")
            )

        elif nombre == "consultar_exportaciones":
            resultado = self.tools.consultar_exportaciones(
                pais=argumentos.get("pais", "GTM")
            )

        elif nombre == "consultar_gasto_educacion":
            resultado = self.tools.consultar_gasto_educacion(
                pais=argumentos.get("pais", "GTM")
            )

        else:
            print(f"Se intentó llamar a una herramienta desconocida: {nombre}")
            return {"error": f"Herramienta desconocida: {nombre}"}

        # Si el resultado trae una serie de años/valores (las 4 herramientas
        # económicas nuevas la incluyen), la guardamos para graficarla.
        if isinstance(resultado, dict) and "serie_anios" in resultado:
            self.ultimo_grafico = {
                "pais": resultado.get("pais"),
                "indicador": resultado.get("indicador"),
                "unidad": resultado.get("unidad"),
                "anios": resultado.get("serie_anios"),
                "valores": resultado.get("serie_valores"),
            }

        return resultado

    def enviar_mensaje(self, memoria_mensajes: list, texto_usuario: str) -> str:
        """
        Recibe el historial de la memoria (lista de mensajes) y el texto
        nuevo del usuario. Ejecuta el ciclo de tool calling con Groq y
        regresa el texto final de la respuesta del asistente.
        """

        # Antes de cada mensaje nuevo se limpia el último gráfico, para que
        # la interfaz solo muestre un gráfico nuevo si en esta ronda
        # realmente se llamó a una herramienta económica.
        self.ultimo_grafico = None

        mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
        mensajes.extend(memoria_mensajes)
        mensajes.append({"role": "user", "content": texto_usuario})

        while True:
            respuesta = self.client.chat.completions.create(
                model=MODELO_GROQ,
                messages=mensajes,
                tools=TOOLS,
            )

            msg = respuesta.choices[0].message

            # Si el modelo ya no pide llamar herramientas, esta es la
            # respuesta final para mostrar al usuario.
            if not getattr(msg, "tool_calls", None):
                return msg.content or ""

            mensajes.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
                }
            )

            for tool_call in msg.tool_calls:
                nombre = tool_call.function.name
                argumentos = json.loads(tool_call.function.arguments or "{}")

                resultado = self._ejecutar_herramienta(nombre, argumentos)

                mensajes.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(resultado, ensure_ascii=False),
                    }
                )
