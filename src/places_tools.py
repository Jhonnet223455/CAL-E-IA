"""
Herramientas para buscar lugares usando Google Places API.
"""
import os
import requests
from langchain.tools import Tool
from weather_tools import obtener_clima_por_latlng


GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


def buscar_lugares_google(query: str) -> str:
    """Busca lugares en Google Places (restaurantes, bares, hoteles) y devuelve lista con clima."""
    print(f"Tool: buscar_lugares_google, Query: {query}")
    try:
        url = "https://places.googleapis.com/v1/places:searchText"
        full_query = f"{query} en Cali"

        payload = {"textQuery": full_query}
        headers = {
            "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
            # Incluimos location para obtener lat/lng
            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.formattedAddress,"
                "places.rating,"
                "places.websiteUri,"
                "places.location"
            )
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        places = data.get('places', [])
        if not places:
            return "No encontré lugares que coincidan con esa búsqueda."

        formatted_results = []
        # Para no exceder cuotas, aplico clima a los primeros 3 (ajústalo si quieres)
        for i, place in enumerate(places[:5], start=1):
            nombre = place.get('displayName', {}).get('text', 'N/A')
            direccion = place.get('formattedAddress', 'N/A')
            rating = place.get('rating', 'N/A')
            web = place.get('websiteUri', 'N/A')

            # Clima (si hay lat/lng)
            clima_txt = ""
            google_maps_url = ""
            loc = place.get('location') or {}
            lat = loc.get('latitude')
            lng = loc.get('longitude')
            if lat is not None and lng is not None:
                # Generar link de Google Maps con coordenadas
                google_maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
                
                # Solo a los primeros 3 para ahorrar llamadas
                if i <= 3:
                    clima_txt = obtener_clima_por_latlng(lat, lng)
                else:
                    clima_txt = "Clima: (toca para ver más detalles)"

            formatted_results.append(
                f"{i}. Nombre: {nombre}\n"
                f"   Dirección: {direccion}\n"
                f"   Rating: {rating}\n"
                f"   Web: {web}\n"
                f"   📍 Google Maps: {google_maps_url}\n"
                f"   {clima_txt}\n"  # Sin "☀️ Pronóstico hoy:" para evitar redundancia
            )

        return "\n".join(formatted_results)

    except Exception as e:
        print(f"Error en API Google Places: {e}")
        return f"Error al contactar la API de Google Places: {e}"


# Crear la herramienta para el agente
tool_google_places = Tool(
    name="buscar_google_places",
    func=buscar_lugares_google,
    description="Busca restaurantes, bares, hoteles y otros lugares de interés en Cali. Útil para recomendaciones, direcciones y calificaciones."
)
