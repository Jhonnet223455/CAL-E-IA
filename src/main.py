import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime

# --- Carga de Claves API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# --- Importaciones de LangChain y Google ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.agents import AgentExecutor, create_react_agent
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.tools.retriever import create_retriever_tool

# --- Importaciones de Telegram ---
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Importaciones de módulos propios ---
from database import init_database, save_message, get_chat_history, clear_old_history, delete_user_history
from weather_tools import tool_clima_por_lugar
from places_tools import tool_google_places
from prompts import AGENT_PROMPT_TEMPLATE

# --- Inicializa la base de datos al arrancar ---
init_database()

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
    vector_store = FAISS.load_local("data/faiss_index_cali", embeddings_model, allow_dangerous_deserialization=True)
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

# --- Lista de todas nuestras herramientas ---
tools = [tool_visitcali_rag, tool_google_places, tool_clima_por_lugar]

# --- 3. Define el Prompt (Instrucciones) del Agente ---
agent_prompt = PromptTemplate.from_template(AGENT_PROMPT_TEMPLATE)

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
        f"¡Hola {user_name}! 💃 Soy CAL-E, tu asistente IA para descubrir Cali.\n\n"
        "Puedes preguntarme sobre:\n"
        "📍 Atracciones (ej. 'Háblame de Cristo Rey')\n"
        "🍲 Restaurantes (ej. 'Dónde como un buen sancocho')\n"
        "🎉 Eventos y cultura\n\n"
        "💡 Tip: Recuerdo nuestras conversaciones anteriores para darte mejores recomendaciones.\n\n"
        "Comandos disponibles:\n"
        "/olvidar - Borra tu historial de conversación\n\n"
        "¡Pregúntame lo que quieras!"
    )

async def forget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para borrar el historial del usuario"""
    user_id = update.effective_user.id
    
    # Borrar todo el historial del usuario usando la función del módulo
    deleted_count = delete_user_history(user_id)
    
    if deleted_count > 0:
        await update.message.reply_text(
            "✅ He borrado todo tu historial de conversación.\n"
            "Empezaremos desde cero. ¡Pregúntame lo que quieras! 🌟"
        )
    else:
        await update.message.reply_text(
            "No hay historial que borrar. ¡Tu pizarra ya está limpia! ✨"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para todos los mensajes de texto."""
    user_text = update.message.text
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
    
    # Obtener historial del usuario
    chat_history_str = get_chat_history(user_id, limit=10)
    
    # Reintentos en caso de sobrecarga del modelo
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # --- Corregido: Usa asyncio.to_thread para correr código síncrono ---
            response = await asyncio.to_thread(
                agent_executor.invoke, # La función síncrona (bloqueante)
                {"input": user_text, "chat_history": chat_history_str} # Los argumentos
            )
            
            bot_response = response['output']
            
            # Guardar el mensaje del usuario y la respuesta del bot
            save_message(user_id, user_text, "user")
            save_message(user_id, bot_response, "assistant")
            
            # Limpiar historial antiguo (mantener solo últimos 50 mensajes)
            clear_old_history(user_id, keep_last=50)
            
            break  # Éxito, salimos del loop
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error procesando mensaje (intento {retry_count + 1}/{max_retries}): {error_msg}")
            
            # Si es error de sobrecarga (503) y aún hay reintentos, esperamos y reintentamos
            if "503" in error_msg or "overloaded" in error_msg.lower():
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Reintentando en 2 segundos...")
                    await asyncio.sleep(2)
                    await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
                    continue
            
            # Para cualquier otro error o si se agotaron los reintentos
            bot_response = "Lo siento, el servidor está muy ocupado en este momento. 😥 Por favor, intenta de nuevo en unos segundos."
            break
    
    # Limpiar markdown que Telegram no interpreta bien
    # Reemplazar **texto** por texto plano
    bot_response_cleaned = bot_response.replace('**', '')
    
    await update.message.reply_text(bot_response_cleaned)# --- 6. Inicia el Bot ---
def main() -> None:
    """Función principal para correr el bot."""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no encontrado. Revisa tu .env")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("olvidar", forget))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\nBot de Telegram iniciado. Usando Polling...")
    print("Habla con tu bot en Telegram.")
    
    application.run_polling()

# --- Corregido: Asegura que esta llamada esté fuera de la función main() ---
if __name__ == "__main__":
    main()