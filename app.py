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

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Intelligence API", version="4.0.0")
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
    timeout=60.0  # Increased timeout
)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

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

async def download_document(url: str, max_retries: int = 3) -> bytes:
    """Download document with retry logic"""
    timeout = httpx.Timeout(60.0, connect=20.0)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as http_client:
                logger.info(f"Downloading PDF (attempt {attempt + 1}/{max_retries})")
                response = await http_client.get(str(url))
                response.raise_for_status()
                logger.info(f"PDF downloaded: {len(response.content)} bytes")
                return response.content
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=400, detail=f"Failed to download: {str(e)}")
            await asyncio.sleep(2)

def clean_text(text: str) -> str:
    """Clean and normalize text while preserving structure"""
    # Replace multiple spaces with single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Keep newlines but normalize them
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove null bytes and other control characters
    text = text.replace('\x00', '')
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    return text.strip()

def extract_text_from_pdf_comprehensive(pdf_content: bytes) -> str:
    """Extract text using multiple methods to ensure we get everything"""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        all_text = []
        
        for page_num, page in enumerate(doc):
            page_text = ""
            
            # Method 1: Dict extraction (preserves layout better)
            dict_text = page.get_text("dict")
            extracted_blocks = []
            
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        for span in line["spans"]:
                            line_text += span["text"]
                        if line_text.strip():
                            extracted_blocks.append(line_text)
            
            if extracted_blocks:
                page_text = "\n".join(extracted_blocks)
            
            # Method 2: Fallback to standard text if dict method fails
            if not page_text.strip():
                page_text = page.get_text("text")
            
            # Method 3: If still no text, try raw extraction
            if not page_text.strip():
                page_text = page.get_text("raw")
            
            # Method 4: Check if page might be an image (scanned PDF)
            if not page_text.strip():
                # Get page as image and check if it has content
                pix = page.get_pixmap()
                if pix.width > 100 and pix.height > 100:
                    logger.warning(f"Page {page_num + 1} appears to be an image. OCR might be needed.")
                    page_text = "[Image page - OCR required]"
            
            if page_text.strip():
                all_text.append(f"\n\n========== PAGE {page_num + 1} ==========\n{page_text}")
        
        doc.close()
        
        if not all_text:
            raise Exception("No text could be extracted from any page")
        
        # Combine all pages
        full_text = "\n".join(all_text)
        
        # Clean the text
        full_text = clean_text(full_text)
        
        logger.info(f"Extracted {len(full_text)} characters from {len(all_text)} pages")
        return full_text
        
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise Exception(f"Failed to extract text: {str(e)}")

async def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Async wrapper for PDF extraction"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, extract_text_from_pdf_comprehensive, pdf_content)

async def answer_questions_comprehensive(text: str, questions: List[str]) -> List[str]:
    """Answer questions with comprehensive context"""
    
    # If text is too long, we need to be smart about context
    MAX_CONTEXT_LENGTH = 12000  # Roughly 3000 tokens
    
    # For very long documents, create a summary first
    if len(text) > MAX_CONTEXT_LENGTH:
        # Use the full text but instruct the model to find specific sections
        prompt = f"""You are analyzing a long document. For each question, search through the ENTIRE document to find the relevant information.

QUESTIONS TO ANSWER:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions)])}

DOCUMENT CONTENT (SEARCH THROUGH ALL OF IT):
{text}

INSTRUCTIONS:
1. For each question, search the ENTIRE document for relevant information
2. Include ALL specific details: numbers, dates, percentages, amounts, periods
3. If information is not found after searching the entire document, say "Information not found in the document"
4. Quote exact phrases when answering about specific terms or conditions
5. For waiting periods, coverage limits, or exclusions, provide exact details

Format your response EXACTLY as:
Answer 1: [your detailed answer]
Answer 2: [your detailed answer]
... continue for all questions

BE VERY SPECIFIC. Include numbers, percentages, time periods, and amounts."""
    else:
        # For shorter documents, use the full text
        prompt = f"""You are analyzing a document. Answer each question with specific details from the document.

QUESTIONS:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(questions)])}

DOCUMENT:
{text}

INSTRUCTIONS:
1. Answer using ONLY information in the document
2. Include specific numbers, dates, percentages, amounts
3. If not found, say "Information not found in the document"
4. Be precise and complete

Format exactly as:
Answer 1: [detailed answer]
Answer 2: [detailed answer]
... etc."""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a precise document analyst. Find and extract specific information accurately."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=4000
        )
        
        # Parse response
        response_text = response.choices[0].message.content
        answers = []
        
        # Better parsing
        for line in response_text.split('\n'):
            match = re.match(r'^Answer\s*(\d+)\s*:\s*(.+)', line.strip())
            if match:
                answers.append(match.group(2).strip())
            elif answers and line.strip():
                # Continuation of previous answer
                answers[-1] += " " + line.strip()
        
        # Ensure correct number of answers
        while len(answers) < len(questions):
            answers.append("Information not found in the document")
        
        return answers[:len(questions)]
        
    except Exception as e:
        logger.error(f"Question answering failed: {str(e)}")
        return ["Error processing question: " + str(e)] * len(questions)

@app.get("/")
async def root():
    return {
        "message": "Document Intelligence API",
        "version": "4.0.0",
        "status": "simplified and optimized"
    }

@app.post("/api/v1/hackrx/run", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    """Process document with comprehensive extraction"""
    start_time = time.time()
    
    try:
        # Step 1: Download
        logger.info("Starting document download...")
        pdf_content = await download_document(str(request.documents))
        
        # Step 2: Extract ALL text
        logger.info("Extracting text from PDF...")
        text = await extract_text_from_pdf(pdf_content)
        
        if not text or len(text) < 100:
            raise HTTPException(status_code=400, detail="No meaningful text extracted from PDF")
        
        logger.info(f"Extracted {len(text)} characters")
        
        # Step 3: Answer questions
        logger.info("Processing questions...")
        answers = await answer_questions_comprehensive(text, request.questions)
        
        total_time = time.time() - start_time
        logger.info(f"Total processing time: {total_time:.2f}s")
        
        return DocumentResponse(answers=answers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "4.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")