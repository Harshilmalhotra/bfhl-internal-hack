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

app = FastAPI(title="Document Intelligence API", version="6.0.0")
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
    timeout=45.0  # Increased timeout
)

# Thread pool
executor = ThreadPoolExecutor(max_workers=4)

# Cache
document_cache = {}
CACHE_TTL = 3600

# Models
class DocumentRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class DocumentResponse(BaseModel):
    answers: List[str]

# Auth
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return credentials.credentials

async def download_document(url: str) -> bytes:
    """Download document"""
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as http_client:
            response = await http_client.get(str(url))
            response.raise_for_status()
            return response.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {str(e)}")

def extract_text_comprehensive(pdf_content: bytes) -> str:
    """Extract ALL text from PDF using multiple methods"""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        all_pages = []
        
        for page_num, page in enumerate(doc):
            # Method 1: Get structured text
            page_dict = page.get_text("dict")
            page_lines = []
            
            # Extract all text blocks
            for block in page_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = " ".join(span["text"] for span in line["spans"])
                        if line_text.strip():
                            page_lines.append(line_text.strip())
            
            # Method 2: If no text found, try standard extraction
            if not page_lines:
                standard_text = page.get_text()
                if standard_text.strip():
                    page_lines = standard_text.split('\n')
            
            # Add page content
            if page_lines:
                page_content = f"\n===== PAGE {page_num + 1} =====\n"
                page_content += "\n".join(page_lines)
                all_pages.append(page_content)
        
        doc.close()
        
        if not all_pages:
            raise Exception("No text found in PDF")
        
        # Combine all pages
        full_text = "\n\n".join(all_pages)
        
        # Clean but preserve structure
        full_text = re.sub(r' +', ' ', full_text)  # Multiple spaces to single
        full_text = re.sub(r'\n{4,}', '\n\n\n', full_text)  # Limit newlines
        
        logger.info(f"Extracted {len(full_text)} characters from {len(all_pages)} pages")
        return full_text
        
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")

async def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Async wrapper"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, extract_text_comprehensive, pdf_content)

def create_smart_chunks(text: str, max_chunk_size: int = 30000) -> List[str]:
    """Create overlapping chunks that preserve context"""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    pages = text.split("===== PAGE")
    
    current_chunk = ""
    for page in pages:
        if not page.strip():
            continue
            
        page_text = "===== PAGE" + page if page else ""
        
        # If adding this page would exceed limit, save current chunk
        if current_chunk and len(current_chunk) + len(page_text) > max_chunk_size:
            chunks.append(current_chunk)
            # Start new chunk with overlap from last page
            current_chunk = page_text
        else:
            current_chunk += "\n" + page_text if current_chunk else page_text
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def answer_questions_smart(text: str, questions: List[str]) -> List[str]:
    """Process questions with smart chunking for long documents"""
    
    # Create chunks
    chunks = create_smart_chunks(text, max_chunk_size=30000)
    logger.info(f"Document split into {len(chunks)} chunks")
    
    # If document fits in one chunk, process normally
    if len(chunks) == 1:
        return await process_single_chunk(text, questions)
    
    # For multiple chunks, search each chunk
    all_answers = ["Information not found in the document"] * len(questions)
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}")
        chunk_answers = await process_single_chunk(chunk, questions)
        
        # Update answers if better ones found
        for j, answer in enumerate(chunk_answers):
            if answer != "Information not found in the document":
                all_answers[j] = answer
    
    return all_answers

async def process_single_chunk(text: str, questions: List[str]) -> List[str]:
    """Process questions for a single chunk"""
    
    questions_formatted = "\n".join([f"Question {i+1}: {q}" for i, q in enumerate(questions)])
    
    prompt = f"""You are analyzing an insurance policy document. Answer each question with SPECIFIC details from the document.

DOCUMENT TEXT:
{text}

QUESTIONS TO ANSWER:
{questions_formatted}

CRITICAL INSTRUCTIONS:
1. Search the ENTIRE document for each answer
2. Include EXACT numbers, percentages, time periods (e.g., "30 days", "36 months", "5%")
3. For waiting periods, look for terms like "waiting period", "after", "continuous coverage"
4. For coverage details, look for "covered", "benefit", "limit", "sub-limit"
5. Only say "Information not found in the document" if you've searched everywhere
6. Be very specific - include section references if mentioned

Format your response EXACTLY as:
Answer 1: [specific answer with numbers/details]
Answer 2: [specific answer with numbers/details]
... etc.

Remember: Extract EXACT information, not general statements."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an insurance policy expert. Extract precise information including all numbers, percentages, and time periods."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=3000
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        answers = []
        
        # Extract answers
        lines = response_text.split('\n')
        for line in lines:
            match = re.match(r'^Answer\s*(\d+):\s*(.+)', line.strip())
            if match:
                answers.append(match.group(2).strip())
        
        # Ensure we have all answers
        while len(answers) < len(questions):
            answers.append("Information not found in the document")
        
        return answers[:len(questions)]
        
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        return ["Error processing question"] * len(questions)

@app.get("/")
async def root():
    return {"message": "Document Intelligence API", "version": "6.0.0"}

@app.post("/api/v1/hackrx/run", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    """Process document with comprehensive extraction"""
    start_time = time.time()
    
    try:
        # Check cache
        doc_hash = hashlib.md5(str(request.documents).encode()).hexdigest()
        cache_key = f"{doc_hash}:{','.join(request.questions)}"
        
        if cache_key in document_cache:
            if time.time() - document_cache[cache_key]['time'] < CACHE_TTL:
                logger.info("Cache hit!")
                return DocumentResponse(answers=document_cache[cache_key]['answers'])
        
        # Download
        logger.info("Downloading document...")
        pdf_content = await download_document(str(request.documents))
        logger.info(f"Downloaded {len(pdf_content)} bytes")
        
        # Extract ALL text
        logger.info("Extracting text...")
        text = await extract_text_from_pdf(pdf_content)
        logger.info(f"Extracted {len(text)} characters")
        
        if len(text) < 100:
            raise HTTPException(status_code=400, detail="No text extracted")
        
        # Process questions with smart chunking
        logger.info("Processing questions...")
        answers = await answer_questions_smart(text, request.questions)
        
        # Cache results
        document_cache[cache_key] = {
            'answers': answers,
            'time': time.time()
        }
        
        # Clean cache
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
    return {"status": "healthy", "version": "6.0.0", "cache_size": len(document_cache)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)