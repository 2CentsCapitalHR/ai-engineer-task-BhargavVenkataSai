import streamlit as st
import os
import traceback
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import time

# --- INITIALIZATION ---
# Load core components AFTER environment is verified
from core.rag_setup import create_rag_pipeline
from core.agent import ADGMCorporateAgent

st.set_page_config(page_title="ADGM Corporate Agent", page_icon="🤖")

@st.cache_resource
def initialize_agent():
    """Initializes the agent and RAG pipeline, cached for performance."""
    print("Initializing the Corporate Agent for Streamlit...")
    load_dotenv()

    # --- API Key Configuration Change Here ---
    # We now check for OPENAI_API_KEY instead of GOOGLE_API_KEY
    if not all(os.getenv(key) for key in ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "OPENAI_API_KEY"]):
        st.error("CRITICAL ERROR: One or more required API keys are missing. Please configure them in your secrets.")
        st.stop()
    # --- End of Change ---

    cloudinary.config(
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key = os.getenv("CLOUDINARY_API_KEY"),
        api_secret = os.getenv("CLOUDINARY_API_SECRET"),
        secure = True
    )
    agent = ADGMCorporateAgent(create_rag_pipeline())
    print("Corporate Agent is ready.")
    return agent

agent = initialize_agent()

# --- STREAMLIT UI ---

st.title("🤖 ADGM-Compliant Corporate Agent")
st.markdown("Upload your `.docx` legal documents. The agent will check for missing items, flag issues, and insert comments.")

uploaded_files = st.file_uploader(
    "Upload .docx Files",
    type=["docx"],
    accept_multiple_files=True
)

if st.button("Analyze Documents", disabled=(not uploaded_files)):
    if uploaded_files:
        try:
            with st.spinner("Analyzing documents... This may take a few moments."):
                doc_urls = []
                original_filenames = []
                for uploaded_file in uploaded_files:
                    public_id = f"adgm_docs/{uploaded_file.name}"
                    upload_result = cloudinary.uploader.upload(
                        uploaded_file, 
                        resource_type="raw", 
                        public_id=public_id, 
                        overwrite=True
                    )
                    
                    secure_url = upload_result.get('secure_url')
                    if secure_url:
                        doc_urls.append(secure_url)
                        original_filenames.append(uploaded_file.name)
                    else:
                        st.error(f"Failed to upload {uploaded_file.name}. Please check Cloudinary credentials.")
                
                if doc_urls:
                    final_report, downloadable_file_path = agent.analyze_and_prepare_downloads(doc_urls, original_filenames)
                    
                    st.session_state['final_report'] = final_report
                    st.session_state['download_path'] = downloadable_file_path
                    st.session_state['original_name'] = os.path.basename(downloadable_file_path) if downloadable_file_path else None

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            traceback.print_exc()

# Display results if they exist in the session state
if 'final_report' in st.session_state:
    st.markdown("### 📝 Analysis Report")
    st.json(st.session_state['final_report'])

if 'download_path' in st.session_state and st.session_state['download_path']:
    st.markdown("### 📄 Download Reviewed Document")
    
    with open(st.session_state['download_path'], "rb") as fp:
        st.download_button(
            label="Download",
            data=fp,
            file_name=st.session_state['original_name'],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )