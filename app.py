import gradio as gr
import os
import traceback
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

print("Initializing the Corporate Agent...")
load_dotenv()

if not all(os.getenv(key) for key in ["CLOUDINARY_CLOUD_NAME", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET", "OPENAI_API_KEY"]):
    raise ValueError("CRITICAL ERROR: One or more required API keys (Cloudinary or OpenAI) are missing from your .env file.")

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

from core.rag_setup import create_rag_pipeline
from core.agent import ADGMCorporateAgent
agent = ADGMCorporateAgent(create_rag_pipeline())
print("Corporate Agent is ready.")

def process_documents(files):
    """
    Main function to upload files to Cloudinary and trigger analysis.
    """
    if not files:
        gr.Info("Please upload at least one document.")
        return None, None

    try:
        doc_urls = []
        original_filenames = []
        for file_input in files:
            file_path = file_input.name
            current_filename = os.path.basename(file_path)
            print(f"Uploading {current_filename} to Cloudinary...")
            
            public_id = f"adgm_docs/{current_filename}"
            upload_result = cloudinary.uploader.upload(file_path, resource_type="raw", public_id=public_id, overwrite=True)
            
            secure_url = upload_result.get('secure_url')
            if secure_url:
                doc_urls.append(secure_url)
                original_filenames.append(current_filename)
            else:
                raise gr.Error(f"Failed to upload {current_filename}. Please check Cloudinary credentials.")
        
        if not doc_urls:
            raise gr.Error("File upload to Cloudinary failed for all files.")

        final_report, downloadable_file_path = agent.analyze_and_prepare_downloads(doc_urls, original_filenames)
        
        return final_report, downloadable_file_path

    except Exception as e:
        print(f"ERROR: An unhandled exception occurred.\n{traceback.format_exc()}")
        raise gr.Error(f"An unexpected error occurred: {e}")

# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft(), title="ADGM Corporate Agent") as demo:
    gr.Markdown("# 🤖 ADGM-Compliant Corporate Agent")
    gr.Markdown("Upload your `.docx` legal documents. The agent will check for missing items, flag issues, and insert comments.")
    with gr.Row():
        with gr.Column(scale=1):
            file_uploader = gr.File(label="Upload .docx Files", file_count="multiple", file_types=[".docx"])
            analyze_btn = gr.Button("Analyze Documents", variant="primary")
            
        with gr.Column(scale=2):
            gr.Markdown("### 📝 Analysis Report")
            json_output = gr.JSON(label="Summary")
            gr.Markdown("### 📄 Download Reviewed Document")
            file_output = gr.File(label="Download")

    analyze_btn.click(
        fn=process_documents,
        inputs=file_uploader,
        outputs=[json_output, file_output]
    )

if __name__ == "__main__":

    demo.launch()