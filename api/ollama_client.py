"""
OLLAMA LLM Integration Module

Handles local OLLAMA model connections for classification and response generation.
All data stays local for privacy and security.
"""

import logging
import json
from typing import Dict, Optional, List
import httpx
import asyncio

logger = logging.getLogger(__name__)


class OLLAMAClient:
    """Client for OLLAMA local LLM model."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        """
        Initialize OLLAMA client.
        
        Args:
            base_url: OLLAMA server base URL
            model: Model name to use (llama3, mistral, neural-chat, etc.)
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = None
        self.timeout = 60
    
    async def connect(self) -> bool:
        """
        Test connection to OLLAMA server.
        
        Returns:
            bool: True if OLLAMA server is reachable, False otherwise
        """
        try:
            logger.info(f"Connecting to OLLAMA at {self.base_url}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name") for m in models]
                    logger.info(f"OLLAMA connected. Available models: {model_names}")
                    
                    # Check if requested model is available
                    if self.model not in model_names:
                        logger.warning(f"Model '{self.model}' not found. Available: {model_names}")
                        if model_names:
                            self.model = model_names[0]
                            logger.info(f"Using model: {self.model}")
                    
                    return True
                else:
                    logger.error(f"OLLAMA connection failed: HTTP {response.status_code}")
                    return False
        
        except Exception as e:
            logger.error(f"Failed to connect to OLLAMA: {e}")
            return False
    
    async def classify_email(self, email_content: Dict) -> Dict:
        """
        Classify email intent using OLLAMA.
        
        Args:
            email_content: Dict with subject, body, sender, etc.
            
        Returns:
            Dict with classification results
        """
        try:
            subject = email_content.get("subject", "")
            body = email_content.get("body", "")
            sender = email_content.get("sender", "")
            
            prompt = f"""Analyze this email and classify its intent.

From: {sender}
Subject: {subject}

Body:
{body}

Respond with JSON only:
{{
    "intent": "support|sales|billing|feedback|complaint|inquiry|spam",
    "confidence": 0.0-1.0,
    "summary": "brief summary of email intent",
    "priority": "high|medium|low",
    "requires_response": true|false
}}"""
            
            logger.info(f"Classifying email: {subject[:50]}")
            
            response = await self._call_ollama(prompt)
            
            # Parse JSON response
            try:
                result = json.loads(response)
                logger.info(f"Classification complete: {result.get('intent')}")
                return result
            except json.JSONDecodeError:
                logger.error(f"Failed to parse OLLAMA response: {response}")
                return {
                    "intent": "inquiry",
                    "confidence": 0.5,
                    "summary": "Classification failed",
                    "priority": "medium",
                    "requires_response": False,
                    "error": "JSON parse error"
                }
        
        except Exception as e:
            logger.error(f"Error classifying email: {e}")
            return {"error": str(e)}
    
    async def generate_response(self, email_content: Dict, classification: Dict) -> str:
        """
        Generate response to email using OLLAMA.
        
        Args:
            email_content: Original email content
            classification: Classification result with intent and summary
            
        Returns:
            Generated response text
        """
        try:
            subject = email_content.get("subject", "")
            body = email_content.get("body", "")
            intent = classification.get("intent", "inquiry")
            summary = classification.get("summary", "")
            
            prompt = f"""You are a professional customer service representative.
Generate a professional, helpful response to this email.

Email Subject: {subject}
Email Body: {body}

Email Intent: {intent}
Summary: {summary}

Requirements:
- Be professional and courteous
- Keep response concise (max 300 words)
- Address the main concern
- Provide clear action items if needed
- Sign off professionally

Generate only the response text, no JSON."""
            
            logger.info(f"Generating response for: {subject[:50]}")
            
            response = await self._call_ollama(prompt, temperature=0.7)
            
            logger.info("Response generation complete")
            return response
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "We appreciate your email and will get back to you shortly. Thank you!"
    
    async def extract_action_items(self, email_body: str) -> List[str]:
        """
        Extract action items from email body.
        
        Args:
            email_body: Email body text
            
        Returns:
            List of identified action items
        """
        try:
            prompt = f"""Extract action items from this email. Return as JSON array.

Email:
{email_body}

Respond with JSON only:
{{
    "action_items": ["item1", "item2", "item3"]
}}"""
            
            logger.info("Extracting action items")
            
            response = await self._call_ollama(prompt)
            result = json.loads(response)
            return result.get("action_items", [])
        
        except Exception as e:
            logger.error(f"Error extracting action items: {e}")
            return []
    
    async def _call_ollama(self, prompt: str, temperature: float = 0.5, max_tokens: int = 1000) -> str:
        """
        Make API call to OLLAMA.
        
        Args:
            prompt: Prompt text
            temperature: Randomness (0.0-1.0)
            max_tokens: Maximum response length
            
        Returns:
            Generated text response
        """
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "temperature": temperature,
                "num_predict": max_tokens
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    logger.error(f"OLLAMA API error: HTTP {response.status_code}")
                    return ""
        
        except Exception as e:
            logger.error(f"Error calling OLLAMA: {e}")
            return ""
    
    async def test_model(self) -> bool:
        """Test that model is working correctly."""
        try:
            logger.info(f"Testing OLLAMA model: {self.model}")
            
            test_prompt = "Say 'Model working correctly' in one sentence."
            response = await self._call_ollama(test_prompt)
            
            if response:
                logger.info(f"Model test successful: {response[:100]}")
                return True
            else:
                logger.error("Model test failed: empty response")
                return False
        
        except Exception as e:
            logger.error(f"Model test failed: {e}")
            return False
