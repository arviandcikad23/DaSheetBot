import streamlit as st
import tempfile
import os
import time
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from exa_py import Exa

# ==========================================
# UI LAYOUT & CONFIGURATION
# ==========================================
st.set_page_config(page_title="DaSheet_BOT", page_icon="🤖", layout="wide")
st.title("DaSheet_BOT 🤖")
st.write("AI Assistant untuk menganalisis datasheet komponen elektronik dan membandingkan harga/alternatif dari Web.")

with st.sidebar:
    st.header("Konfigurasi API")
    google_api_key = st.text_input("Google API Key", type="password", help="Dapatkan di Google AI Studio")
    exa_api_key = st.text_input("Exa API Key", type="password", help="Dapatkan di Exa AI")
    
    st.markdown("---")
    st.header("Unggah Datasheet")
    uploaded_files = st.file_uploader("Unggah PDF Datasheet (Bisa lebih dari 1)", type="pdf", accept_multiple_files=True)
    process_btn = st.button("Proses Datasheet")

# API Keys Sanitization
# Menggunakan .strip() untuk mencegah error INVALID_ARGUMENT karena whitespace
os.environ["GOOGLE_API_KEY"] = google_api_key.strip() if google_api_key else ""
os.environ["EXA_API_KEY"] = exa_api_key.strip() if exa_api_key else ""

# ==========================================
# STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "retriever" not in st.session_state:
    st.session_state.retriever = None

# ==========================================
# WEB SEARCH TOOL (EXA AI)
# ==========================================
@tool
def web_search(query: str) -> str:
    """Useful for searching the web for live market prices, component alternatives, and technical articles."""
    if not os.environ.get("EXA_API_KEY"):
        return "Error: Exa API Key not provided. Please enter the API Key in the sidebar."
    try:
        exa = Exa(api_key=os.environ["EXA_API_KEY"])
        response = exa.search_and_contents(
            query,
            type="neural",
            use_autoprompt=True,
            num_results=3,
            text=True
        )
        results = []
        for res in response.results:
            results.append(f"Title: {res.title}\nURL: {res.url}\nContent: {res.text}\n")
        return "\n".join(results) if results else "No results found."
    except Exception as e:
        return f"Error during web search: {str(e)}"

# ==========================================
# RAG PIPELINE (PDF PROCESSING)
# ==========================================
if process_btn:
    if not os.environ.get("GOOGLE_API_KEY"):
        st.sidebar.error("Silakan masukkan Google API Key terlebih dahulu.")
    elif not uploaded_files:
        st.sidebar.warning("Silakan unggah minimal 1 file PDF datasheet.")
    else:
        with st.spinner("Memproses dokumen PDF..."):
            all_splits = []
            
            # Read uploaded PDFs using tempfile
            for uploaded_file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    loader = PyPDFLoader(tmp_file_path)
                    docs = loader.load()
                    
                    # Chunking
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    splits = text_splitter.split_documents(docs)
                    all_splits.extend(splits)
                except Exception as e:
                    st.sidebar.error(f"Gagal memproses file {uploaded_file.name}: {e}")
                finally:
                    os.remove(tmp_file_path)
            
            if all_splits:
                persist_dir = "./db_datasheet"
                
                # ChromaDB Locking Error Prevention
                if os.path.exists(persist_dir):
                    shutil.rmtree(persist_dir, ignore_errors=True)
                    time.sleep(1)
                
                # Embedding Fallback Mechanism
                try:
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
                    # Try to embed a dummy text to verify if the model works
                    embeddings.embed_query("test_connection")
                except Exception as e:
                    st.sidebar.warning("Fallback embeddings aktif: Menggunakan models/embedding-001")
                    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                
                # Storage to ChromaDB
                try:
                    vectorstore = Chroma.from_documents(
                        documents=all_splits, 
                        embedding=embeddings, 
                        persist_directory=persist_dir
                    )
                    # Initialize retriever in session state
                    st.session_state.retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
                    st.sidebar.success("✅ Datasheet berhasil diproses dan disimpan ke database!")
                except Exception as e:
                    st.sidebar.error(f"Gagal membuat Vector Database: {e}")

# ==========================================
# CHAT INTERFACE & LANGGRAPH AGENT
# ==========================================
# Render previous messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat Input
if prompt := st.chat_input("Tanyakan spesifikasi atau cari alternatif komponen di web..."):
    # Append user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Validation before invoking agent
    if not os.environ.get("GOOGLE_API_KEY"):
        st.error("Google API Key diperlukan untuk merespons percakapan.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("Berpikir dan mencari informasi..."):
                tools = [web_search]
                
                # Add Retriever tool if PDF has been processed
                if st.session_state.retriever:
                    datasheet_tool = create_retriever_tool(
                        st.session_state.retriever,
                        "datasheet_search",
                        "Search and return information from the uploaded datasheet PDFs. Useful for finding technical specifications, pinouts, electrical characteristics, and component features."
                    )
                    tools.append(datasheet_tool)
                
                # LLM Initialization
                # Memastikan tidak menggunakan "gemini-1.5-flash" biasa untuk menghindari error 404 v1beta routing
                llm = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash-latest",
                    temperature=0.2
                )
                
                # System Prompt
                system_prompt = """You are DaSheet_BOT, a Senior Electronics Engineering AI Assistant.
Your primary role is to help users analyze and compare electronic component datasheets.
- Prioritize using the 'datasheet_search' tool for finding technical specifications, electrical characteristics, and pinouts from the user's uploaded documents.
- Use the 'web_search' tool for finding live market prices, component availability, alternatives, and tutorials on the internet.
- Combine information from both tools if the user asks for comparisons between the uploaded datasheet and alternative components on the market.
- ALWAYS respond in Indonesian (Bahasa Indonesia) in a clear, professional, and helpful manner.
"""

                # Initialize LangGraph Agent
                try:
                    agent = create_react_agent(
                        llm, 
                        tools=tools,
                        state_modifier=system_prompt
                    )
                    
                    # Prepare message history
                    chat_history = []
                    for msg in st.session_state.messages:
                        if msg["role"] == "user":
                            chat_history.append(HumanMessage(content=msg["content"]))
                        elif msg["role"] == "assistant":
                            chat_history.append(AIMessage(content=msg["content"]))
                    
                    # Invoke Agent
                    response = agent.invoke({"messages": chat_history})
                    final_answer = response["messages"][-1].content
                    
                    # Display response
                    st.markdown(final_answer)
                    
                    # Save assistant response to state
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memproses agen: {e}")
