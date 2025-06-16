import PyPDF2
import pdfplumber
import re
from typing import Optional

def extract_text_from_pdf(pdf_file_path: str) -> str:
    """Extract text from PDF using multiple methods for best results"""
    
    # Method 1: Try pdfplumber (better for formatted text)
    try:
        text = extract_with_pdfplumber(pdf_file_path)
        if text and len(text.strip()) > 100:  # Reasonable amount of text
            return clean_extracted_text(text)
    except Exception as e:
        print(f"⚠️ pdfplumber failed: {e}")
    
    # Method 2: Fallback to PyPDF2
    try:
        text = extract_with_pypdf2(pdf_file_path)
        if text and len(text.strip()) > 100:
            return clean_extracted_text(text)
    except Exception as e:
        print(f"⚠️ PyPDF2 failed: {e}")
    
    raise ValueError("Could not extract readable text from PDF")

def extract_with_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber (better formatting preservation)"""
    text_content = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                    print(f"📄 Extracted page {page_num + 1}")
            except Exception as e:
                print(f"⚠️ Error extracting page {page_num + 1}: {e}")
                continue
    
    return "\n".join(text_content)

def extract_with_pypdf2(pdf_path: str) -> str:
    """Extract text using PyPDF2 (fallback method)"""
    text_content = []
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
                    print(f"📄 Extracted page {page_num + 1}")
            except Exception as e:
                print(f"⚠️ Error extracting page {page_num + 1}: {e}")
                continue
    
    return "\n".join(text_content)

def clean_extracted_text(text: str) -> str:
    """Clean and normalize extracted text"""
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    
    # Fix common PDF extraction issues
    text = re.sub(r'([a-z])([A-Z])', r'\1\n\2', text)  # Split concatenated lines
    text = re.sub(r'\s+', ' ', text)  # Normalize spaces
    text = re.sub(r'\n ', '\n', text)  # Remove leading spaces after newlines
    
    # Preserve script formatting patterns
    text = re.sub(r'(INT\.|EXT\.)', r'\n\1', text)  # Ensure scene headers on new lines
    text = re.sub(r'(FADE IN:|FADE OUT:|CUT TO:)', r'\n\1', text)  # Preserve transitions
    
    return text.strip()

def validate_script_content(text: str) -> bool:
    """Validate that extracted text looks like a script"""
    script_indicators = [
        r'(INT\.|EXT\.)',  # Scene headers
        r'FADE IN:',       # Script opening
        r'FADE OUT:',      # Script ending
        r'[A-Z]{2,}\s*\n',  # Character names
        r'\([^)]+\)',      # Parentheticals
    ]
    
    matches = sum(1 for pattern in script_indicators 
                 if re.search(pattern, text, re.IGNORECASE))
    
    return matches >= 2  # At least 2 script indicators found