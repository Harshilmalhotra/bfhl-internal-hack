from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List
import httpx
import fitz  # PyMuPDF
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import time
import re
import hashlib

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Intelligence API", version="5.0.0")
security = HTTPBearer()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set!")

# Initialize AsyncOpenAI client
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://bfhldevapigw.healthrx.co.in/sp-gw/api/openai/v1/",
    timeout=30.0
)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

# Document cache
document_cache = {}
CACHE_TTL = 3600  # 1 hour

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

async def download_document(url: str) -> bytes:
    """Download document quickly"""
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as http_client:
            response = await http_client.get(str(url))
            response.raise_for_status()
            return response.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

def extract_text_from_pdf_fast(pdf_content: bytes) -> str:
    """Fast PDF text extraction"""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_parts = []
        
        for page in doc:
            # Use dict extraction for better structure
            page_dict = page.get_text("dict")
            page_text = []
            
            for block in page_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = " ".join(span["text"] for span in line["spans"])
                        if line_text.strip():
                            page_text.append(line_text)
            
            if page_text:
                text_parts.append("\n".join(page_text))
        
        doc.close()
        full_text = "\n\n".join(text_parts)
        
        # Basic cleaning
        full_text = re.sub(r'\s+', ' ', full_text)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        
        return full_text
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")

async def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Async PDF extraction"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, extract_text_from_pdf_fast, pdf_content)

async def process_questions_batch(text: str, questions: List[str]) -> List[str]:
    """Process all questions in a single API call"""
    
    # Format all questions
    questions_text = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(questions)])
    
    prompt = f"""Analyze this document and answer the questions. Be specific and include numbers, dates, percentages.

DOCUMENT:
{text[:15000]}  # Limit context for speed

QUESTIONS:
{questions_text}

For each question, provide a specific answer based ONLY on the document. If not found, say "Information not found in the document".

Format your response EXACTLY as:
A1: [answer to Q1]
A2: [answer to Q2]
... etc

Include specific details like amounts, percentages, time periods."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a document analyst. Provide precise, specific answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2500
        )
        
        # Parse answers
        response_text = response.choices[0].message.content
        answers = []
        
        for line in response_text.split('\n'):
            match = re.match(r'^A(\d+):\s*(.+)', line.strip())
            if match:
                answers.append(match.group(2).strip())
        
        # Fill missing answers
        while len(answers) < len(questions):
            answers.append("Information not found in the document")
        
        return answers[:len(questions)]
        
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return ["Error processing question"] * len(questions)

@app.get("/")
async def root():
    return {"message": "Document Intelligence API", "version": "5.0.0"}

@app.post("/api/v1/hackrx/run", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    """Fast document processing"""
    start_time = time.time()
    
    try:
        # Check cache
        doc_hash = hashlib.md5(str(request.documents).encode()).hexdigest()
        cache_key = f"{doc_hash}:{','.join(request.questions)}"
        
        if cache_key in document_cache:
            if time.time() - document_cache[cache_key]['time'] < CACHE_TTL:
                logger.info("Cache hit!")
                return DocumentResponse(answers=document_cache[cache_key]['answers'])
        
        # Download and extract in parallel
        download_task = download_document(str(request.documents))
        
        # Get PDF content
        pdf_content = await download_task
        logger.info(f"Downloaded {len(pdf_content)} bytes")
        
        # Extract text
        text = await extract_text_from_pdf(pdf_content)
        logger.info(f"Extracted {len(text)} characters")
        
        if len(text) < 100:
            raise HTTPException(status_code=400, detail="No text extracted")
        
        # Process all questions at once
        answers = await process_questions_batch(text, request.questions)
        
        # Cache results
        document_cache[cache_key] = {
            'answers': answers,
            'time': time.time()
        }
        
        # Clean old cache
        if len(document_cache) > 100:
            oldest = min(document_cache.keys(), key=lambda k: document_cache[k]['time'])
            del document_cache[oldest]
        
        logger.info(f"Total time: {time.time() - start_time:.2f}s")
        
        return DocumentResponse(answers=answers)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "5.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)