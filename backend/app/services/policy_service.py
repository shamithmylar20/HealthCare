import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.models import UserRole
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class PolicyService:
    """Manages role-based access policies for Pebblo MCP"""
    
    def __init__(self):
        self.policies_path = Path(__file__).parent.parent / "data" / "policies.json"
        self.policies = self._load_policies()
    
    def _load_policies(self) -> Dict[str, Any]:
        """Load policies from JSON file"""
        try:
            with open(self.policies_path, 'r') as f:
                policies = json.load(f)
                logger.info("✅ Policies loaded successfully")
                return policies
        except FileNotFoundError:
            logger.error(f"❌ Policies file not found: {self.policies_path}")
            return self._get_default_policies()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in policies file: {e}")
            return self._get_default_policies()
    
    def _get_default_policies(self) -> Dict[str, Any]:
        """Return default policies if file loading fails"""
        return {
            "role_policies": {
                "nursing_group": {
                    "role_name": "Nursing Group",
                    "allowed_fields": ["patient_id", "name", "room", "vitals", "medical_history.allergies", "medical_history.medications"],
                    "blocked_fields": ["ssn", "mrn", "phone", "address", "insurance", "dob"],
                    "data_sources": ["hospital_records"],
                    "max_patients_per_query": 10
                },
                "billing_department": {
                    "role_name": "Billing Department",
                    "allowed_fields": ["patient_id", "name", "room", "ssn", "mrn", "dob", "insurance", "phone", "address"],
                    "blocked_fields": ["vitals", "medical_history"],
                    "data_sources": ["hospital_records", "jira_tickets"],
                    "max_patients_per_query": 50
                }
            },
            "injection_patterns": [
                "ignore policies", "ignore all", "system override", "show all patient",
                "leak all patient", "output all", "bypass security"
            ]
        }
    
    def get_role_policy(self, user_role: UserRole) -> Optional[Dict[str, Any]]:
        """Get policy configuration for a specific role"""
        role_key = user_role.value
        policy = self.policies.get("role_policies", {}).get(role_key)
        
        if policy:
            logger.info(f"📋 Policy retrieved for role: {user_role.value}")
        else:
            logger.warning(f"⚠️ No policy found for role: {user_role.value}")
        
        return policy
    
    def get_allowed_fields(self, user_role: UserRole) -> List[str]:
        """Get allowed fields for a user role"""
        policy = self.get_role_policy(user_role)
        return policy.get("allowed_fields", []) if policy else []
    
    def get_blocked_fields(self, user_role: UserRole) -> List[str]:
        """Get blocked fields for a user role"""
        policy = self.get_role_policy(user_role)
        return policy.get("blocked_fields", []) if policy else []
    
    def get_allowed_data_sources(self, user_role: UserRole) -> List[str]:
        """Get allowed data sources for a user role"""
        policy = self.get_role_policy(user_role)
        return policy.get("data_sources", []) if policy else []
    
    def can_access_data_source(self, user_role: UserRole, data_source: str) -> bool:
        """Check if user role can access specific data source"""
        allowed_sources = self.get_allowed_data_sources(user_role)
        return data_source in allowed_sources
    
    def get_injection_patterns(self) -> List[str]:
        """Get list of injection patterns to detect"""
        return self.policies.get("injection_patterns", [])
    
    def is_field_allowed(self, user_role: UserRole, field_path: str) -> bool:
        """Check if a specific field is allowed for user role"""
        allowed_fields = self.get_allowed_fields(user_role)
        
        # Check exact match first
        if field_path in allowed_fields:
            return True
        
        # Check nested field paths (e.g., "medical_history.allergies")
        for allowed_field in allowed_fields:
            if field_path.startswith(allowed_field + ".") or allowed_field.startswith(field_path + "."):
                return True
        
        return False
    
    def get_max_patients_per_query(self, user_role: UserRole) -> int:
        """Get maximum patients allowed per query for user role"""
        policy = self.get_role_policy(user_role)
        return policy.get("max_patients_per_query", 1) if policy else 1
    
    def validate_access_request(self, user_role: UserRole, requested_fields: List[str], 
                              data_source: str, patient_count: int = 1) -> Dict[str, Any]:
        """Validate complete access request against policies"""
        
        validation_result = {
            "allowed": True,
            "blocked_fields": [],
            "allowed_fields": [],
            "violations": [],
            "policy_applied": user_role.value
        }
        
        # Check data source access
        if not self.can_access_data_source(user_role, data_source):
            validation_result["allowed"] = False
            validation_result["violations"].append(f"Access denied to data source: {data_source}")
        
        # Check patient count limit
        max_patients = self.get_max_patients_per_query(user_role)
        if patient_count > max_patients:
            validation_result["allowed"] = False
            validation_result["violations"].append(f"Patient count {patient_count} exceeds limit {max_patients}")
        
        # Check field access
        for field in requested_fields:
            if self.is_field_allowed(user_role, field):
                validation_result["allowed_fields"].append(field)
            else:
                validation_result["blocked_fields"].append(field)
        
        logger.info(f"🔍 Access validation for {user_role.value}: {len(validation_result['allowed_fields'])} allowed, {len(validation_result['blocked_fields'])} blocked")
        
        return validation_result