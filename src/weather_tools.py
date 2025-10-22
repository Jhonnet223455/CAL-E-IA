"""
Herramientas relacionadas con el clima.
"""
import os
import requests
from langchain.tools import Tool


WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def obtener_clima_por_latlng(lat: float, lng: float) -> str:
    """Consulta el pronóstico del clima para una ubicación y devuelve el del día actual."""
    try:
        if not WEATHER_API_KEY:
            return "⚠️ Clima no disponible (falta WEATHER_API_KEY)."

        # URL corregida para usar el pronóstico diario según especificación
        url = "https://weather.googleapis.com/v1/forecast/days:lookup"
        params = {
            "key": WEATHER_API_KEY,
            "location.latitude": lat,
            "location.longitude": lng,
            "unitsSystem": "METRIC",
            "days": "1" # Pedimos solo el pronóstico para el día actual
        }
        
        print(f"[DEBUG] Consultando clima para lat={lat}, lng={lng}")
        resp = requests.get(url, params=params, timeout=10)
        
        print(f"[DEBUG] Status Code: {resp.status_code}")
        print(f"[DEBUG] Response: {resp.text[:500]}")  # Primeros 500 caracteres
        
        if resp.status_code != 200:
            # Intentamos decodificar el error por si Google nos da más detalles
            try:
                error_details = resp.json().get("error", {}).get("message", "")
                print(f"[DEBUG] Error de API: {error_details}")
                return f"Clima no disponible ({resp.status_code}): {error_details}"
            except:
                return f"Clima no disponible ({resp.status_code})."

        data = resp.json() or {}
        print(f"[DEBUG] Estructura de respuesta: {list(data.keys())}")
        
        # CORREGIDO: La respuesta viene en 'forecastDays', no en 'forecast.days'
        forecast_days = data.get("forecastDays", [])
        
        if not forecast_days:
            print(f"[DEBUG] No se encontraron días en forecastDays. Data completo: {data}")
            return "No se encontró pronóstico del clima."

        # Tomamos el primer día de la lista (el día actual)
        today_forecast = forecast_days[0]
        print(f"[DEBUG] Campos del pronóstico: {list(today_forecast.keys())}")
        
        # CORREGIDO: Los campos son maxTemperature y minTemperature (objetos con 'degrees')
        temp_max_obj = today_forecast.get("maxTemperature", {})
        temp_min_obj = today_forecast.get("minTemperature", {})
        temp_max = temp_max_obj.get("degrees") if temp_max_obj else None
        temp_min = temp_min_obj.get("degrees") if temp_min_obj else None
        
        # Obtenemos la condición del clima del pronóstico diurno
        daytime = today_forecast.get("daytimeForecast", {})
        weather_cond = daytime.get("weatherCondition", {})
        cond = weather_cond.get("description", {}).get("text")
        
        # Obtenemos el viento del pronóstico diurno
        wind_obj = daytime.get("wind", {})
        wind_speed = wind_obj.get("speed", {})
        wind = wind_speed.get("value") if wind_speed else None

        partes = []
        if temp_min is not None and temp_max is not None:
            partes.append(f"{temp_min}°C - {temp_max}°C")
        if cond:
            partes.append(str(cond))
        if wind is not None:
            partes.append(f"viento {wind} km/h")

        resultado = " | ".join(partes) if partes else "Pronóstico no disponible."
        print(f"[DEBUG] Resultado final: {resultado}")
        # Agregar emoji al principio para formato consistente
        return f"☀️ {resultado}"
    except Exception as e:
        print(f"[ERROR] Error en API de Clima: {e}")
        import traceback
        traceback.print_exc()
        return "Pronóstico no disponible."
        return "Pronóstico no disponible."


def clima_por_lugar(query: str) -> str:
    """Busca un lugar por texto y devuelve solo clima del primer match."""
    try:
        # CORREGIDO: Usar la URL correcta de Google Places, NO de Weather
        url = "https://places.googleapis.com/v1/places:searchText"
        payload = {"textQuery": f"{query} en Cali"}
        headers = {
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            "X-Goog-FieldMask": "places.displayName,places.location"
        }
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        places = (r.json() or {}).get("places", [])
        if not places:
            return "No encontré ese lugar para consultar su clima."

        loc = places[0].get("location") or {}
        lat, lng = loc.get("latitude"), loc.get("longitude")
        if lat is None or lng is None:
            return "No pude obtener coordenadas de ese lugar."

        clima = obtener_clima_por_latlng(lat, lng)
        nombre = places[0].get("displayName", {}).get("text", "Lugar")
        return f"☀️ Pronóstico para hoy en {nombre}: {clima}"
    except Exception as e:
        return "No logré obtener el clima del lugar."


# Crear la herramienta para el agente
tool_clima_por_lugar = Tool(
    name="clima_por_lugar",
    func=clima_por_lugar,
    description="Devuelve el pronóstico del clima para hoy en un lugar específico de Cali."
)
