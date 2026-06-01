"""
FastAPI Main Application

Central API for Email AI Classification & Response System.
Receives emails from UiPath robots via REST API, processes them, and returns results.
"""

import logging
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv

# Import custom modules
from classifier import EmailClassifier, EmailClassificationRequest
from responder import ResponseGenerator, ResponseGenerationRequest
from validator import SchemaValidator
from ollama_client import OLLAMAClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AI Email Classification & Auto-Response System",
    description="Intelligent email processing with local OLLAMA LLM",
    version="1.0.0"
)

# Initialize OLLAMA client
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
ollama_client = OLLAMAClient(base_url=ollama_base_url, model=ollama_model)

# Initialize classifier and responder
classifier = None
responder = None


# ─── Pydantic Models ───────────────────────────────────────────────

class ProcessEmailRequest(BaseModel):
    """Request model for email processing."""
    subject: str
    body: str
    sender: str
    received_date: Optional[str] = None
    generate_response: bool = True


class ProcessEmailResponse(BaseModel):
    """Response model for email processing."""
    classification: dict
    response: Optional[dict] = None
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    ollama_connected: bool
    model: str


# ─── Startup & Shutdown ───────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    global classifier, responder
    
    logger.info("Starting up Email AI Classification System...")
    
    try:
        # Test OLLAMA connection
        is_connected = await ollama_client.connect()
        
        if is_connected:
            # Test model
            is_working = await ollama_client.test_model()
            
            if is_working:
                # Initialize classifier and responder
                classifier = EmailClassifier(ollama_client)
                responder = ResponseGenerator(
                    ollama_client,
                    company_info={
                        "name": os.getenv("COMPANY_NAME", "Company"),
                        "support_email": os.getenv("SUPPORT_EMAIL", "support@company.com")
                    }
                )
                logger.info("✅ System initialized successfully")
            else:
                logger.error("❌ OLLAMA model test failed")
        else:
            logger.error("❌ OLLAMA connection failed")
    
    except Exception as e:
        logger.error(f"Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Email AI Classification System...")


# ─── Health Check ────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    is_connected = await ollama_client.connect()
    
    return HealthResponse(
        status="healthy" if is_connected else "unhealthy",
        ollama_connected=is_connected,
        model=ollama_client.model
    )


# ─── Classification Endpoint ─────────────────────────────────────

@app.post("/api/v1/classify", tags=["Classification"])
async def classify_email(request: ProcessEmailRequest):
    """
    Classify email intent and extract metadata.
    
    Args:
        request: Email processing request
        
    Returns:
        Classification result
    """
    try:
        if not classifier:
            raise HTTPException(status_code=503, detail="Classifier not initialized")
        
        logger.info(f"Classifying email: {request.subject[:50]}")
        
        # Validate request
        is_valid, error_msg = SchemaValidator.validate_email_request({
            "subject": request.subject,
            "body": request.body,
            "sender": request.sender
        })
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Classify email
        classification_request = EmailClassificationRequest(
            subject=request.subject,
            body=request.body,
            sender=request.sender,
            received_date=request.received_date
        )
        
        result = await classifier.classify(classification_request)
        
        response = SchemaValidator.create_api_response(
            status="success",
            message="Email classified successfully",
            data=result.dict()
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Response Generation Endpoint ──────────────────────────────────

@app.post("/api/v1/generate-response", tags=["Response Generation"])
async def generate_response(request: ProcessEmailRequest):
    """
    Generate response to email based on classification.
    
    Args:
        request: Email processing request
        
    Returns:
        Generated response
    """
    try:
        if not responder or not classifier:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        logger.info(f"Generating response for: {request.subject[:50]}")
        
        # First classify the email
        classification_request = EmailClassificationRequest(
            subject=request.subject,
            body=request.body,
            sender=request.sender,
            received_date=request.received_date
        )
        
        classification = await classifier.classify(classification_request)
        
        # Generate response
        response_request = ResponseGenerationRequest(
            email_subject=request.subject,
            email_body=request.body,
            sender=request.sender,
            classification_intent=classification.intent,
            classification_summary=classification.summary,
            include_action_items=classification.requires_response
        )
        
        generated_response = await responder.generate(response_request)
        
        response = SchemaValidator.create_api_response(
            status="success",
            message="Response generated successfully",
            data=generated_response.dict()
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Response generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── End-to-End Processing Endpoint ───────────────────────────────

@app.post("/api/v1/process-email", response_model=ProcessEmailResponse, tags=["Processing"])
async def process_email(
    request: ProcessEmailRequest,
    background_tasks: BackgroundTasks = None
):
    """
    End-to-end email processing: classify + generate response.
    This is the main endpoint for UiPath robot integration.
    
    Args:
        request: Email processing request
        background_tasks: Background task queue
        
    Returns:
        Complete processing result
    """
    try:
        if not classifier or not responder:
            raise HTTPException(status_code=503, detail="Services not initialized")
        
        logger.info(f"Processing email: {request.subject[:50]}")
        
        # Validate request
        is_valid, error_msg = SchemaValidator.validate_email_request({
            "subject": request.subject,
            "body": request.body,
            "sender": request.sender
        })
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Step 1: Classify email
        classification_request = EmailClassificationRequest(
            subject=request.subject,
            body=request.body,
            sender=request.sender,
            received_date=request.received_date
        )
        
        classification = await classifier.classify(classification_request)
        
        # Step 2: Generate response if needed
        response_data = None
        if request.generate_response and classification.requires_response:
            response_request = ResponseGenerationRequest(
                email_subject=request.subject,
                email_body=request.body,
                sender=request.sender,
                classification_intent=classification.intent,
                classification_summary=classification.summary,
                include_action_items=True
            )
            
            response_data = await responder.generate(response_request)
        
        result = ProcessEmailResponse(
            classification=classification.dict(),
            response=response_data.dict() if response_data else None,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"Email processing complete: {classification.intent}")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Batch Processing Endpoint ────────────────────────────────────

@app.post("/api/v1/batch-process", tags=["Processing"])
async def batch_process_emails(requests: List[ProcessEmailRequest]):
    """
    Process multiple emails in batch.
    
    Args:
        requests: List of email processing requests
        
    Returns:
        List of processing results
    """
    try:
        if not classifier:
            raise HTTPException(status_code=503, detail="Classifier not initialized")
        
        logger.info(f"Batch processing {len(requests)} emails")
        
        results = []
        for request in requests:
            try:
                # Classify each email
                classification_request = EmailClassificationRequest(
                    subject=request.subject,
                    body=request.body,
                    sender=request.sender,
                    received_date=request.received_date
                )
                
                classification = await classifier.classify(classification_request)
                results.append({
                    "subject": request.subject,
                    "status": "success",
                    "classification": classification.dict()
                })
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                results.append({
                    "subject": request.subject,
                    "status": "error",
                    "error": str(e)
                })
        
        response = SchemaValidator.create_api_response(
            status="success",
            message=f"Batch processing complete: {len(results)} emails",
            data={"results": results, "count": len(results)}
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── System Info Endpoint ──────────────────────────────────────────

@app.get("/api/v1/info", tags=["Info"])
async def system_info():
    """Get system and configuration information."""
    return SchemaValidator.create_api_response(
        status="success",
        message="System information retrieved",
        data={
            "service": "AI Email Classification & Auto-Response System",
            "version": "1.0.0",
            "ollama_model": ollama_client.model,
            "ollama_url": ollama_client.base_url,
            "company": os.getenv("COMPANY_NAME", "Unknown"),
            "debug": os.getenv("DEBUG", "false").lower() == "true"
        }
    )


# ─── Root Endpoint ────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint - API info."""
    return {
        "service": "AI Email Classification & Auto-Response System",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "classify": "POST /api/v1/classify",
            "generate_response": "POST /api/v1/generate-response",
            "process_email": "POST /api/v1/process-email",
            "batch_process": "POST /api/v1/batch-process"
        }
    }


# ─── Error Handlers ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=SchemaValidator.create_api_response(
            status="error",
            message="Internal server error",
            error=str(exc)
        )
    )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
