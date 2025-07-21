from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Tuple
import httpx
import fitz  # PyMuPDF for PDF processing
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
import time
import hashlib
import re
from collections import defaultdict

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Intelligence API", version="3.0.0")
security = HTTPBearer()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "1ece783ac40d4fc0fc4677d974f00124d9e686133426a1630d9c95dc75a1837c")

# Validate environment variables
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set. The API will not function properly without it.")

# Initialize AsyncOpenAI client
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://bfhldevapigw.healthrx.co.in/sp-gw/api/openai/v1/",
    timeout=30.0
)

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

# Cache for processed documents
document_cache = {}
CACHE_MAX_SIZE = 50
CACHE_TTL = 3600  # 1 hour

# Request/Response Models
class DocumentRequest(BaseModel):
    documents: HttpUrl
    questions: List[str]

class DocumentResponse(BaseModel):
    answers: List[str]

# Document type patterns
DOCUMENT_PATTERNS = {
    "insurance_policy": [
        r"policy\s*number", r"premium", r"coverage", r"insured", r"beneficiary",
        r"claim", r"deductible", r"exclusions", r"waiting period"
    ],
    "medical_report": [
        r"patient", r"diagnosis", r"treatment", r"medication", r"symptoms",
        r"medical history", r"examination", r"test results"
    ],
    "legal_contract": [
        r"agreement", r"party", r"whereas", r"terms and conditions", r"liability",
        r"jurisdiction", r"governing law", r"dispute resolution"
    ],
    "financial_statement": [
        r"balance sheet", r"income statement", r"cash flow", r"assets", r"liabilities",
        r"revenue", r"expenses", r"equity"
    ]
}

# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != AUTH_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    return credentials.credentials

def get_document_hash(url: str) -> str:
    """Generate hash for document URL for caching"""
    return hashlib.md5(url.encode()).hexdigest()

def detect_document_type(text: str) -> str:
    """Detect document type based on content patterns"""
    text_lower = text.lower()
    scores = defaultdict(int)
    
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                scores[doc_type] += 1
    
    if scores:
        return max(scores, key=scores.get)
    return "general"

async def download_document(url: str, max_retries: int = 3) -> bytes:
    """Download document from URL with retry logic"""
    timeout = httpx.Timeout(30.0, connect=10.0)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as http_client:
                logger.info(f"Downloading document (attempt {attempt + 1}/{max_retries})")
                response = await http_client.get(str(url))
                response.raise_for_status()
                logger.info(f"Document downloaded successfully ({len(response.content)} bytes)")
                return response.content
        except Exception as e:
            logger.error(f"Download attempt {attempt + 1} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise HTTPException(status_code=400, detail=f"Failed to download document: {str(e)}")
            await asyncio.sleep(1)

def extract_tables_from_page(page) -> List[Dict]:
    """Extract tables from a PDF page"""
    tables = []
    try:
        # Extract table data if present
        tabs = page.find_tables()
        for tab in tabs:
            table_data = []
            for row in tab.extract():
                table_data.append([cell if cell else "" for cell in row])
            if table_data:
                tables.append({"data": table_data})
    except:
        pass
    return tables

def extract_text_from_pdf_sync(pdf_content: bytes) -> Tuple[str, List[Dict]]:
    """Extract text and tables from PDF document"""
    try:
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_parts = []
        all_tables = []
        
        for page_num, page in enumerate(doc):
            # Extract text
            page_text = page.get_text("text")
            if page_text.strip():
                text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
            
            # Extract tables
            tables = extract_tables_from_page(page)
            for table in tables:
                all_tables.append({
                    "page": page_num + 1,
                    "data": table["data"]
                })
        
        doc.close()
        full_text = "\n\n".join(text_parts)
        
        # Add table information to text
        if all_tables:
            table_text = "\n\n[TABLES FOUND IN DOCUMENT]\n"
            for table in all_tables:
                table_text += f"\nTable on Page {table['page']}:\n"
                for row in table['data']:
                    table_text += " | ".join(str(cell) for cell in row) + "\n"
            full_text += table_text
        
        logger.info(f"Extracted {len(full_text)} characters and {len(all_tables)} tables from PDF")
        return full_text, all_tables
    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

async def extract_text_from_pdf(pdf_content: bytes) -> Tuple[str, List[Dict]]:
    """Extract text from PDF document asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, extract_text_from_pdf_sync, pdf_content)

def chunk_text(text: str, chunk_size: int = 6000, overlap: int = 500) -> List[str]:
    """Split text into overlapping chunks for better context"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to end at a sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            if last_period > chunk_size - 1000:
                end = start + last_period + 1
                chunk = text[start:end]
        
        chunks.append(chunk)
        start = end - overlap
    
    return chunks

async def answer_questions_with_context(text: str, questions: List[str], doc_type: str) -> List[str]:
    """Answer questions using document context and type-specific prompts"""
    
    # Type-specific instructions
    type_instructions = {
        "insurance_policy": "Focus on policy terms, coverage details, exclusions, waiting periods, claim procedures, and premium information.",
        "medical_report": "Focus on patient information, diagnoses, test results, medications, and treatment recommendations.",
        "legal_contract": "Focus on parties involved, obligations, terms, conditions, and legal provisions.",
        "financial_statement": "Focus on financial metrics, balances, transactions, and accounting details.",
        "general": "Extract relevant information based on the questions asked."
    }
    
    instruction = type_instructions.get(doc_type, type_instructions["general"])
    
    # Split text into chunks if too large
    chunks = chunk_text(text, chunk_size=6000)
    
    # For each question, search across all chunks
    answers = []
    
    for question in questions:
        # Create focused prompt for each question
        prompt = f"""You are analyzing a {doc_type.replace('_', ' ')} document. {instruction}

QUESTION: {question}

DOCUMENT EXCERPTS:
"""
        
        # Add relevant chunks (for now, all chunks, but could be optimized with semantic search)
        for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks for speed
            prompt += f"\n[Section {i+1}]\n{chunk}\n"
        
        prompt += """
INSTRUCTIONS:
1. Answer ONLY based on information explicitly stated in the document
2. Be specific and include relevant details (numbers, dates, terms)
3. If information is not found, state: "Information not found in the document"
4. For policies/contracts, quote specific sections when relevant
5. Keep the answer concise but complete

ANSWER:"""

        try:
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a {doc_type.replace('_', ' ')} document expert. Provide accurate, specific answers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            answers.append(answer)
            
        except Exception as e:
            logger.error(f"Question answering failed: {str(e)}")
            answers.append(f"Error processing question: {str(e)}")
    
    return answers

async def parallel_question_search(text: str, questions: List[str], doc_type: str) -> List[str]:
    """Process questions in parallel with intelligent batching"""
    
    # Group similar questions together
    question_groups = []
    current_group = []
    
    for q in questions:
        if len(current_group) < 3:  # Smaller batches for better accuracy
            current_group.append(q)
        else:
            question_groups.append(current_group)
            current_group = [q]
    
    if current_group:
        question_groups.append(current_group)
    
    # Process groups in parallel
    tasks = []
    for group in question_groups:
        task = answer_questions_with_context(text, group, doc_type)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    
    # Flatten results
    all_answers = []
    for group_answers in results:
        all_answers.extend(group_answers)
    
    return all_answers

# API Endpoints
@app.get("/")
async def root():
    return {
        "message": "Document Intelligence API",
        "version": "3.0.0",
        "features": ["parallel_processing", "document_type_detection", "table_extraction", "intelligent_chunking"]
    }

@app.post("/api/v1/hackrx/run", response_model=DocumentResponse)
async def process_document(request: DocumentRequest):
    """Process document with advanced optimization"""
    start_time = time.time()
    
    try:
        # Check cache first
        doc_hash = get_document_hash(str(request.documents))
        cache_key = f"{doc_hash}:{','.join(sorted(request.questions))}"
        
        if cache_key in document_cache:
            cache_entry = document_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < CACHE_TTL:
                logger.info(f"Cache hit! Returning cached results")
                return DocumentResponse(answers=cache_entry['answers'])
        
        # Download document
        download_start = time.time()
        pdf_content = await download_document(str(request.documents))
        logger.info(f"Download completed in {time.time() - download_start:.2f}s")
        
        # Extract text and tables
        extract_start = time.time()
        text, tables = await extract_text_from_pdf(pdf_content)
        logger.info(f"Text extraction completed in {time.time() - extract_start:.2f}s")
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")
        
        # Detect document type
        doc_type = detect_document_type(text)
        logger.info(f"Detected document type: {doc_type}")
        
        # Answer questions with parallel processing
        qa_start = time.time()
        answers = await parallel_question_search(text, request.questions, doc_type)
        logger.info(f"Question answering completed in {time.time() - qa_start:.2f}s")
        
        # Cache results
        document_cache[cache_key] = {
            'answers': answers,
            'timestamp': time.time()
        }
        
        # Clean old cache entries
        if len(document_cache) > CACHE_MAX_SIZE:
            oldest_key = min(document_cache.keys(), 
                           key=lambda k: document_cache[k]['timestamp'])
            del document_cache[oldest_key]
        
        total_time = time.time() - start_time
        logger.info(f"Total processing time: {total_time:.2f}s")
        
        return DocumentResponse(answers=answers)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "cache_size": len(document_cache),
        "features": [
            "parallel_processing",
            "document_type_detection", 
            "table_extraction",
            "intelligent_chunking",
            "response_caching"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")