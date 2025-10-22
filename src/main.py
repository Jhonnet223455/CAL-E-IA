import os
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import tempfile
import whisper
from pydub import AudioSegment
import subprocess
import sys
'''
# Configurar ffmpeg para pydub
if sys.platform == "win32":
    # Buscar ffmpeg en ubicaciones comunes de Windows
    possible_ffmpeg_paths = [
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe")
    ]
    for path in possible_ffmpeg_paths:
        if os.path.exists(path):
            AudioSegment.converter = path
            AudioSegment.ffmpeg = path
            AudioSegment.ffprobe = path.replace("ffmpeg.exe", "ffprobe.exe")
            print(f"FFmpeg configurado en: {path}")
            break
'''
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

# --- Cargar modelo Whisper (una sola vez al inicio) ---
print("Cargando modelo Whisper para transcripción de voz...")
try:
    whisper_model = whisper.load_model("tiny")  # tiny es 10x más rápido que base
    print("Modelo Whisper cargado (tiny - optimizado para velocidad).")
except Exception as e:
    print(f"Error al cargar Whisper: {e}")
    whisper_model = None

# --- 1. Inicializa el Cerebro (LLM) ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    google_api_key=GOOGLE_API_KEY,
    temperature=0.5  # Aumentado de 0.3 a 0.5 para respuestas más rápidas y directas
)

# --- 2. Define las Herramientas (Tools) ---

# --- Herramienta 1: RAG (Conocimiento Estático de VisitCali) ---
print("Cargando índice FAISS y modelo de embeddings local...")
try:
    embeddings_model = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    vector_store = FAISS.load_local("data/faiss_index_cali", embeddings_model, allow_dangerous_deserialization=True)
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})  # Reducido de 3 a 2 documentos
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
    max_iterations=8,  # Reducido de 10 a 8 para evitar búsquedas excesivas
    max_execution_time=45  # Reducido de 120 a 45 segundos
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
    
    # Obtener historial del usuario (reducido a 5 mensajes para respuestas más rápidas)
    chat_history_str = get_chat_history(user_id, limit=5)
    
    # Reintentos en caso de sobrecarga del modelo
    max_retries = 3
    retry_count = 0
    
    # Variable para controlar el mensaje de "estoy trabajando"
    thinking_message = None
    thinking_task = None
    
    async def send_thinking_message():
        """Envía un mensaje después de 5 segundos si el agente aún está procesando"""
        await asyncio.sleep(5)  # Reducido de 8 a 5 segundos
        nonlocal thinking_message
        thinking_message = await update.message.reply_text(
            "🤔 Estoy buscando la mejor información para ti, dame un momento..."
        )
    
    while retry_count < max_retries:
        try:
            # Iniciar tarea para enviar mensaje de "estoy pensando"
            thinking_task = asyncio.create_task(send_thinking_message())
            
            # --- Corregido: Usa asyncio.to_thread para correr código síncrono ---
            response = await asyncio.to_thread(
                agent_executor.invoke, # La función síncrona (bloqueante)
                {"input": user_text, "chat_history": chat_history_str} # Los argumentos
            )
            
            # Cancelar el mensaje de "estoy pensando" si aún no se envió
            if not thinking_task.done():
                thinking_task.cancel()
            
            # Eliminar el mensaje de "estoy pensando" si se envió
            if thinking_message:
                try:
                    await thinking_message.delete()
                except:
                    pass  # Ignorar errores al eliminar
            
            bot_response = response['output']
            
            # Guardar el mensaje del usuario y la respuesta del bot
            save_message(user_id, user_text, "user")
            save_message(user_id, bot_response, "assistant")
            
            # Limpiar historial antiguo (mantener solo últimos 50 mensajes)
            clear_old_history(user_id, keep_last=50)
            
            break  # Éxito, salimos del loop
            
        except Exception as e:
            # Cancelar mensaje de "estoy pensando" en caso de error
            if thinking_task and not thinking_task.done():
                thinking_task.cancel()
            if thinking_message:
                try:
                    await thinking_message.delete()
                except:
                    pass
            
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
    
    await update.message.reply_text(bot_response_cleaned)


# --- 5.2 Handler de Mensajes de Voz ---
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja mensajes de voz del usuario, transcribe con Whisper y procesa con el agente."""
    if not whisper_model:
        await update.message.reply_text("⚠️ La función de voz no está disponible en este momento.")
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Descargar el archivo de voz
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
        
        voice_file = await update.message.voice.get_file()
        
        # Crear archivo temporal para OGG
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_audio:
            temp_path_ogg = temp_audio.name
        
        # Crear archivo temporal para WAV (formato que Whisper entiende mejor)
        temp_path_wav = temp_path_ogg.replace('.ogg', '.wav')
        
        # Descargar el audio
        await voice_file.download_to_drive(temp_path_ogg)
        print(f"Audio descargado en: {temp_path_ogg}")
        
        # Convertir OGG a WAV usando pydub (no requiere ffmpeg en PATH)
        try:
            audio = AudioSegment.from_file(temp_path_ogg, format="ogg")
            audio.export(temp_path_wav, format="wav")
            print(f"Audio convertido a WAV: {temp_path_wav}")
        except Exception as conv_error:
            print(f"Error convirtiendo audio: {conv_error}")
            # Intentar directamente con el OGG
            temp_path_wav = temp_path_ogg
        
        # Transcribir con Whisper
        print("Transcribiendo audio con Whisper...")
        result = whisper_model.transcribe(temp_path_wav, language="es", fp16=False)
        user_text = result["text"].strip()
        print(f"Texto transcrito: {user_text}")
        
        # Eliminar archivos temporales
        try:
            os.unlink(temp_path_ogg)
            if temp_path_wav != temp_path_ogg:
                os.unlink(temp_path_wav)
        except:
            pass
        
        if not user_text:
            await update.message.reply_text("⚠️ No pude entender el audio. Por favor, intenta de nuevo.")
            return
        
        # Mostrar el texto transcrito al usuario
        await update.message.reply_text(f"🎤 Escuché: *{user_text}*", parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error procesando voz: {e}")
        await update.message.reply_text("⚠️ Hubo un error procesando tu mensaje de voz. Por favor, intenta de nuevo.")
        return
    
    # --- Procesar el texto transcrito con el agente (reutilizar lógica de handle_message) ---
    max_retries = 3
    retry_count = 0
    bot_response = "Lo siento, hubo un error procesando tu solicitud."
    
    while retry_count < max_retries:
        thinking_message = None
        thinking_task = None
        
        try:
            await context.bot.send_chat_action(chat_id=chat_id, action=constants.ChatAction.TYPING)
            
            # Mostrar mensaje de "pensando" si tarda más de 5 segundos
            async def thinking_message_func():
                await asyncio.sleep(5)  # Reducido de 8 a 5 segundos
                return await context.bot.send_message(
                    chat_id=chat_id,
                    text="🤔 Estoy buscando la mejor información para ti..."
                )
            
            thinking_task = asyncio.create_task(thinking_message_func())
            
            # Obtener historial
            history = get_chat_history(user_id)
            
            # Invocar agente
            result = agent_executor.invoke(
                {
                    "input": user_text,
                    "chat_history": history
                }
            )
            bot_response = result.get("output", "Lo siento, no pude procesar tu solicitud.")
            
            # Guardar en historial
            save_message(user_id, "user", user_text)
            save_message(user_id, "assistant", bot_response)
            
            # Cancelar mensaje de "pensando"
            if thinking_task and not thinking_task.done():
                thinking_task.cancel()
            if thinking_message:
                try:
                    await thinking_message.delete()
                except:
                    pass
            
            break  # Éxito, salir del bucle
            
        except Exception as e:
            # Cancelar mensaje de "pensando"
            if thinking_task and not thinking_task.done():
                thinking_task.cancel()
            if thinking_message:
                try:
                    await thinking_message.delete()
                except:
                    pass
            
            error_msg = str(e)
            print(f"Error procesando mensaje de voz (intento {retry_count + 1}/{max_retries}): {error_msg}")
            
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
    
    # Limpiar markdown
    bot_response_cleaned = bot_response.replace('**', '')
    
    await update.message.reply_text(bot_response_cleaned)


# --- 6. Inicia el Bot ---
def main() -> None:
    """Función principal para correr el bot."""
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN no encontrado. Revisa tu .env")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("olvidar", forget))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))  # Handler de mensajes de voz

    print("\nBot de Telegram iniciado. Usando Polling...")
    print("Habla con tu bot en Telegram.")
    
    application.run_polling()

# --- Corregido: Asegura que esta llamada esté fuera de la función main() ---
if __name__ == "__main__":
    main()