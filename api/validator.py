"""
JSON Schema Validator Module

Enforces strict JSON output format and validates all API responses.
"""

import logging
import json
from typing import Dict, Any, Tuple
import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates JSON responses against strict schemas."""
    
    # Schema for email classification responses
    CLASSIFICATION_SCHEMA = {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["support", "sales", "billing", "feedback", "complaint", "inquiry", "spam"]
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1
            },
            "summary": {
                "type": "string",
                "minLength": 10,
                "maxLength": 500
            },
            "priority": {
                "type": "string",
                "enum": ["high", "medium", "low"]
            },
            "requires_response": {
                "type": "boolean"
            },
            "action_items": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["intent", "confidence", "summary", "priority", "requires_response"]
    }
    
    # Schema for API responses
    API_RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["success", "error"]
            },
            "message": {
                "type": "string"
            },
            "data": {
                "type": "object"
            },
            "error": {
                "type": "string"
            }
        },
        "required": ["status", "message"]
    }
    
    # Schema for email processing request
    EMAIL_REQUEST_SCHEMA = {
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500
            },
            "body": {
                "type": "string",
                "minLength": 1,
                "maxLength": 50000
            },
            "sender": {
                "type": "string",
                "format": "email"
            },
            "received_date": {
                "type": "string"
            }
        },
        "required": ["subject", "body", "sender"]
    }
    
    @staticmethod
    def validate_classification(data: Dict) -> Tuple[bool, str, Dict]:
        """
        Validate classification output.
        
        Args:
            data: Classification data to validate
            
        Returns:
            Tuple of (is_valid, error_message, cleaned_data)
        """
        try:
            validate(instance=data, schema=SchemaValidator.CLASSIFICATION_SCHEMA)
            logger.info("Classification validation passed")
            return True, "", data
        
        except ValidationError as e:
            logger.error(f"Classification validation failed: {e.message}")
            error_msg = f"Validation error: {e.message}"
            return False, error_msg, {}
        
        except Exception as e:
            logger.error(f"Classification validation error: {e}")
            return False, str(e), {}
    
    @staticmethod
    def validate_api_response(data: Dict) -> Tuple[bool, str]:
        """
        Validate API response format.
        
        Args:
            data: Response data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            validate(instance=data, schema=SchemaValidator.API_RESPONSE_SCHEMA)
            logger.info("API response validation passed")
            return True, ""
        
        except ValidationError as e:
            logger.error(f"API response validation failed: {e.message}")
            return False, f"Response validation error: {e.message}"
        
        except Exception as e:
            logger.error(f"API response validation error: {e}")
            return False, str(e)
    
    @staticmethod
    def validate_email_request(data: Dict) -> Tuple[bool, str]:
        """
        Validate incoming email request.
        
        Args:
            data: Email request data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            validate(instance=data, schema=SchemaValidator.EMAIL_REQUEST_SCHEMA)
            logger.info("Email request validation passed")
            return True, ""
        
        except ValidationError as e:
            logger.error(f"Email request validation failed: {e.message}")
            return False, f"Request validation error: {e.message}"
        
        except Exception as e:
            logger.error(f"Email request validation error: {e}")
            return False, str(e)
    
    @staticmethod
    def sanitize_json_response(raw_response: str) -> Tuple[bool, Dict]:
        """
        Extract and sanitize JSON from LLM response.
        LLMs may include text before/after JSON.
        
        Args:
            raw_response: Raw text response from LLM
            
        Returns:
            Tuple of (success, parsed_json_dict)
        """
        try:
            # Try direct JSON parse first
            return True, json.loads(raw_response)
        
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_pattern = r'\{[\s\S]*\}'
            match = re.search(json_pattern, raw_response)
            
            if match:
                try:
                    json_str = match.group(0)
                    return True, json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    return False, {}
            
            logger.error(f"No JSON found in response: {raw_response[:100]}")
            return False, {}
        
        except Exception as e:
            logger.error(f"JSON sanitization error: {e}")
            return False, {}
    
    @staticmethod
    def create_api_response(status: str, message: str, data: Dict = None, error: str = None) -> Dict:
        """
        Create properly formatted API response.
        
        Args:
            status: Response status (success/error)
            message: Status message
            data: Response data (optional)
            error: Error description (optional)
            
        Returns:
            Formatted API response dict
        """
        response = {
            "status": status,
            "message": message
        }
        
        if data:
            response["data"] = data
        
        if error:
            response["error"] = error
        
        # Validate response format
        is_valid, error_msg = SchemaValidator.validate_api_response(response)
        
        if not is_valid:
            logger.warning(f"API response validation failed: {error_msg}")
        
        return response
