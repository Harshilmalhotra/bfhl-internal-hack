from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import httpx
import fitz  # PyMuPDF for PDF processing
from openai import OpenAI
import os
from dotenv import load_dotenv
import tempfile
import json

# Load environment variables
load_dotenv()

app = FastAPI(title="Document Intelligence API", version="1.0.0")
security = HTTPBearer()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c")

# Validate environment variables
if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not set. The API will not function properly without it.")

# Initialize OpenAI client with custom base URL
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://bfhldevapigw.healthrx.co.in/sp-gw/api/openai/v1/"
)

# Request/Response Models
class DocumentRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class DocumentResponse(BaseModel):
    answers: List[str]

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return credentials.credentials

# Document processing functions
async def download_document(url: str) -> bytes:
    """Download document from URL"""
    async with httpx.AsyncClient() as client:
        response = await client.get(str(url))
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download document")
        return response.content

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text from PDF document"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf_content)
        tmp_file_path = tmp_file.name
    
    try:
        doc = fitz.open(tmp_file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    finally:
        os.unlink(tmp_file_path)

def classify_document(text: str) -> dict:
    """Classify document and extract key information"""
    prompt = f"""Analyze the following document and provide:
1. Document type/classification
2. Key entities (names, dates, amounts, etc.)
3. Main topics covered
4. Important sections

Document text:
{text[:3000]}...

Provide the analysis in JSON format."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a document analysis expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"classification": "Unknown", "entities": [], "topics": [], "sections": []}

def clean_and_structure_text(text: str) -> str:
    """Remove unnecessary details and structure the text"""
    prompt = f"""Clean and structure the following document text by:
1. Removing boilerplate and redundant information
2. Organizing content into clear sections
3. Highlighting key information
4. Maintaining all important policy details, terms, and conditions

Document text:
{text}

Provide a clean, structured version of the document."""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a document structuring expert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

def answer_questions(text: str, questions: List[str]) -> List[str]:
    """Answer questions based on document content"""
    answers = []
    
    for question in questions:
        prompt = f"""Based on the following document, answer this question accurately and concisely:

Question: {question}

Document content:
{text}

Provide a specific answer based only on information found in the document. If the information is not available, state that clearly."""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a precise document Q&A assistant. Answer based only on the provided document content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        answers.append(response.choices[0].message.content)
    
    return answers

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Document Intelligence API", "version": "1.0.0"}

@app.post("/api/v1/hackrx/run", response_model=DocumentResponse)
async def process_document(
    request: DocumentRequest,
    token: str = Depends(verify_token)
):
    """Process document and answer questions"""
    try:
        # Download document
        pdf_content = await download_document(str(request.documents))
        
        # Extract text from PDF
        raw_text = extract_text_from_pdf(pdf_content)
        
        # Classify document
        classification = classify_document(raw_text)
        
        # Clean and structure text
        structured_text = clean_and_structure_text(raw_text)
        
        # Answer questions
        answers = answer_questions(structured_text, request.questions)
        
        return DocumentResponse(answers=answers)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)