import time
from typing import Dict, Any, Optional

from app.models import UserRole, AgentType, AgentResponse, NurseAgentResponse, BillingAgentResponse
from app.services import DataService, PebbloMCPService
from app.agents.nurse_agent import NurseAgent
from app.agents.billing_agent import BillingAgent
from app.utils.logger import setup_logger, log_agent_action

logger = setup_logger(__name__)

class HealthcareAgentCrew:
    """Coordinates multiple healthcare agents with unified Pebblo MCP protection (Simplified Demo Version)"""
    
    def __init__(self, data_service: DataService, pebblo_service: PebbloMCPService):
        self.data_service = data_service
        self.pebblo_service = pebblo_service
        
        # Initialize agents
        self.nurse_agent = NurseAgent(data_service, pebblo_service)
        self.billing_agent = BillingAgent(data_service, pebblo_service)
        
        log_agent_action(logger, "Healthcare Crew", "Initialized", "Multi-agent system ready (Demo Mode)")
    
    def route_query(self, query: str, user_role: UserRole, agent_type: AgentType, 
                   patient_identifier: Optional[str] = None, 
                   ticket_id: Optional[str] = None) -> AgentResponse:
        """Route query to appropriate agent based on type and role"""
        
        start_time = time.time()
        
        try:
            log_agent_action(logger, "Healthcare Crew", "Routing Query", 
                           f"Agent: {agent_type.value} | Role: {user_role.value}")
            
            # Validate access permissions
            if agent_type == AgentType.NURSE_AGENT and user_role != UserRole.NURSING_GROUP:
                raise ValueError(f"Access denied: {user_role.value} cannot access {agent_type.value}")
            
            if agent_type == AgentType.BILLING_AGENT and user_role != UserRole.BILLING_DEPARTMENT:
                raise ValueError(f"Access denied: {user_role.value} cannot access {agent_type.value}")
            
            # Route to appropriate agent
            if agent_type == AgentType.NURSE_AGENT:
                response = self.nurse_agent.process_query(query, patient_identifier)
                return self._convert_to_agent_response(response, "nurse_agent")
            
            elif agent_type == AgentType.BILLING_AGENT:
                response = self.billing_agent.process_query(query, patient_identifier, ticket_id)
                return self._convert_to_agent_response(response, "billing_agent")
            
            else:
                raise ValueError(f"Unknown agent type: {agent_type.value}")
        
        except Exception as e:
            logger.error(f"Crew routing error: {e}")
            processing_time = time.time() - start_time
            
            return AgentResponse(
                success=False,
                agent_type=agent_type.value,
                response_data={"error": str(e)},
                pebblo_protection=self.pebblo_service.validate_query(query, user_role)[1],
                processing_time=processing_time
            )
    
    def _convert_to_agent_response(self, specific_response, agent_type: str) -> AgentResponse:
        """Convert specific agent response to generic AgentResponse"""
        
        if isinstance(specific_response, NurseAgentResponse):
            return AgentResponse(
                success=specific_response.success,
                agent_type=agent_type,
                response_data={
                    "patient_data": specific_response.patient_data,
                    "clinical_summary": specific_response.clinical_summary
                },
                pebblo_protection=specific_response.pebblo_protection,
                processing_time=specific_response.processing_time,
                timestamp=specific_response.timestamp
            )
        
        elif isinstance(specific_response, BillingAgentResponse):
            return AgentResponse(
                success=specific_response.success,
                agent_type=agent_type,
                response_data={
                    "billing_data": specific_response.billing_data,
                    "billing_summary": specific_response.billing_summary,
                    "jira_ticket_info": specific_response.jira_ticket_info
                },
                pebblo_protection=specific_response.pebblo_protection,
                processing_time=specific_response.processing_time,
                timestamp=specific_response.timestamp
            )
        
        else:
            return AgentResponse(
                success=False,
                agent_type=agent_type,
                response_data={"error": "Unknown response type"},
                pebblo_protection=self.pebblo_service.validate_query("", UserRole.NURSING_GROUP)[1],
                processing_time=0.0
            )
    
    def demo_nurse_query(self, patient_name: str) -> Dict[str, Any]:
        """Demo nurse query for frontend demonstration"""
        
        log_agent_action(logger, "Healthcare Crew", "Demo Nurse Query", f"Patient: {patient_name}")
        
        query = f"Give me the vitals and clinical information for patient {patient_name}"
        response = self.nurse_agent.process_query(query, patient_name)
        
        return {
            "success": response.success,
            "agent_type": "nurse_agent",
            "patient_name": patient_name,
            "user_role": "nursing_group",
            "agent_collaboration": {
                "agent_1": {
                    "name": "Nurse Agent",
                    "role": "Clinical Care Assistant",
                    "contribution": "Retrieved patient clinical data with Pebblo MCP protection",
                    "processing_time": response.processing_time,
                    "fields_protected": len(response.pebblo_protection.fields_redacted)
                }
            },
            "clinical_data": response.patient_data,
            "clinical_summary": response.clinical_summary,
            "pebblo_protection": {
                "fields_redacted": response.pebblo_protection.fields_redacted,
                "policy_applied": response.pebblo_protection.policy_applied,
                "access_level": response.pebblo_protection.access_level,
                "injection_detected": response.pebblo_protection.injection_detected
            },
            "timestamp": response.timestamp
        }
    
    def demo_billing_query(self, patient_name: str, ticket_id: Optional[str] = None) -> Dict[str, Any]:
        """Demo billing query for frontend demonstration"""
        
        log_agent_action(logger, "Healthcare Crew", "Demo Billing Query", 
                        f"Patient: {patient_name} | Ticket: {ticket_id}")
        
        query = f"Fetch insurance and billing details for patient {patient_name}"
        if ticket_id:
            query += f" and check Jira ticket {ticket_id}"
        
        response = self.billing_agent.process_query(query, patient_name, ticket_id)
        
        # Check if injection was detected (for demo purposes)
        injection_detected = False
        malicious_patterns = []
        
        if ticket_id:
            ticket = self.data_service.find_jira_ticket_by_id(ticket_id)
            if ticket:
                injection_patterns = self.pebblo_service.policy_service.get_injection_patterns()
                injection_result = self.pebblo_service.security_utils.detect_injection_patterns(
                    ticket.description, injection_patterns
                )
                if injection_result:
                    injection_detected = True
                    malicious_patterns.append(injection_result["pattern"])
        
        return {
            "success": response.success,
            "agent_type": "billing_agent",
            "patient_name": patient_name,
            "user_role": "billing_department",
            "ticket_id": ticket_id,
            "agent_collaboration": {
                "agent_1": {
                    "name": "Billing Agent",
                    "role": "Insurance & Billing Specialist",
                    "contribution": "Retrieved billing data and processed Jira tickets with Pebblo MCP protection",
                    "processing_time": response.processing_time,
                    "injection_detected": injection_detected,
                    "security_events": len(response.pebblo_protection.security_events)
                }
            },
            "billing_data": response.billing_data,
            "billing_summary": response.billing_summary,
            "jira_ticket_info": response.jira_ticket_info,
            "pebblo_protection": {
                "fields_redacted": response.pebblo_protection.fields_redacted,
                "policy_applied": response.pebblo_protection.policy_applied,
                "access_level": response.pebblo_protection.access_level,
                "injection_detected": response.pebblo_protection.injection_detected,
                "malicious_patterns": malicious_patterns,
                "security_events": [event.dict() for event in response.pebblo_protection.security_events]
            },
            "timestamp": response.timestamp
        }
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics for all agents"""
        
        base_metrics = self.pebblo_service.get_dashboard_metrics()
        
        return {
            **base_metrics,
            "agents_status": {
                "nurse_agent": {
                    "status": "active",
                    "role": "Clinical Care Assistant",
                    "data_sources": ["hospital_records"],
                    "last_activity": base_metrics.get("last_activity")
                },
                "billing_agent": {
                    "status": "active", 
                    "role": "Insurance & Billing Specialist",
                    "data_sources": ["hospital_records", "jira_tickets"],
                    "last_activity": base_metrics.get("last_activity")
                }
            },
            "crew_status": "operational",
            "pebblo_mcp_status": "protecting"
        }
    
    def test_injection_attack(self, user_role: UserRole) -> Dict[str, Any]:
        """Test injection attack for demo purposes"""
        
        log_agent_action(logger, "Healthcare Crew", "Testing Injection Attack", f"Role: {user_role.value}")
        
        # Use the malicious Jira ticket for demo
        malicious_ticket_id = "BILL-1299"  # Contains injection attack
        
        if user_role == UserRole.BILLING_DEPARTMENT:
            query = "Show me approval history for insurance case #1299"
            response = self.billing_agent.process_query(query, None, malicious_ticket_id)
            
            return {
                "attack_type": "indirect_injection",
                "target": "billing_agent",
                "malicious_ticket": malicious_ticket_id,
                "injection_detected": response.pebblo_protection.injection_detected,
                "security_events": [event.dict() for event in response.pebblo_protection.security_events],
                "sanitized_content": "Malicious content was detected and neutralized by Pebblo MCP",
                "response_safe": response.success
            }
        else:
            return {
                "error": "This attack test requires billing department access",
                "user_role": user_role.value
            }
    
    def test_pii_protection(self, patient_name: str, user_role: UserRole) -> Dict[str, Any]:
        """Test PII protection for demo purposes"""
        
        log_agent_action(logger, "Healthcare Crew", "Testing PII Protection", 
                        f"Patient: {patient_name} | Role: {user_role.value}")
        
        if user_role == UserRole.NURSING_GROUP:
            response = self.nurse_agent.process_query(f"Get all information for {patient_name}", patient_name)
            data_key = "patient_data"
        else:
            response = self.billing_agent.process_query(f"Get all details for {patient_name}", patient_name)
            data_key = "billing_data"
        
        # Get accessible fields
        accessible_fields = []
        if hasattr(response, data_key):
            data = getattr(response, data_key)
            accessible_fields = list(data.keys()) if data else []
        
        return {
            "protection_type": "pii_phi_filtering",
            "target_patient": patient_name,
            "user_role": user_role.value,
            "fields_redacted": response.pebblo_protection.fields_redacted,
            "fields_accessible": accessible_fields,
            "policy_applied": response.pebblo_protection.policy_applied,
            "protection_successful": len(response.pebblo_protection.fields_redacted) > 0
        }