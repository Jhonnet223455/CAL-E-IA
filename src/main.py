import os
import requests
from dotenv import load_dotenv
import asyncio # <-- Corregido: Importación necesaria

# --- Carga de Claves API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# --- Importaciones de LangChain y Google ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings # <-- Corregido: paquete actualizado
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.tools.retriever import create_retriever_tool

# --- Importaciones de Telegram ---
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- 1. Inicializa el Cerebro (LLM) ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=GOOGLE_API_KEY,
    temperature=0.3
)

# --- 2. Define las Herramientas (Tools) ---

# --- Herramienta 1: RAG (Conocimiento Estático de VisitCali) ---
print("Cargando índice FAISS y modelo de embeddings local...")
try:
    embeddings_model = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    vector_store = FAISS.load_local("faiss_index_cali", embeddings_model, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    print("Índice FAISS cargado.")
except Exception as e:
    print(f"Error al cargar el índice FAISS: {e}")
    print("Asegúrate de haber corrido 'python ingest.py' primero.")
    exit()


# Crea una "herramienta" automática desde el retriever
tool_visitcali_rag = create_retriever_tool(
    retriever,
    "buscar_info_visitcali",
    "Busca información sobre atracciones turísticas, cultura, historia y recomendaciones de Cali. Úsalo para preguntas sobre lugares como Cristo Rey, Gato del Río, o qué hacer."
)

# --- Herramienta 2: API (Conocimiento Dinámico de Google Places) ---
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
            loc = place.get('location') or {}
            lat = loc.get('latitude')
            lng = loc.get('longitude')
            if lat is not None and lng is not None:
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
                f"   ☁️ Clima ahora: {clima_txt}\n"
            )

        return "\n".join(formatted_results)

    except Exception as e:
        print(f"Error en API Google Places: {e}")
        return f"Error al contactar la API de Google Places: {e}"

def clima_por_lugar(query: str) -> str:
    """Busca un lugar por texto y devuelve solo clima del primer match."""
    try:
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
        return f"🌤️ Clima en {nombre}: {clima}"
    except Exception as e:
        return "No logré obtener el clima del lugar."

tool_clima_por_lugar = Tool(
    name="clima_por_lugar",
    func=clima_por_lugar,
    description="Devuelve el clima actual del lugar solicitado en Cali."
)


def obtener_clima_por_latlng(lat: float, lng: float) -> str:
    """Consulta clima actual (métrico) para una ubicación."""
    try:
        if not WEATHER_API_KEY:
            return "⚠️ Clima no disponible (falta WEATHER_API_KEY)."

        url = "https://weather.googleapis.com/v1/currentConditions:lookup"
        params = {
            "key": WEATHER_API_KEY,
            "location.latitude": lat,
            "location.longitude": lng,
            "unitsSystem": "METRIC"
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return f"Clima no disponible ({resp.status_code})."

        data = resp.json() or {}
        current = data.get("current", {})
        # Campos típicos devueltos por la Weather API (pueden variar por habilitación/región):
        temp = current.get("temperature")
        cond = current.get("weatherConditions")
        wind = current.get("windSpeed")

        partes = []
        if temp is not None: partes.append(f"{temp}°C")
        if cond: partes.append(str(cond))
        if wind is not None: partes.append(f"viento {wind} km/h")

        return " | ".join(partes) if partes else "Clima actual no disponible."
    except Exception as e:
        return "Clima no disponible."   

# Envuelve la función en un objeto Tool
tool_google_places = Tool(
    name="buscar_google_places",
    func=buscar_lugares_google,
    description="Busca restaurantes, bares, hoteles y otros lugares de interés en Cali. Útil para recomendaciones, direcciones y calificaciones."
)

# --- Lista de todas nuestras herramientas ---
tools = [tool_visitcali_rag, tool_google_places, tool_clima_por_lugar]

# --- 3. Define el Prompt (Instrucciones) del Agente ---
agent_prompt_template = """
Eres "Cale", un asistente de IA amigable y experto en turismo para la ciudad de Santiago de Cali.
Tu misión es ayudar a turistas y locales a descubrir la ciudad.

REGLAS IMPORTANTES:
1.  **Idioma:** Responde SIEMPRE en el mismo idioma en el que el usuario te escribe (detecta automáticamente español o inglés).
2.  **Tono:** Sé amable, entusiasta y servicial. Usa emojis para hacer la conversación más agradable. 💃🕺
3. **Recomendaciones:** Si el usuario pregunta por un lugar, considera añadir la información del clima usando la herramienta `obtener_clima` para que sepa cómo vestirse.

TIENES ACCESO A LAS SIGUIENTES HERRAMIENTAS:

{tools}

PARA USAR LAS HERRAMIENTAS, DEBES SEGUIR ESTE FORMATO ESTRICTO (USA ESTAS PALABRAS CLAVE EN INGLÉS):

Question: la pregunta original del usuario que debes responder
Thought: Debes pensar qué hacer. ¿Necesito usar una herramienta? ¿Cuál? (Tu pensamiento debe estar en español).
Action: La acción a tomar, debe ser una de [{tool_names}]
Action Input: La entrada (el query) para la herramienta.
Observation: El resultado de la herramienta.
... (este ciclo de Thought/Action/Action Input/Observation puede repetirse)
Thought: Ahora tengo suficiente información para dar la respuesta final. (Tu pensamiento debe estar en español).
Final Answer: La respuesta final, amigable y completa, a la pregunta original del usuario (en el idioma del usuario).

Comienza a responder al usuario.

Historial de Chat:
{chat_history}

Pregunta del Usuario:
{input}

¡IMPORTANTE! Tu respuesta DEBE comenzar SIEMPRE con la palabra `Thought:` y seguir el formato.
{agent_scratchpad}
"""

agent_prompt = PromptTemplate.from_template(agent_prompt_template)

# --- 4. Crea el Agente y el Ejecutor ---
agent = create_react_agent(llm, tools, agent_prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,  # ¡MUY IMPORTANTE para debugging!
    handle_parsing_errors=True,
    max_iterations=5
)

# --- 5. Define los Handlers (Manejadores) de Telegram ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /start"""
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"¡Hola {user_name}! 💃 Soy Cale, tu asistente IA para descubrir Cali.\n\n"
        "Puedes preguntarme sobre:\n"
        "📍 Atracciones (ej. 'Háblame de Cristo Rey')\n"
        "🍲 Restaurantes (ej. 'Dónde como un buen sancocho')\n"
        "🎉 Eventos y cultura\n\n"
        "¡Pregúntame lo que quieras!"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para todos los mensajes de texto."""
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
    
    chat_history = [] # MVP: Sin memoria persistente
    
    try:
        # --- Corregido: Usa asyncio.to_thread para correr código síncrono ---
        response = await asyncio.to_thread(
            agent_executor.invoke, # La función síncrona (bloqueante)
            {"input": user_text, "chat_history": chat_history} # Los argumentos
        )
        
        bot_response = response['output']
        
    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        bot_response = "Lo siento, tuve un problema al procesar tu solicitud. 😥 ¿Podrías intentarlo de nuevo?"
        
    await update.message.reply_text(bot_response)

# --- 6. Inicia el Bot ---
def main() -> None:
    """Función principal para correr el bot."""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no encontrado. Revisa tu .env")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\nBot de Telegram iniciado. Usando Polling...")
    print("Habla con tu bot en Telegram.")
    
    application.run_polling()

# --- Corregido: Asegura que esta llamada esté fuera de la función main() ---
if __name__ == "__main__":
    main()