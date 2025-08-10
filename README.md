# ADGM-Compliant Corporate Agent

This project is an AI-powered legal assistant for reviewing and validating documentation for business incorporation and compliance within the Abu Dhabi Global Market (ADGM).
![Dashboard Screenshot](assets/screenshots/dashboard.png)
![Dashboard Screenshot](assets/screenshots/dashboard.png)
![Dashboard Screenshot](assets/screenshots/dashboard.png)
## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-link>
    cd adgm_corporate_agent
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Up API Key:**
    - Get a Google API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Create a file named `.env` in the project's root directory.
    - Add your API key to the `.env` file like this:
      ```
      GOOGLE_API_KEY="YOUR_API_KEY_HERE"
      ```

## Running the Application

1.  **Start the Application:**
    Run the `app.py` script from your terminal:
    ```bash
    python app.py
    ```

2.  **First-Time Setup (RAG Data Processing):**
    The first time you run the app, it will download and process the ADGM source documents to build a local vector database. This may take a few minutes. Subsequent runs will be much faster as they will load the pre-built database.

3.  **Using the Agent:**
    - Open the URL provided in the terminal (usually `http://127.0.0.1:7860`).
    - Upload one or more `.docx` files related to an ADGM process (e.g., Company Incorporation).
    - Click "Analyze Documents".
    - The agent will return a JSON summary report and a link to download the reviewed `.docx` file with comments.
