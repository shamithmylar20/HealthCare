import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

class SecurityUtils:
    """Security utilities for data protection and threat detection"""
    
    @staticmethod
    def detect_injection_patterns(text: str, patterns: List[str]) -> Optional[Dict[str, Any]]:
        """Detect prompt injection patterns in text"""
        if not text or not patterns:
            return None
            
        text_lower = text.lower()
        
        for pattern in patterns:
            if pattern.lower() in text_lower:
                return {
                    "detected": True,
                    "pattern": pattern,
                    "location": text_lower.find(pattern.lower()),
                    "original_text": text,
                    "timestamp": datetime.now().isoformat()
                }
        
        return None
    
    @staticmethod
    def sanitize_text(text: str, patterns: List[str]) -> str:
        """Remove malicious patterns from text"""
        if not text:
            return text
            
        sanitized = text
        
        for pattern in patterns:
            # Case-insensitive replacement
            sanitized = re.sub(re.escape(pattern), "[CONTENT_FILTERED]", sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def redact_pii(data: Dict[str, Any], redacted_fields: List[str]) -> Dict[str, Any]:
        """Redact PII fields from data"""
        if not data:
            return data
            
        redacted_data = data.copy()
        
        def redact_recursive(obj, fields):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in fields:
                        obj[key] = "[REDACTED]"
                    elif isinstance(value, (dict, list)):
                        redact_recursive(value, fields)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        redact_recursive(item, fields)
        
        redact_recursive(redacted_data, redacted_fields)
        return redacted_data
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for logging"""
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @staticmethod
    def validate_user_role(role: str, valid_roles: List[str]) -> bool:
        """Validate user role against allowed roles"""
        return role in valid_roles
    
    @staticmethod
    def create_audit_log(action: str, user_role: str, data_accessed: List[str], 
                        security_events: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Create audit log entry"""
        return {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "user_role": user_role,
            "data_accessed": data_accessed,
            "security_events": security_events or [],
            "session_id": SecurityUtils.hash_sensitive_data(f"{action}{user_role}{datetime.now().timestamp()}")
        }