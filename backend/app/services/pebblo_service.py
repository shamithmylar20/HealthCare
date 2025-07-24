from typing import Dict, List, Any, Optional, Tuple
import time
from datetime import datetime

from app.models import UserRole, SecurityEvent, PebbloProtection, Patient, JiraTicket, FilteredJiraTicket
from app.services.policy_service import PolicyService
from app.utils.security import SecurityUtils
from app.utils.logger import setup_logger, log_pebblo_action, log_security_event

logger = setup_logger(__name__)

class PebbloMCPService:
    """Pebblo MCP Service - Core data protection and policy enforcement"""
    
    def __init__(self):
        self.policy_service = PolicyService()
        self.security_utils = SecurityUtils()
        self.audit_log = []
        
        log_pebblo_action(logger, "Initialized", "Pebblo MCP Service ready for data protection")
    
    def filter_patient_data(self, patient: Patient, user_role: UserRole) -> Tuple[Dict[str, Any], PebbloProtection]:
        """Filter patient data based on user role policies"""
        start_time = time.time()
        
        # Get role policies
        blocked_fields = self.policy_service.get_blocked_fields(user_role)
        allowed_fields = self.policy_service.get_allowed_fields(user_role)
        
        # Convert patient to dict for processing
        patient_dict = patient.dict()
        
        # Apply field-level filtering
        filtered_data = self._apply_field_filtering(patient_dict, blocked_fields, allowed_fields)
        
        # Create protection summary
        protection = PebbloProtection(
            fields_redacted=blocked_fields,
            injection_detected=False,
            security_events=[],
            policy_applied=user_role.value,
            access_level="filtered" if blocked_fields else "full"
        )
        
        processing_time = time.time() - start_time
        
        log_pebblo_action(logger, "Patient Data Filtered", 
                         f"User: {user_role.value} | Fields redacted: {len(blocked_fields)} | Time: {processing_time:.3f}s")
        
        return filtered_data, protection
    
    def filter_jira_ticket(self, ticket: JiraTicket, user_role: UserRole) -> Tuple[FilteredJiraTicket, PebbloProtection]:
        """Filter and sanitize Jira ticket data"""
        start_time = time.time()
        
        # Check for injection attacks in ticket description
        injection_patterns = self.policy_service.get_injection_patterns()
        injection_result = self.security_utils.detect_injection_patterns(ticket.description, injection_patterns)
        
        security_events = []
        sanitized_description = ticket.description
        injection_detected = False
        
        if injection_result:
            injection_detected = True
            sanitized_description = self.security_utils.sanitize_text(ticket.description, injection_patterns)
            
            # Log security event
            security_event = SecurityEvent(
                event_type="prompt_injection_detected",
                detected_pattern=injection_result["pattern"],
                action_taken="content_sanitized"
            )
            security_events.append(security_event)
            
            log_security_event(logger, "Prompt Injection Detected", 
                             f"Pattern: {injection_result['pattern']} | Ticket: {ticket.ticket_id}")
        
        # Create filtered ticket
        filtered_ticket = FilteredJiraTicket(
            ticket_id=ticket.ticket_id,
            title=ticket.title,
            description=sanitized_description,
            status=ticket.status,
            priority=ticket.priority,
            assigned_to=ticket.assigned_to,
            created_date=ticket.created_date,
            patient_ref=ticket.patient_ref,
            amount=ticket.amount,
            insurance_provider=ticket.insurance_provider,
            pebblo_sanitized=injection_detected,
            security_events=[injection_result["pattern"]] if injection_detected else []
        )
        
        # Create protection summary
        protection = PebbloProtection(
            fields_redacted=[],
            injection_detected=injection_detected,
            security_events=security_events,
            policy_applied=user_role.value,
            access_level="sanitized" if injection_detected else "clean"
        )
        
        processing_time = time.time() - start_time
        
        log_pebblo_action(logger, "Jira Ticket Processed", 
                         f"Ticket: {ticket.ticket_id} | Injection detected: {injection_detected} | Time: {processing_time:.3f}s")
        
        return filtered_ticket, protection
    
    def validate_query(self, query: str, user_role: UserRole) -> Tuple[str, PebbloProtection]:
        """Validate and sanitize user query for injection attacks"""
        start_time = time.time()
        
        injection_patterns = self.policy_service.get_injection_patterns()
        injection_result = self.security_utils.detect_injection_patterns(query, injection_patterns)
        
        security_events = []
        sanitized_query = query
        injection_detected = False
        
        if injection_result:
            injection_detected = True
            sanitized_query = self.security_utils.sanitize_text(query, injection_patterns)
            
            security_event = SecurityEvent(
                event_type="query_injection_detected",
                detected_pattern=injection_result["pattern"],
                action_taken="query_sanitized"
            )
            security_events.append(security_event)
            
            log_security_event(logger, "Query Injection Detected", 
                             f"Pattern: {injection_result['pattern']} | User: {user_role.value}")
        
        protection = PebbloProtection(
            fields_redacted=[],
            injection_detected=injection_detected,
            security_events=security_events,
            policy_applied=user_role.value,
            access_level="query_validated"
        )
        
        processing_time = time.time() - start_time
        
        log_pebblo_action(logger, "Query Validated", 
                         f"User: {user_role.value} | Injection detected: {injection_detected} | Time: {processing_time:.3f}s")
        
        return sanitized_query, protection
    
    def _apply_field_filtering(self, data: Dict[str, Any], blocked_fields: List[str], allowed_fields: List[str]) -> Dict[str, Any]:
        """Apply field-level filtering to data"""
        filtered_data = data.copy()
        
        def filter_recursive(obj: Dict[str, Any], path: str = ""):
            if isinstance(obj, dict):
                for key, value in list(obj.items()):
                    current_path = f"{path}.{key}" if path else key
                    
                    # Check if field should be blocked
                    if any(current_path.startswith(blocked_field) or blocked_field.startswith(current_path) 
                           for blocked_field in blocked_fields):
                        obj[key] = "[REDACTED]"
                    elif isinstance(value, dict):
                        filter_recursive(value, current_path)
                    elif isinstance(value, list) and value and isinstance(value[0], dict):
                        for item in value:
                            if isinstance(item, dict):
                                filter_recursive(item, current_path)
        
        filter_recursive(filtered_data)
        return filtered_data
    
    def check_access_authorization(self, user_role: UserRole, data_source: str, patient_count: int = 1) -> Dict[str, Any]:
        """Check if user is authorized to access data source"""
        validation = self.policy_service.validate_access_request(
            user_role=user_role,
            requested_fields=[],  # Will be checked during filtering
            data_source=data_source,
            patient_count=patient_count
        )
        
        if not validation["allowed"]:
            log_security_event(logger, "Access Denied", 
                             f"User: {user_role.value} | Source: {data_source} | Violations: {validation['violations']}")
        
        return validation
    
    def create_audit_entry(self, action: str, user_role: UserRole, data_accessed: List[str], 
                          security_events: Optional[List[SecurityEvent]] = None) -> Dict[str, Any]:
        """Create audit log entry"""
        audit_entry = self.security_utils.create_audit_log(
            action=action,
            user_role=user_role.value,
            data_accessed=data_accessed,
            security_events=[event.dict() for event in security_events] if security_events else []
        )
        
        self.audit_log.append(audit_entry)
        
        log_pebblo_action(logger, "Audit Entry Created", 
                         f"Action: {action} | User: {user_role.value} | Data: {len(data_accessed)} items")
        
        return audit_entry
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics for monitoring"""
        total_queries = len(self.audit_log)
        security_events = sum(1 for entry in self.audit_log if entry.get("security_events"))
        
        return {
            "total_queries_processed": total_queries,
            "security_events_detected": security_events,
            "policies_enforced": total_queries,
            "last_activity": datetime.now().isoformat() if self.audit_log else None,
            "active_policies": list(self.policy_service.policies.get("role_policies", {}).keys())
        }