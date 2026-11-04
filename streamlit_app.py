#########################
# Agente Económico De IA #
# Interfaz en Streamlit  #
#########################
#
# Cómo usarlo:
#   EN TU LAPTOP:   streamlit run streamlit_app.py
#   EN INTERNET:    Streamlit Community Cloud (share.streamlit.io)
#
# NO modifica economic_agent.py ni economic_tools.py: solo los usa.
# Los colores y las fuentes están en el archivo .streamlit/config.toml


import os
import time
from datetime import datetime, timedelta, timezone

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Agente Económico IA",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="expanded",
)

from groq import APIConnectionError, AuthenticationError, RateLimitError

from basic_memory import BasicMemory
from economic_agent import EconomicAgent  # al importarlo se lee el archivo .env

# ----------------------------------------------------------------------
# Clave de Groq: en tu laptop viene del archivo .env; en Streamlit Cloud
# viene de la sección "Secrets" de la app.
# ----------------------------------------------------------------------
if not os.environ.get("GROQ_API_KEY"):
    try:
        os.environ["GROQ_API_KEY"] = st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

if not os.environ.get("GROQ_API_KEY"):
    st.error(
        "Falta la clave **GROQ_API_KEY**. En tu laptop, revisa que el archivo .env esté "
        "en esta carpeta. En Streamlit Cloud, agrégala en Settings > Secrets."
    )
    st.stop()

# ----------------------------------------------------------------------
# Configuración y contenido editable
# ----------------------------------------------------------------------
MEMORY_MAX_MESSAGES = 10
MENSAJES_POR_MINUTO = 12
HORA_GUATEMALA = timezone(timedelta(hours=-6))

INDICADORES = [
    ("Población total", ":material/groups:", "¿Cuál es la población de Guatemala y cómo ha cambiado?"),
    ("PIB per cápita", ":material/payments:", "¿Cómo ha evolucionado el PIB per cápita de Guatemala?"),
    ("Exportaciones", ":material/sailing:", "¿Cómo han cambiado las exportaciones de Guatemala?"),
    ("Gasto en educación", ":material/school:", "¿Cuánto invierte Guatemala en educación como porcentaje del PIB?"),
    ("Tipo de cambio", ":material/currency_exchange:", "¿A cuánto está el dólar en quetzales hoy?"),
]

IDEAS = [
    (":material/payments:", "Compara el PIB per cápita de Guatemala, El Salvador y Honduras"),
    (":material/groups:", "¿Cómo ha crecido la población de Guatemala desde el 2000?"),
    (":material/school:", "¿Cuánto gasta Costa Rica en educación?"),
    (":material/currency_exchange:", "¿A cuánto está el dólar en quetzales hoy?"),
]

PAISES = {
    "GTM": "Guatemala", "SLV": "El Salvador", "HND": "Honduras", "NIC": "Nicaragua",
    "CRI": "Costa Rica", "PAN": "Panamá", "BLZ": "Belice", "MEX": "México",
    "USA": "Estados Unidos", "CAN": "Canadá", "DOM": "República Dominicana",
    "CUB": "Cuba", "COL": "Colombia", "VEN": "Venezuela", "ECU": "Ecuador",
    "PER": "Perú", "BOL": "Bolivia", "CHL": "Chile", "ARG": "Argentina",
    "URY": "Uruguay", "PRY": "Paraguay", "BRA": "Brasil", "ESP": "España",
    "DEU": "Alemania", "FRA": "Francia", "GBR": "Reino Unido", "ITA": "Italia",
    "CHN": "China", "JPN": "Japón", "IND": "India", "KOR": "Corea del Sur",
}

# Jade, maíz, quetzal, azul lago y gris
COLORES_SERIE = ["#1d7a66", "#d29a2f", "#c0392b", "#2c5d8a", "#6b7471"]
AVATAR_AGENTE = ":material/query_stats:"

# ----------------------------------------------------------------------
# Estilos extra (lo que no se puede hacer solo con config.toml)
# ----------------------------------------------------------------------
st.markdown(
    """
<style>
  .block-container { max-width: 880px; padding-top: 2.6rem; }

  /* Marca en la barra lateral */
  .marca { display: flex; align-items: center; gap: 12px; margin: 4px 0 18px; }
  .marca-logo {
    flex: none; display: grid; place-items: center; width: 44px; height: 44px;
    border-radius: 12px; background: #16504a; box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
  }
  .marca h1 {
    margin: 0 !important; padding: 0 !important; font-size: 1.25rem !important;
    line-height: 1.15 !important; color: #ffffff !important; text-wrap: balance;
  }
  .marca p { margin: 2px 0 0 !important; font-size: .82rem !important; color: #9dbab1 !important; }
  .etiqueta-lateral {
    margin: 16px 0 4px !important; font-size: .82rem !important; font-weight: 600; color: #9dbab1 !important;
  }
  ul.fuentes { margin: 0 !important; padding: 0 !important; list-style: none; }
  ul.fuentes li { margin: 0 !important; padding: 3px 0 !important; font-size: .9rem !important; }
  ul.fuentes small { display: block; color: #9dbab1; font-size: .8rem; }
  .nota-lateral {
    margin-top: 18px; padding: 12px; border-radius: 12px; background: #16504a;
    font-size: .8rem !important; line-height: 1.45; color: #9dbab1;
  }
  .nota-lateral strong { color: #e4eeea; }

  /* Botones de indicadores en la barra lateral */
  .st-key-indicadores button {
    justify-content: flex-start; border: 0; background: transparent; color: #e4eeea;
    border-radius: 10px; padding: .45rem .6rem; min-height: 2.6rem;
  }
  .st-key-indicadores button:hover { background: #16504a; color: #ffffff; }
  .st-key-indicadores button > div, .st-key-ideas button > div { width: 100%; justify-content: flex-start; }
  .st-key-indicadores button > div > span, .st-key-ideas button > div > span { gap: 12px; align-items: center; }
  .st-key-indicadores button p, .st-key-ideas button p { text-align: left; white-space: normal; }
  .st-key-indicadores button span[data-testid="stIconMaterial"],
  .st-key-ideas button span[data-testid="stIconMaterial"] {
    width: 32px !important; min-width: 32px; height: 32px; display: grid; place-items: center;
    border-radius: 9px; font-size: 18px;
  }
  .st-key-indicadores button span:has(> [data-testid="stIconMaterial"]),
  .st-key-ideas button span:has(> [data-testid="stIconMaterial"]) { width: auto !important; flex: none; }
  .st-key-indicadores button span[data-testid="stIconMaterial"] { color: #ffffff; background: rgba(255,255,255,.09); }
  .st-key-boton_nueva button { border-color: #2f6d64; color: #ffffff; }
  .st-key-boton_nueva button:hover { border-color: #d29a2f; color: #ffffff; }

  /* Portada */
  .portada h1 {
    max-width: 17ch; margin: 3vh 0 .6rem !important; padding: 0 !important;
    font-size: clamp(2rem, 4.4vw, 2.85rem) !important; line-height: 1.05 !important;
    letter-spacing: -0.025em; color: #0f3d36 !important; text-wrap: balance;
  }
  .portada p { max-width: 56ch; margin-bottom: 1.4rem !important; font-size: 1.05rem !important; color: #5a6965 !important; }
  .st-key-ideas button {
    justify-content: flex-start; text-align: left; min-height: 4.2rem; padding: .8rem 1rem;
    background: #ffffff; border: 1px solid #d7e1dd; border-radius: 14px; color: #14201d;
  }
  .st-key-ideas button:hover { border-color: #1d7a66; color: #14201d; }
  .st-key-ideas button p { font-weight: 500; }
  .st-key-ideas button span[data-testid="stIconMaterial"] { color: #155d4e; background: #e2f0eb; }

  /* Burbujas del chat */
  [data-testid="stChatMessage"] {
    padding: .9rem 1.1rem; border-radius: 6px 18px 18px 18px;
    background: #ffffff; border: 1px solid #d7e1dd;
  }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse; width: fit-content !important; max-width: 85%; margin-left: auto;
    border-radius: 18px 6px 18px 18px; background: #1d7a66; border-color: #1d7a66; color: #ffffff;
  }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) * { color: #ffffff; }
  [data-testid="stChatMessageAvatarUser"] { background: #155d4e; color: #ffffff; }
  [data-testid="stChatMessageAvatarCustom"] { background: #0f3d36; border-radius: 10px; }
  [data-testid="stChatMessageAvatarCustom"], [data-testid="stChatMessageAvatarCustom"] * { color: #ffffff !important; }
  .hora { margin-top: 2px; font-size: .74rem !important; color: #5a6965; text-align: right; }
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .hora { color: rgba(255,255,255,.75); }
  [data-testid="stChatMessage"] li::marker { color: #1d7a66; font-weight: 700; }

  /* Tarjeta de cada gráfica */
  [class*="st-key-grafico"] { background: #f4f7f6; border-radius: 14px; padding: 14px 16px 16px; }
  p.grafico-titulo { margin: 0 !important; font-weight: 700; font-size: 1.05rem !important; color: #0f3d36 !important; }
  p.grafico-unidad { margin: 0 0 2px !important; font-size: .82rem !important; color: #5a6965 !important; }
  [class*="st-key-grafico"] [data-testid="stMetric"] { background: #ffffff; border-radius: 10px; padding: 8px 12px; }
  p.pie-grafico { margin: 0 !important; font-size: .76rem !important; color: #5a6965 !important; }

  /* Caja para escribir en blanco */
  [data-testid="stChatInput"] > div { background-color: #ffffff !important; border: 1.5px solid #d7e1dd; }
  [data-testid="stChatInput"] > div:focus-within { border-color: #1d7a66; }
  [data-testid="stChatInput"] > div div { background-color: transparent !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Agente con lista de gráficos (para comparar varios países a la vez)
# ----------------------------------------------------------------------
class AgenteWeb(EconomicAgent):
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
# Estado de la sesión: cada visitante tiene su propia conversación
# ----------------------------------------------------------------------
def iniciar_estado():
    st.session_state.agente = AgenteWeb()
    st.session_state.memoria = BasicMemory(max_messages=MEMORY_MAX_MESSAGES)
    st.session_state.historial = []
    st.session_state.envios = []
    st.session_state.pendiente = None


if "agente" not in st.session_state:
    iniciar_estado()


def preguntar(texto):
    st.session_state.pendiente = texto


def nueva_conversacion():
    iniciar_estado()


def hora_actual():
    return datetime.now(HORA_GUATEMALA).strftime("%H:%M")


def supera_limite():
    ahora = time.time()
    st.session_state.envios = [t for t in st.session_state.envios if ahora - t < 60]
    if len(st.session_state.envios) >= MENSAJES_POR_MINUTO:
        return True
    st.session_state.envios.append(ahora)
    return False


# ----------------------------------------------------------------------
# Formatos de números
# ----------------------------------------------------------------------
def nombre_pais(codigo):
    return PAISES.get(codigo, codigo or "")


def unir_nombres(nombres):
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def formato_corto(valor, unidad):
    unidad = unidad or ""
    if "%" in unidad:
        return f"{valor:,.1f}%"
    prefijo = "US$ " if "USD" in unidad else ""
    if abs(valor) >= 1e9:
        return f"{prefijo}{valor / 1e9:,.1f} mil M"
    if abs(valor) >= 1e6:
        return f"{prefijo}{valor / 1e6:,.1f} M"
    if abs(valor) >= 100:
        return f"{prefijo}{valor:,.0f}"
    return f"{prefijo}{valor:,.2f}"


def formato_largo(valor, unidad):
    unidad = unidad or ""
    if "%" in unidad:
        return f"{valor:,.2f}% del PIB"
    if "USD" in unidad:
        return f"US$ {valor:,.2f}"
    return f"{valor:,.0f} {unidad}".strip()


def expresion_eje(unidad):
    """Cómo se escriben los números del eje vertical de la gráfica."""
    unidad = unidad or ""
    if "%" in unidad:
        return "format(datum.value, '.1~f') + '%'"
    p = "'US$ ' + " if "USD" in unidad else ""
    return (
        f"datum.value >= 1e9 ? {p}format(datum.value / 1e9, ',.1~f') + ' mil M' : "
        f"datum.value >= 1e6 ? {p}format(datum.value / 1e6, ',.1~f') + ' M' : "
        f"{p}format(datum.value, ',.0f')"
    )


def texto_seguro(texto):
    # En Streamlit el signo $ activa fórmulas matemáticas; así se muestra normal
    return (texto or "").replace("$", "\\$")


# ----------------------------------------------------------------------
# Gráficas
# ----------------------------------------------------------------------
def agrupar_graficos(graficos):
    grupos = {}
    for g in graficos or []:
        if not g or not g.get("anios"):
            continue
        clave = (g.get("indicador"), g.get("unidad"))
        grupo = grupos.setdefault(clave, {"indicador": g.get("indicador"), "unidad": g.get("unidad"), "series": []})
        if all(s["pais"] != g.get("pais") for s in grupo["series"]):
            grupo["series"].append(g)
    return list(grupos.values())


def mostrar_altair(grafica):
    # Las versiones nuevas de Streamlit usan width="stretch" y las anteriores
    # use_container_width=True; así funciona en cualquiera de las dos.
    try:
        st.altair_chart(grafica, width="stretch")
    except TypeError:
        st.altair_chart(grafica, use_container_width=True)


def dibujar_grafico(grupo, clave):
    unidad = grupo["unidad"]
    series = grupo["series"]
    paises = [nombre_pais(s["pais"]) for s in series]
    colores = COLORES_SERIE[: len(paises)]

    with st.container(key=f"grafico_{clave}"):
        st.markdown(
            f'<p class="grafico-titulo">{grupo["indicador"]}: {unir_nombres(paises)}</p>'
            f'<p class="grafico-unidad">{unidad}</p>',
            unsafe_allow_html=True,
        )

        # Último dato de cada país y su variación frente al dato anterior
        columnas = st.columns(min(len(series), 3))
        for i, serie in enumerate(series):
            anios, valores = serie["anios"], serie["valores"]
            delta = None
            if len(valores) >= 2 and valores[-2]:
                cambio = (valores[-1] - valores[-2]) / abs(valores[-2]) * 100
                delta = f"{cambio:+.1f}% vs {anios[-2]}"
            with columnas[i % len(columnas)]:
                st.metric(f"{paises[i]}, {anios[-1]}", formato_corto(valores[-1], unidad), delta)

        filas = [
            {"Año": a, "Valor": v, "País": paises[i], "Dato": formato_largo(v, unidad)}
            for i, s in enumerate(series)
            for a, v in zip(s["anios"], s["valores"])
        ]
        datos = pd.DataFrame(filas)
        anio_min, anio_max = int(datos["Año"].min()), int(datos["Año"].max())

        base = alt.Chart(datos).encode(
            x=alt.X(
                "Año:Q", title=None, scale=alt.Scale(domain=[anio_min, anio_max], nice=False),
                axis=alt.Axis(format="d", tickMinStep=1, labelAngle=0, grid=False),
            ),
            y=alt.Y(
                "Valor:Q", title=None, scale=alt.Scale(zero=False),
                axis=alt.Axis(labelExpr=expresion_eje(unidad), tickCount=5, domain=False, ticks=False),
            ),
            color=alt.Color("País:N", scale=alt.Scale(domain=paises, range=colores), legend=None),
            tooltip=[alt.Tooltip("País:N"), alt.Tooltip("Año:Q", format="d"), alt.Tooltip("Dato:N", title="Valor")],
        )

        capas = []
        if len(series) == 1:
            capas.append(base.mark_area(opacity=0.12, interpolate="monotone", clip=True))
        capas.append(base.mark_line(strokeWidth=2.6, interpolate="monotone"))
        capas.append(base.mark_point(size=60, filled=True, opacity=0))  # zona para el tooltip

        grafica = alt.layer(*capas).properties(height=240).configure_view(stroke=None)
        mostrar_altair(grafica)
        st.markdown(
            f'<p class="pie-grafico">Fuente: Banco Mundial, {anio_min} a {anio_max}.</p>',
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------------
# Mensajes
# ----------------------------------------------------------------------
def mostrar_mensaje(mensaje, indice):
    if mensaje["rol"] == "user":
        with st.chat_message("user"):
            st.markdown(texto_seguro(mensaje["texto"]))
            st.markdown(f'<div class="hora">{mensaje["hora"]}</div>', unsafe_allow_html=True)
        return

    with st.chat_message("assistant", avatar=AVATAR_AGENTE):
        if mensaje.get("error"):
            st.error(mensaje["texto"], icon=":material/error:")
        else:
            st.markdown(texto_seguro(mensaje["texto"]))
            for j, grupo in enumerate(agrupar_graficos(mensaje.get("graficos"))):
                dibujar_grafico(grupo, f"{indice}_{j}")
        st.markdown(f'<div class="hora">{mensaje["hora"]}</div>', unsafe_allow_html=True)


def responder(pregunta):
    historial = st.session_state.historial
    historial.append({"rol": "user", "texto": pregunta, "hora": hora_actual()})
    mostrar_mensaje(historial[-1], len(historial) - 1)

    if supera_limite():
        historial.append({
            "rol": "assistant", "error": True, "hora": hora_actual(),
            "texto": "Enviaste muchas preguntas seguidas. Espera un minuto y vuelve a intentarlo.",
        })
        mostrar_mensaje(historial[-1], len(historial) - 1)
        return

    agente = st.session_state.agente
    memoria = st.session_state.memoria
    error = None

    # Burbuja temporal con el indicador de "consultando" mientras responde
    marcador = st.empty()
    with marcador.container(), st.chat_message("assistant", avatar=AVATAR_AGENTE), st.spinner("Consultando datos..."):
        try:
            respuesta = agente.enviar_mensaje(memoria.messages(), pregunta)
        except RateLimitError:
            error = "El servicio de IA alcanzó su límite de uso por ahora. Espera un minuto y vuelve a intentarlo."
        except AuthenticationError:
            error = "La clave del servicio de IA no es válida. Hay que revisar GROQ_API_KEY en los Secrets."
        except APIConnectionError:
            error = "No se pudo conectar con el servicio de IA. Intenta de nuevo en unos segundos."
        except Exception as e:
            print(f"Error al procesar el mensaje: {e}")
            error = "El agente no pudo responder esta vez. Intenta de nuevo o reformula la pregunta."
    marcador.empty()

    if error:
        historial.append({"rol": "assistant", "error": True, "texto": error, "hora": hora_actual()})
    else:
        memoria.add("user", pregunta)
        memoria.add("assistant", respuesta)
        historial.append({
            "rol": "assistant", "texto": respuesta, "hora": hora_actual(),
            "graficos": list(agente.graficos),
        })
    mostrar_mensaje(historial[-1], len(historial) - 1)


# ----------------------------------------------------------------------
# Barra lateral
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
<div class="marca">
  <div class="marca-logo">
    <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
      <path d="M6 23l6.5-6.5 4.5 3.5 8.5-10" fill="none" stroke="#ffffff" stroke-width="2.6"
            stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="25.5" cy="10" r="3" fill="#e0533f"/>
    </svg>
  </div>
  <div><h1>Agente Económico IA</h1><p>Indicadores de Guatemala y el mundo</p></div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.button("Nueva conversación", icon=":material/add:", key="boton_nueva",
              on_click=nueva_conversacion, width="stretch")

    st.markdown('<p class="etiqueta-lateral">Pregúntame por</p>', unsafe_allow_html=True)
    with st.container(key="indicadores", gap=None):
        for i, (nombre, icono, pregunta_ejemplo) in enumerate(INDICADORES):
            st.button(nombre, icon=icono, key=f"indicador_{i}", on_click=preguntar,
                      args=(pregunta_ejemplo,), width="stretch")

    st.markdown(
        """
<p class="etiqueta-lateral">De dónde vienen los datos</p>
<ul class="fuentes">
  <li>Banco Mundial<small>Series anuales desde el año 2000</small></li>
  <li>ExchangeRate-API<small>Tipo de cambio del día</small></li>
</ul>
<div class="nota-lateral">
  <strong>Recuerdo tus últimos 10 mensajes,</strong> así que puedes hacer preguntas de
  seguimiento como «¿y en México?». El agente puede equivocarse: verifica los datos importantes.
</div>
""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Zona principal
# ----------------------------------------------------------------------
pregunta = st.chat_input("Escribe tu pregunta sobre economía...", max_chars=1500)
if st.session_state.pendiente:
    pregunta = st.session_state.pendiente
    st.session_state.pendiente = None

if not st.session_state.historial and not pregunta:
    st.markdown(
        """
<div class="portada">
  <h1>¿Qué quieres saber de la economía hoy?</h1>
  <p>Consulto datos del Banco Mundial y el tipo de cambio del día, te explico cómo han
  cambiado y te muestro la tendencia en una gráfica.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    with st.container(key="ideas"):
        columnas = st.columns(2)
        for i, (icono, texto) in enumerate(IDEAS):
            with columnas[i % 2]:
                st.button(texto, icon=icono, key=f"idea_{i}", on_click=preguntar,
                          args=(texto,), width="stretch")

for indice, mensaje in enumerate(st.session_state.historial):
    mostrar_mensaje(mensaje, indice)

if pregunta:
    responder(pregunta)
