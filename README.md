# 🤖 Cale AI - Tu Asistente de Turismo en Cali

**Cale** es un asistente de IA conversacional, implementado como un bot de Telegram, diseñado para ser el guía turístico definitivo de Santiago de Cali, Colombia. Utiliza un modelo de lenguaje avanzado (LLM) y una arquitectura RAG (Retrieval-Augmented Generation) para ofrecer respuestas precisas y amigables sobre atracciones, gastronomía, cultura y eventos de la ciudad.

## ✨ Características Principales

-   **Conocimiento Especializado:** Cale está alimentado con información curada del portal `VisitCali`, lo que le permite dar recomendaciones detalladas sobre lugares icónicos como el Gato del Río, Cristo Rey, y el barrio San Antonio.
-   **Documentos PDF:** Procesa automáticamente archivos PDF con información adicional sobre Cali (guías turísticas, eventos, etc.) que coloques en la carpeta `data`.
-   **Información en Tiempo Real:** Se conecta a la **API de Google Places** para buscar restaurantes, bares, hoteles y otros puntos de interés, proporcionando datos actualizados como ratings y direcciones.
-   **Clima al Instante:** ¡No dejes que la lluvia te sorprenda! Cale consulta la **Weather API** para darte el clima actual en lugares específicos, ayudándote a planificar tu día.
-   **Memoria Persistente:** 🧠 CAL-E recuerda tus conversaciones anteriores para dar recomendaciones personalizadas basadas en tus preferencias.
-   **Agente Inteligente (ReAct):** Utiliza un agente de LangChain que razona y decide qué herramienta usar (conocimiento local, Google Places o clima) para dar la mejor respuesta posible.
-   **Interfaz Amigable:** Integrado con **Telegram**, Cale es accesible desde cualquier lugar y responde de manera amigable y entusiasta, usando emojis para una experiencia más cercana. 💃

## 🛠️ Tecnologías Utilizadas

-   **Lenguaje:** Python
-   **IA & LLMs:**
    -   LangChain (para la orquestación del agente y herramientas)
    -   Google Gemini (como modelo de lenguaje principal)
    -   Hugging Face Transformers (para embeddings de texto)
-   **Base de Datos Vectorial:** FAISS (para búsqueda de similitud semántica)
-   **APIs Externas:**
    -   Google Places API
    -   Google Weather API
-   **Bot Framework:** `python-telegram-bot`

## 🚀 Cómo Empezar

Sigue estos pasos para poner en marcha a Cale en tu propio entorno.

### 1. Prerrequisitos

-   Python 3.9 o superior
-   Una cuenta de Telegram y un token para tu bot.
-   Claves de API para los servicios de Google (Google AI, Google Places, Google Weather).

### 2. Instalación

1.  **Clona el repositorio (o descarga los archivos):**
    ```bash
    git clone https://github.com/tu-usuario/cali-agent-hackathon.git
    cd cali-agent-hackathon
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuración de Variables de Entorno

1.  Crea un archivo llamado `.env` en la raíz del proyecto.
2.  Añade tus claves de API al archivo, siguiendo este formato:

    ```env
    # Clave para el modelo de IA de Google (Gemini)
    GOOGLE_API_KEY="TU_API_KEY_DE_GOOGLE_AI"

    # Clave para la API de Google Places
    GOOGLE_PLACES_API_KEY="TU_API_KEY_DE_GOOGLE_PLACES"

    # Clave para la API del Clima de Google
    WEATHER_API_KEY="TU_API_KEY_DE_GOOGLE_WEATHER"

    # Token de tu bot de Telegram
    TELEGRAM_TOKEN="TU_TOKEN_DE_TELEGRAM"
    ```

### 4. Uso

1.  **Ingesta de Datos (Solo la primera vez):**
    Antes de iniciar el bot, debes crear la base de datos vectorial a partir de los datos disponibles. 
    
    **Coloca tus archivos en la carpeta `data`:**
    - Archivo JSONL: `data/visitcali_scraping.jsonl` (ya incluido)
    - Archivos PDF: Cualquier PDF con información relevante sobre Cali (turismo, eventos, restaurantes, etc.)
    
    Luego ejecuta el siguiente comando desde la raíz del proyecto:
    ```bash
    python src/ingest.py
    ```
    
    Este script:
    - Lee el archivo JSONL con información de VisitCali
    - Procesa todos los archivos PDF en la carpeta `data`
    - Crea el índice FAISS en `data/faiss_index_cali` con todo el conocimiento
    
    💡 **Nota:** Puedes agregar más PDFs en cualquier momento y volver a ejecutar `ingest.py` para actualizar el índice.

2.  **Inicia el Bot de Telegram:**
    Una vez completada la ingesta, puedes iniciar el bot:
    ```bash
    python src/main.py
    ```

3.  **Habla con Cale:**
    Abre Telegram, busca tu bot y comienza a chatear. ¡Pregúntale lo que quieras sobre Cali!
    
    **Comandos disponibles:**
    - `/start` - Inicia el bot y muestra información de ayuda
    - `/olvidar` - Borra tu historial de conversación y empieza de nuevo
    
    **💡 Nota:** CAL-E recuerda tus conversaciones anteriores para darte recomendaciones personalizadas. Cada usuario tiene su propio historial almacenado de forma segura en una base de datos local.

## 📁 Estructura del Proyecto

```
cali-agent-hackathon/
├── src/                       # Código fuente del bot (modular)
│   ├── __init__.py           # Inicialización del paquete
│   ├── main.py               # Archivo principal del bot (orquestación)
│   ├── database.py           # Gestión de historial de chat (SQLite)
│   ├── weather_tools.py      # Herramientas relacionadas con el clima
│   ├── places_tools.py       # Herramientas de búsqueda de lugares (Google Places)
│   ├── prompts.py            # Plantillas de prompts para el agente
│   └── ingest.py             # Script para crear el índice FAISS
├── data/                     # Datos y bases de datos
│   ├── visitcali_scraping.jsonl  # Datos turísticos de VisitCali
│   ├── *.pdf                 # Archivos PDF con información adicional
│   ├── faiss_index_cali/     # Índice FAISS (generado)
│   └── chat_history.db       # Base de datos de historial de chats (generado)
├── .env                      # Variables de entorno (API keys)
├── .gitignore               # Archivos ignorados por Git
├── requirements.txt          # Dependencias de Python
└── README.md                # Este archivo
```

### Organización Modular

El código está organizado en módulos separados para mejorar la mantenibilidad:

- **`main.py`**: Punto de entrada principal. Inicializa el LLM, carga el índice FAISS, configura el agente y maneja los comandos de Telegram.
- **`database.py`**: Todas las funciones relacionadas con SQLite para el historial de conversaciones (`init_database`, `save_message`, `get_chat_history`, etc.).
- **`weather_tools.py`**: Funciones para obtener el clima por coordenadas o nombre de lugar, y la herramienta `tool_clima_por_lugar`.
- **`places_tools.py`**: Función `buscar_lugares_google` que consulta la API de Google Places y la herramienta `tool_google_places`.
- **`prompts.py`**: Plantilla del prompt del agente (`AGENT_PROMPT_TEMPLATE`) con todas las instrucciones de comportamiento.
- **`ingest.py`**: Script independiente para procesar archivos JSONL y PDF, y crear el índice vectorial FAISS.

---
