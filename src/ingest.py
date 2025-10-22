import json
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings # <-- Corregido: paquete actualizado
from dotenv import load_dotenv
import os

load_dotenv()

# --- 1. Configura el modelo de Embeddings ---
print("Cargando modelo de embeddings local (esto puede tardar la primera vez)...")
try:
    embeddings_model = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2" # Modelo local, rápido y gratis
    )
    print("Modelo de embeddings cargado.")
except Exception as e:
    print(f"Error al cargar el modelo de embeddings. Asegúrate de tener 'pip install langchain-huggingface sentence-transformers'. Error: {e}")
    exit()


# --- 2. Define la ruta al archivo JSONL ---
FILE_PATH = "visitcali_scraping.jsonl" 

documents = []
print(f"Leyendo el archivo {FILE_PATH}...")

try:
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip(): # Evita líneas vacías
                data = json.loads(line)
                
                # --- 3. Crea el "documento" de texto ---
                # Combinamos título y descripción para un contexto más rico.
                title = data.get('title', '').replace(' - CALI ES DONDE DEBES ESTAR', '') # Limpiamos el título
                description = data.get('description', '')
                url = data.get('url', '')
                
                # Solo añadimos el documento si tiene una descripción útil
                if description and description.strip():
                    text_content = f"Título: {title}\nDescripción: {description}\nFuente: {url}"
                    documents.append(text_content)

    print(f"Se procesaron {len(documents)} documentos válidos del archivo JSONL.")

    if not documents:
        raise ValueError("No se encontraron documentos válidos (con descripción) en el archivo JSONL.")

    # --- 4. Crea y guarda la Base de Datos Vectorial ---
    print("Creando índice vectorial con FAISS (esto puede tardar unos segundos)...")
    
    # `from_texts` toma la lista de strings y crea los embeddings y el índice
    vector_store = FAISS.from_texts(documents, embeddings_model)
    
    # Guarda el índice localmente
    vector_store.save_local("faiss_index_cali")
    
    print("\n✅ ¡Éxito! Índice FAISS 'faiss_index_cali' creado y guardado con la nueva información.")

except FileNotFoundError:
    print(f"Error: No se encontró el archivo '{FILE_PATH}'.")
    print("Asegúrate de que el archivo 'visitcali_scraping.jsonl' esté en la misma carpeta que este script.")
except json.JSONDecodeError as e:
    print(f"Error al leer el JSON en una de las líneas. Revisa el archivo. Error: {e}")
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")