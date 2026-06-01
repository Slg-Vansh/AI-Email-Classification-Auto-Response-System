"""
Email Classifier Module

Handles email intent classification using OLLAMA local LLM.
"""

import logging
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmailClassificationRequest(BaseModel):
    """Request model for email classification."""
    subject: str
    body: str
    sender: str
    received_date: Optional[str] = None


class EmailClassificationResult(BaseModel):
    """Result model for email classification."""
    intent: str
    confidence: float
    summary: str
    priority: str  # high, medium, low
    requires_response: bool
    action_items: list = []
    error: Optional[str] = None


class EmailClassifier:
    """Classifies emails using OLLAMA LLM."""
    
    VALID_INTENTS = [
        "support",
        "sales",
        "billing",
        "feedback",
        "complaint",
        "inquiry",
        "spam"
    ]
    
    def __init__(self, ollama_client):
        """
        Initialize classifier with OLLAMA client.
        
        Args:
            ollama_client: OLLAMAClient instance
        """
        self.ollama_client = ollama_client
    
    async def classify(self, email: EmailClassificationRequest) -> EmailClassificationResult:
        """
        Classify email and extract metadata.
        
        Args:
            email: Email classification request
            
        Returns:
            Classification result with intent and details
        """
        try:
            logger.info(f"Classifying email: {email.subject[:50]}")
            
            # Call OLLAMA for classification
            email_dict = {
                "subject": email.subject,
                "body": email.body,
                "sender": email.sender
            }
            
            classification = await self.ollama_client.classify_email(email_dict)
            
            # Extract action items if needed
            action_items = []
            if classification.get("requires_response"):
                action_items = await self.ollama_client.extract_action_items(email.body)
            
            # Validate and normalize intent
            intent = classification.get("intent", "inquiry").lower()
            if intent not in self.VALID_INTENTS:
                intent = "inquiry"
            
            result = EmailClassificationResult(
                intent=intent,
                confidence=min(1.0, max(0.0, float(classification.get("confidence", 0.5)))),
                summary=classification.get("summary", ""),
                priority=classification.get("priority", "medium"),
                requires_response=classification.get("requires_response", False),
                action_items=action_items
            )
            
            logger.info(f"Classification complete: {result.intent} ({result.confidence:.2f})")
            return result
        
        except Exception as e:
            logger.error(f"Classification error: {e}")
            return EmailClassificationResult(
                intent="inquiry",
                confidence=0.0,
                summary="Classification failed",
                priority="medium",
                requires_response=False,
                error=str(e)
            )
    
    async def batch_classify(self, emails: list) -> list:
        """
        Classify multiple emails.
        
        Args:
            emails: List of email requests
            
        Returns:
            List of classification results
        """
        try:
            logger.info(f"Batch classifying {len(emails)} emails")
            
            results = []
            for email in emails:
                result = await self.classify(email)
                results.append(result)
            
            logger.info(f"Batch classification complete: {len(results)} emails")
            return results
        
        except Exception as e:
            logger.error(f"Batch classification error: {e}")
            return []
    
    @staticmethod
    def get_intent_description(intent: str) -> str:
        """Get human-readable description of intent."""
        descriptions = {
            "support": "Customer support or technical issue",
            "sales": "Sales inquiry or lead",
            "billing": "Billing or payment related",
            "feedback": "Feedback or suggestion",
            "complaint": "Complaint or issue report",
            "inquiry": "General inquiry",
            "spam": "Spam or unsolicited"
        }
        return descriptions.get(intent, "Unknown")
