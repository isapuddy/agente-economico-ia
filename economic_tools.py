#########################
# Agente Económico De IA #
# Herramientas           #
#########################

import requests
from datetime import datetime

# URL base de la API del Banco Mundial. No necesita API key.
WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2/country"

# Rango de años que se pide a la API. Se usa un rango amplio porque
# el Banco Mundial no siempre tiene el dato del año más reciente
# publicado todavía (a veces el último dato real es de hace 1 o 2 años).
ANIO_INICIO = 2000
ANIO_FIN = datetime.now().year


class EconomicTools:

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # HERRAMIENTA ORIGINAL DE LA BASE (NO SE MODIFICÓ, SOLO SE CONSERVÓ)
    # ------------------------------------------------------------------
    def consultar_tipo_cambio_api(self, moneda: str):
        print(f"Herramienta consultar_tipo_cambio_api llamada con moneda: {moneda}")

        if not moneda:
            return "Error: Se requiere el código de la moneda para obtener el tipo de cambio."

        # URL del servicio para obtener el tipo de cambio según la moneda:
        url = (
            f"https://open.er-api.com/v6/latest/{moneda.upper()}"
        )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Lanza una excepción si la respuesta no es exitosa
            return response.json()  # Intentar decodificar la respuesta como JSON
        except Exception as e:
            print(f"Error al obtener_tipo_cambio_api: {moneda}. Error: {e}")
            return f"ERROR: No se pudo obtener el tipo de cambio para la moneda: {moneda}"

    # ------------------------------------------------------------------
    # FUNCIÓN INTERNA COMPARTIDA (no es una herramienta que llame el modelo,
    # es un ayudante que usan las 4 herramientas económicas nuevas para no
    # repetir el mismo código de consulta y análisis 4 veces).
    # ------------------------------------------------------------------
    def _consultar_indicador_banco_mundial(
        self,
        pais: str,
        codigo_indicador: str,
        nombre_indicador: str,
        unidad: str,
    ):
        pais = (pais or "GTM").strip().upper()

        url = (
            f"{WORLD_BANK_BASE_URL}/{pais}/indicator/{codigo_indicador}"
            f"?format=json&per_page=100&date={ANIO_INICIO}:{ANIO_FIN}"
        )

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error al consultar {codigo_indicador} para {pais}: {e}")
            return {
                "error": f"No se pudo consultar el indicador para el país '{pais}'. "
                         f"Verifica que el código de país ISO-3 sea correcto (ej. GTM, MEX, USA)."
            }

        # La API del Banco Mundial regresa una lista: [metadata, datos]
        # Si el país no existe o el código está mal, regresa un mensaje de error
        # en vez de la lista esperada.
        if not isinstance(data, list) or len(data) < 2 or data[1] is None:
            return {
                "error": f"El país '{pais}' no parece válido o no tiene datos para "
                         f"este indicador. Usa un código ISO-3 como GTM, MEX, USA, SLV, etc."
            }

        registros = data[1]

        # Filtrar solo los registros que sí tienen un valor numérico
        # (el Banco Mundial regresa 'value: null' en los años sin dato)
        puntos = [
            (int(r["date"]), r["value"])
            for r in registros
            if r.get("value") is not None
        ]

        if not puntos:
            return {
                "error": f"No hay datos disponibles de '{nombre_indicador}' para el país '{pais}'."
            }

        # Ordenar del año más antiguo al más reciente para poder graficar
        # y calcular la tendencia correctamente
        puntos.sort(key=lambda x: x[0])

        anios = [p[0] for p in puntos]
        valores = [p[1] for p in puntos]

        ultimo_anio, ultimo_valor = puntos[-1]

        # Variación respecto al dato anterior disponible (no necesariamente
        # el año calendario anterior, porque puede faltar algún año)
        if len(puntos) >= 2:
            anio_anterior, valor_anterior = puntos[-2]
            variacion_absoluta = ultimo_valor - valor_anterior
            if valor_anterior != 0:
                variacion_porcentual = round((variacion_absoluta / valor_anterior) * 100, 2)
            else:
                variacion_porcentual = None
        else:
            anio_anterior, valor_anterior = None, None
            variacion_absoluta = None
            variacion_porcentual = None

        # Tendencia simple: se compara el último valor contra el valor de
        # aproximadamente 5 datos atrás (o el primero disponible si hay menos).
        # Es un análisis objetivo y sencillo, no una predicción.
        indice_referencia = max(0, len(puntos) - 6)
        anio_referencia, valor_referencia = puntos[indice_referencia]

        if valor_referencia != 0 and valor_referencia is not None:
            cambio_referencia_pct = ((ultimo_valor - valor_referencia) / valor_referencia) * 100
        else:
            cambio_referencia_pct = 0

        if cambio_referencia_pct > 2:
            tendencia = "creciente"
        elif cambio_referencia_pct < -2:
            tendencia = "decreciente"
        else:
            tendencia = "estable"

        return {
            "pais": pais,
            "indicador": nombre_indicador,
            "unidad": unidad,
            "ultimo_anio": ultimo_anio,
            "ultimo_valor": round(ultimo_valor, 2),
            "anio_anterior": anio_anterior,
            "valor_anterior": round(valor_anterior, 2) if valor_anterior is not None else None,
            "variacion_absoluta": round(variacion_absoluta, 2) if variacion_absoluta is not None else None,
            "variacion_porcentual": variacion_porcentual,
            "tendencia": tendencia,
            "comparado_con_anio": anio_referencia,
            "serie_anios": anios,
            "serie_valores": valores,
        }

    # ------------------------------------------------------------------
    # HERRAMIENTAS ECONÓMICAS NUEVAS
    # ------------------------------------------------------------------

    # 1) Población total
    #    Código Banco Mundial: SP.POP.TOTL
    #    Por qué se eligió: es la base para interpretar cualquier otro
    #    indicador económico "per cápita" o relativo, y es un dato muy
    #    intuitivo para empezar a explicar el tamaño de una economía.
    def consultar_poblacion_total(self, pais: str = "GTM"):
        print(f"Herramienta consultar_poblacion_total llamada con pais: {pais}")
        return self._consultar_indicador_banco_mundial(
            pais=pais,
            codigo_indicador="SP.POP.TOTL",
            nombre_indicador="Población total",
            unidad="personas",
        )

    # 2) PIB per cápita (US$ a precios actuales)
    #    Código Banco Mundial: NY.GDP.PCAP.CD
    #    Por qué se eligió: a diferencia del PIB total (que ya existe en
    #    otra versión), el PIB per cápita permite comparar el nivel de
    #    riqueza promedio entre países de distinto tamaño de población,
    #    algo que el PIB total no muestra por sí solo.
    def consultar_pib_per_capita(self, pais: str = "GTM"):
        print(f"Herramienta consultar_pib_per_capita llamada con pais: {pais}")
        return self._consultar_indicador_banco_mundial(
            pais=pais,
            codigo_indicador="NY.GDP.PCAP.CD",
            nombre_indicador="PIB per cápita",
            unidad="USD por persona",
        )

    # 3) Exportaciones de bienes y servicios (US$ a precios actuales)
    #    Código Banco Mundial: NE.EXP.GNFS.CD
    #    Por qué se eligió: muestra la capacidad de un país de generar
    #    ingresos vendiendo al exterior, y es distinto a la "balanza
    #    comercial" (que resta importaciones) porque aquí se analiza solo
    #    el lado de las exportaciones y su evolución en el tiempo.
    def consultar_exportaciones(self, pais: str = "GTM"):
        print(f"Herramienta consultar_exportaciones llamada con pais: {pais}")
        return self._consultar_indicador_banco_mundial(
            pais=pais,
            codigo_indicador="NE.EXP.GNFS.CD",
            nombre_indicador="Exportaciones de bienes y servicios",
            unidad="USD",
        )

    # 4) Gasto público en educación (% del PIB)
    #    Código Banco Mundial: SE.XPD.TOTL.GD.ZS
    #    Por qué se eligió: es un indicador de inversión social/estructural
    #    que no tiene relación directa con los indicadores excluidos
    #    (PIB, inflación, desempleo, balanza comercial, IED), y permite
    #    analizar economía desde el ángulo de las políticas públicas.
    def consultar_gasto_educacion(self, pais: str = "GTM"):
        print(f"Herramienta consultar_gasto_educacion llamada con pais: {pais}")
        return self._consultar_indicador_banco_mundial(
            pais=pais,
            codigo_indicador="SE.XPD.TOTL.GD.ZS",
            nombre_indicador="Gasto público en educación",
            unidad="% del PIB",
        )
