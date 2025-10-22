import json
import os
from pathlib import Path
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings # <-- Corregido: paquete actualizado
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv

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

documents = []

# --- 2. Procesar archivo JSONL ---
FILE_PATH = "data/visitcali_scraping.jsonl"
print(f"\n📄 Leyendo el archivo {FILE_PATH}...")

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

    print(f"✅ Se procesaron {len(documents)} documentos del archivo JSONL.")

except FileNotFoundError:
    print(f"⚠️ No se encontró el archivo '{FILE_PATH}'.")
except json.JSONDecodeError as e:
    print(f"❌ Error al leer el JSON en una de las líneas. Revisa el archivo. Error: {e}")
except Exception as e:
    print(f"❌ Ocurrió un error inesperado al leer JSONL: {e}")

# --- 3. Procesar archivos PDF ---
DATA_DIR = Path("data")
pdf_files = list(DATA_DIR.glob("*.pdf"))

if pdf_files:
    print(f"\n📚 Encontrados {len(pdf_files)} archivos PDF. Procesando...")
    
    for pdf_path in pdf_files:
        try:
            print(f"   - Procesando: {pdf_path.name}")
            loader = PyPDFLoader(str(pdf_path))
            pdf_documents = loader.load()
            
            # Agregar información del archivo al contenido
            for doc in pdf_documents:
                # Agregar metadatos al contenido
                text_with_source = f"Fuente PDF: {pdf_path.name}\n{doc.page_content}"
                documents.append(text_with_source)
            
            print(f"     ✅ {len(pdf_documents)} páginas procesadas de {pdf_path.name}")
            
        except Exception as e:
            print(f"     ❌ Error al procesar {pdf_path.name}: {e}")
    
    print(f"✅ Total de documentos de PDFs: {len(pdf_documents) if pdf_files else 0}")
else:
    print(f"\nℹ️ No se encontraron archivos PDF en la carpeta 'data'.")

# --- 4. Verificar que hay documentos para procesar ---
if not documents:
    print("\n❌ ERROR: No se encontraron documentos válidos para crear el índice.")
    print("Asegúrate de tener el archivo JSONL o archivos PDF en la carpeta 'data'.")
    exit()

print(f"\n📊 Total de documentos a indexar: {len(documents)}")

# --- 5. Crea y guarda la Base de Datos Vectorial ---
try:
    print("\n🔄 Creando índice vectorial con FAISS (esto puede tardar unos segundos)...")
    
    # `from_texts` toma la lista de strings y crea los embeddings y el índice
    vector_store = FAISS.from_texts(documents, embeddings_model)
    
    # Guarda el índice localmente
    vector_store.save_local("data/faiss_index_cali")
    
    print("\n✅ ¡Éxito! Índice FAISS 'faiss_index_cali' creado y guardado.")
    print(f"   📁 Ubicación: data/faiss_index_cali")
    print(f"   📝 Documentos indexados: {len(documents)}")
    
except Exception as e:
    print(f"\n❌ Ocurrió un error al crear el índice: {e}")