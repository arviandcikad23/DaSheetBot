import streamlit as st
import tempfile
import os
import time
import shutil

import requests
from langchain_core.embeddings import Embeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage

# ==========================================
# CUSTOM EMBEDDING CLASS
# Menggunakan google-genai SDK langsung (endpoint /v1, bukan /v1beta)
# Menghindari error 404 yang terjadi pada langchain-google-genai wrapper
# ==========================================
class DirectGoogleEmbeddings(Embeddings):
    """
    Memanggil Google Generative Language REST API v1 secara langsung.
    Menghindari semua masalah routing v1beta pada SDK LangChain dan google-genai.
    Endpoint: https://generativelanguage.googleapis.com/v1/models/{model}:embedContent
    """
    def __init__(self, model_name: str = "text-embedding-004", api_key: str = ""):
        self.model_name = model_name  # tanpa prefix 'models/'
        self.api_key = api_key
        self.url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{model_name}:embedContent?key={api_key}"
        )

    def _call_api(self, text: str) -> list:
        payload = {
            "model": f"models/{self.model_name}",
            "content": {"parts": [{"text": text}]}
        }
        resp = requests.post(self.url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["embedding"]["values"]

    def embed_documents(self, texts: list) -> list:
        return [self._call_api(t) for t in texts]

    def embed_query(self, text: str) -> list:
        return self._call_api(text)


# Fallback untuk create_retriever_tool jika tidak ditemukan di lokasi standar
try:
    from langchain.tools.retriever import create_retriever_tool
except (ImportError, ModuleNotFoundError):
    try:
        from langchain.tools import create_retriever_tool
    except (ImportError, ModuleNotFoundError):
        from langchain_core.tools import Tool
        def create_retriever_tool(retriever, name, description):
            def func(query: str) -> str:
                docs = retriever.invoke(query)
                return "\n\n".join([d.page_content for d in docs])
            return Tool(name=name, description=description, func=func)


# ==========================================
# UI LAYOUT & KONFIGURASI
# ==========================================
st.set_page_config(page_title="DaSheet_BOT", page_icon="🤖", layout="wide")
st.title("DaSheet_BOT 🤖")
st.write("AI Assistant untuk menganalisis dokumen menggunakan Google Gemini & RAG.")

with st.sidebar:
    st.header("⚙️ Konfigurasi API")
    google_api_key = st.text_input(
        "Google API Key",
        type="password",
        help="Dapatkan di Google AI Studio (aistudio.google.com)"
    )

    st.markdown("---")
    st.header("📄 Unggah Dokumen PDF")
    uploaded_files = st.file_uploader(
        "Unggah PDF (bisa lebih dari 1)",
        type="pdf",
        accept_multiple_files=True
    )
    process_btn = st.button("🔄 Proses Dokumen")


# Sanitasi API Key — mencegah INVALID_ARGUMENT karena spasi
os.environ["GOOGLE_API_KEY"] = google_api_key.strip() if google_api_key else ""


# ==========================================
# STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "retriever" not in st.session_state:
    st.session_state.retriever = None


# ==========================================
# RAG PIPELINE (PDF PROCESSING)
# ==========================================
if process_btn:
    if not os.environ.get("GOOGLE_API_KEY"):
        st.sidebar.error("❌ Silakan masukkan Google API Key terlebih dahulu.")
    elif not uploaded_files:
        st.sidebar.warning("⚠️ Silakan unggah minimal 1 file PDF.")
    else:
        with st.spinner("Memproses dokumen PDF..."):
            all_splits = []

            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                try:
                    loader = PyPDFLoader(tmp_file_path)
                    docs = loader.load()
                    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    splits = splitter.split_documents(docs)
                    all_splits.extend(splits)
                except Exception as e:
                    st.sidebar.error(f"Gagal memproses '{uploaded_file.name}': {e}")
                finally:
                    os.remove(tmp_file_path)

            if all_splits:
                persist_dir = "./db_datasheet"

                # Hapus database lama untuk mencegah ChromaDB lock error
                if os.path.exists(persist_dir):
                    shutil.rmtree(persist_dir, ignore_errors=True)
                    time.sleep(1)

                # Inisialisasi embedding menggunakan google-genai SDK
                api_key = os.environ["GOOGLE_API_KEY"]
                embeddings = None
                # Nama model TANPA prefix 'models/' karena sudah ditambahkan di dalam kelas
                for model_name in ["text-embedding-004", "gemini-embedding-exp-03-07"]:
                    try:
                        emb = DirectGoogleEmbeddings(model_name=model_name, api_key=api_key)
                        emb.embed_query("test")
                        embeddings = emb
                        st.sidebar.info(f"✅ Embedding aktif: `{model_name}`")
                        break
                    except Exception as emb_err:
                        st.sidebar.warning(f"Model `{model_name}` gagal: {emb_err}")
                        continue

                if embeddings is None:
                    st.sidebar.error(
                        "❌ Semua model embedding gagal.\n"
                        "Pastikan API Key valid dan memiliki akses ke Gemini API."
                    )
                    st.stop()

                # Simpan ke ChromaDB
                try:
                    vectorstore = Chroma.from_documents(
                        documents=all_splits,
                        embedding=embeddings,
                        persist_directory=persist_dir
                    )
                    st.session_state.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                    st.sidebar.success("✅ Dokumen berhasil diproses dan siap digunakan!")
                except Exception as e:
                    st.sidebar.error(f"Gagal membuat Vector Database: {e}")


# ==========================================
# CHAT INTERFACE & GEMINI AGENT
# ==========================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Tanyakan sesuatu tentang dokumen yang diunggah..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not os.environ.get("GOOGLE_API_KEY"):
        st.error("❌ Google API Key diperlukan untuk merespons percakapan.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Sedang berpikir..."):
                tools = []

                # Tambahkan Retriever Tool jika dokumen sudah diproses
                if st.session_state.retriever:
                    doc_tool = create_retriever_tool(
                        st.session_state.retriever,
                        "document_search",
                        "Cari informasi dari dokumen PDF yang sudah diunggah. "
                        "Gunakan ini untuk menjawab pertanyaan tentang isi dokumen."
                    )
                    tools.append(doc_tool)

                # Inisialisasi LLM Gemini
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash-latest",
                    temperature=0.2,
                    google_api_key=os.environ["GOOGLE_API_KEY"]
                )

                system_prompt = (
                    "Kamu adalah DaSheet_BOT, asisten AI yang membantu pengguna memahami isi dokumen.\n"
                    "- Gunakan tool 'document_search' untuk menjawab pertanyaan berdasarkan dokumen yang diunggah.\n"
                    "- Jika informasi tidak ada di dokumen, sampaikan dengan jujur bahwa kamu tidak menemukan informasinya.\n"
                    "- Selalu jawab dalam Bahasa Indonesia yang jelas dan profesional.\n"
                )

                try:
                    if tools:
                        agent = create_react_agent(
                            llm,
                            tools=tools,
                            state_modifier=system_prompt
                        )
                        chat_history = []
                        for m in st.session_state.messages:
                            if m["role"] == "user":
                                chat_history.append(HumanMessage(content=m["content"]))
                            elif m["role"] == "assistant":
                                chat_history.append(AIMessage(content=m["content"]))

                        response = agent.invoke({"messages": chat_history})
                        final_answer = response["messages"][-1].content
                    else:
                        # Tidak ada dokumen — langsung tanya ke Gemini tanpa tools
                        chat_history = []
                        for m in st.session_state.messages:
                            if m["role"] == "user":
                                chat_history.append(HumanMessage(content=m["content"]))
                            elif m["role"] == "assistant":
                                chat_history.append(AIMessage(content=m["content"]))

                        response = llm.invoke(
                            [HumanMessage(content=system_prompt + "\n\nPertanyaan: " + prompt)]
                        )
                        final_answer = response.content

                    st.markdown(final_answer)
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})

                except Exception as e:
                    st.error(f"Terjadi kesalahan: {e}")
