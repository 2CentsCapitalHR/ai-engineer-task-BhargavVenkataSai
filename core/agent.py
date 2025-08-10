import os
import json
import requests
import tempfile
from docx import Document
from langchain_openai import ChatOpenAI # Changed from Google to OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from core.docx_handler import add_comment, save_document

# Checklists and Keywords are defined here and are complete
ADGM_CHECKLISTS = {
    "Company Incorporation": {
        "required_docs": 5, "docs": ["Articles of Association", "Memorandum of Association", "Board Resolution for Incorporation", "UBO Declaration Form", "Register of Members and Directors"]
    },
    "Financial Services Licensing": {
        "required_docs": 6, "docs": ["Application for FSP", "Business Plan", "Financial Projections", "Compliance Manual", "AML Policy", "Controllers and Authorised Individuals Forms"]
    },
    "Annual Filing": {"required_docs": 2, "docs": ["Annual Return", "Annual Accounts"]}
}
DOC_TYPE_KEYWORDS = {
    "Articles of Association": ["articles", "aoa"], "Memorandum of Association": ["memorandum", "moa", "mou"], "Board Resolution for Incorporation": ["resolution", "board"], "UBO Declaration Form": ["ubo", "beneficial owner"], "Register of Members and Directors": ["register", "members", "directors"],
    "Application for FSP": ["fsp", "permission", "license application", "licence"], "Business Plan": ["business plan", "b-plan"], "Financial Projections": ["financial", "projection", "forecast"], "Compliance Manual": ["compliance manual", "compliance policy"], "AML Policy": ["aml", "anti-money", "cft"], "Controllers and Authorised Individuals Forms": ["controller", "authorised individual", "authorized"],
    "Annual Return": ["annual return", "confirmation statement"], "Annual Accounts": ["annual accounts", "financial statements"],
}

class ADGMCorporateAgent:
    def __init__(self, retriever):
        self.retriever = retriever
        # --- MAJOR CHANGE HERE ---
        # Swapped ChatGoogleGenerativeAI with ChatOpenAI and specified a GPT model
        self.llm = ChatOpenAI(model_name="gpt-4o", temperature=0.2)
        # --- END OF MAJOR CHANGE ---
        self.prompt_template = self._create_prompt_template()
        self.llm_chain = LLMChain(prompt=self.prompt_template, llm=self.llm)

    def _create_prompt_template(self):
        template = """
        You are an expert ADGM legal assistant. Your task is to review a batch of legal document clauses based ONLY on the provided ADGM regulations context.

        **ADGM Regulations Context:**
        {context}

        **Document Clauses to Review:**
        {clauses_batch}

        **Task:**
        Review each clause in the batch for red flags such as incorrect jurisdiction, missing information, or non-compliant language according to the context.
        For each clause that has an issue, identify the problem and suggest a fix.

        **Output Format:**
        Respond ONLY with a single, valid JSON array of objects. Each object represents one issue you found.
        - If you find issues, use this format for each issue:
        {{"clause_number": <The number of the clause with the issue>, "issue": "A brief description of the problem.", "severity": "High/Medium/Low", "suggestion": "A concise suggestion to fix the issue."}}
        - If you find no issues at all in the entire batch, respond with an empty JSON array: []
        """
        return PromptTemplate(template=template, input_variables=["context", "clauses_batch"])

    def _identify_doc_type(self, filename):
        filename_lower = filename.lower()
        for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
            if any(keyword in filename_lower for keyword in keywords):
                return doc_type
        return "Unknown Document"

    def check_missing_documents(self, original_filenames):
        uploaded_doc_types = {self._identify_doc_type(name) for name in original_filenames}
        process = "Unknown"
        if any(doc in uploaded_doc_types for doc in {"Articles of Association", "Board Resolution for Incorporation"}):
            process = "Company Incorporation"
        elif any(doc in uploaded_doc_types for doc in ADGM_CHECKLISTS["Financial Services Licensing"]["docs"]):
            process = "Financial Services Licensing"
        elif any(doc in uploaded_doc_types for doc in ADGM_CHECKLISTS["Annual Filing"]["docs"]):
            process = "Annual Filing"
        
        if process in ADGM_CHECKLISTS:
            checklist = ADGM_CHECKLISTS[process]
            missing = list(set(checklist["docs"]) - uploaded_doc_types)
            return {"process": process, "documents_uploaded": len(original_filenames), "required_documents": checklist["required_docs"], "missing_documents": missing}
        return {"process": "Unknown", "missing_documents": []}

    def _analyze_single_document_from_url(self, docx_url, original_filename):
        # We need the time module to add a delay for free-tier APIs
        import time

        temp_path = None
        try:
            response = requests.get(docx_url, timeout=30)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_f:
                temp_f.write(response.content)
                temp_path = temp_f.name

            doc = Document(temp_path)
            issues_found = []

            paragraphs = [p for p in doc.paragraphs if len(p.text.strip()) > 20]
            

            batch_size = 2 

            for i in range(0, len(paragraphs), batch_size):
                batch = paragraphs[i:i+batch_size]
                
                clauses_for_prompt = []
                for j, para in enumerate(batch):
                    clauses_for_prompt.append(f"Clause {i+j+1}:\n\"\"\"\n{para.text}\n\"\"\"")
                
                clauses_batch_str = "\n\n".join(clauses_for_prompt)
                
                context_docs = self.retriever.get_relevant_documents(clauses_batch_str)
                context = "\n".join([d.page_content for d in context_docs])
                
                response = self.llm_chain.invoke({"context": context, "clauses_batch": clauses_batch_str})
                
                try:
                    results = json.loads(response['text'])
                    if not isinstance(results, list):
                        continue

                    for result in results:
                        clause_num = result.get('clause_number')
                        if clause_num and 1 <= clause_num <= len(paragraphs):
                            para_to_comment = paragraphs[clause_num - 1]
                            
                            comment_text = f"Issue: {result.get('issue', '')}\nSuggestion: {result.get('suggestion', '')}"
                            add_comment(para_to_comment, comment_text)
                            
                            issue_details = {
                                "document": original_filename,
                                "section": f"Paragraph starting with: '{para_to_comment.text[:50]}...'",
                                "issue": result.get('issue'),
                                "severity": result.get('severity', 'Medium'),
                                "suggestion": result.get('suggestion')
                            }
                            issues_found.append(issue_details)
                except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                    pass

                time.sleep(70) 

            return doc, issues_found
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def analyze_and_prepare_downloads(self, doc_urls, original_filenames):
        if not doc_urls:
            return {}, None
        
        final_report = self.check_missing_documents(original_filenames)
        final_report["issues_found"] = []
        
        reviewed_doc_paths_for_download = []
        
        for i, url in enumerate(doc_urls):
            original_name = original_filenames[i]
            modified_doc, issues = self._analyze_single_document_from_url(url, original_name)
            final_report["issues_found"].extend(issues)
            
            output_dir = tempfile.mkdtemp()
            output_path = os.path.join(output_dir, f"REVIEWED_{original_name}")
            save_document(modified_doc, output_path)
            reviewed_doc_paths_for_download.append(output_path)
            
        downloadable_file = reviewed_doc_paths_for_download[0] if reviewed_doc_paths_for_download else None
        
        return final_report, downloadable_file