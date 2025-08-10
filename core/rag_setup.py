import os
import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings 
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

ADGM_DATA_SOURCES = {
    "Resolution_Incorporate_LTD.docx": "https://assets.adgm.com/download/assets/adgm-ra-resolution-multiple-incorporate-shareholders-LTD-incorporation-v2.docx/186a12846c3911efa4e6c6223862cd87",
    "Checklist_Private_Company.pdf": "https://www.adgm.com/documents/registration-authority/registration-and-incorporation/checklist/private-company-limited-by-guarantee-non-financial-services-20231228.pdf",
    "Standard_Employment_Contract_2024.docx": "https://assets.adgm.com/download/assets/ADGM+Standard+Employment+Contract+Template++ER+2024+(Feb+2025).docx/ee14b252edbe11efa63b12b3a30e5e3a",
    "Guidance_And_Policy.html": "https://www.adgm.com/legal-framework/guidance-and-policy-statements",
    "Annual_Filings.html": "https://www.adgm.com/operating-in-adgm/obligations-of-adgm-registered-entities/annual-filings/annual-accounts",
}

SOURCE_DOCS_DIR = "data/adgm_sources"
VECTOR_STORE_PATH = "faiss_index"

def download_and_prepare_sources():
    if not os.path.exists(SOURCE_DOCS_DIR):
        os.makedirs(SOURCE_DOCS_DIR)
    for filename, url in ADGM_DATA_SOURCES.items():
        output_path = os.path.join(SOURCE_DOCS_DIR, filename)
        if not os.path.exists(output_path):
            print(f"Downloading {filename}...")
            try:
                response = requests.get(url, stream=True, timeout=30)
                response.raise_for_status()
                if ".html" in filename:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text = soup.get_text(separator='\n', strip=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                else:
                    with open(output_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except requests.RequestException as e:
                print(f"Error downloading {url}: {e}")

def create_rag_pipeline():
    if os.path.exists(VECTOR_STORE_PATH):
        print("Loading existing vector store...")

        embeddings = OpenAIEmbeddings()

        return FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True).as_retriever()
    
    print("Building new vector store...")
    download_and_prepare_sources()
    all_docs = []
    
    loaders_config = {
        "**/*.docx": {"loader_cls": Docx2txtLoader},
        "**/*.pdf": {"loader_cls": PyPDFLoader},
        "**/*.html": {"loader_cls": TextLoader, "loader_kwargs": {"encoding": "utf-8"}}
    }
    
    for glob_pattern, config in loaders_config.items():
        try:
            loader = DirectoryLoader(
                SOURCE_DOCS_DIR, 
                glob=glob_pattern, 
                loader_cls=config["loader_cls"],
                loader_kwargs=config.get("loader_kwargs"),
                show_progress=True, 
                use_multithreading=True
            )
            docs = loader.load()
            all_docs.extend(docs)
            print(f"Loaded {len(docs)} document(s) for pattern {glob_pattern}.")
        except Exception as e:
            print(f"Could not load files for pattern {glob_pattern}. Error: {e}")

    if not all_docs:
        raise ValueError("No documents were loaded from the source directory.")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs = text_splitter.split_documents(all_docs)
    

    embeddings = OpenAIEmbeddings()

    vector_store = FAISS.from_documents(docs, embeddings)
    vector_store.save_local(VECTOR_STORE_PATH)
    print("Vector store created and saved.")
    return vector_store.as_retriever()