from docx import Document
import os

def add_comment(paragraph, comment_text, author="Corporate Agent"):
    """Adds a comment to a paragraph in a .docx file."""
    comment = paragraph.add_comment(comment_text, author=author)
    # Highlight the commented text
    for run in paragraph.runs:
        run.font.highlight_color = 7 # Corresponds to yellow
    return comment

def save_document(doc, output_path):
    """Saves the document object to the specified path."""
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    doc.save(output_path)