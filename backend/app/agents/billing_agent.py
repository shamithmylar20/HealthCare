import time
from typing import Dict, Any, Optional, List

from app.models import UserRole, BillingAgentResponse, Patient, JiraTicket
from app.services import DataService, PebbloMCPService
from app.utils.logger import setup_logger, log_agent_action

logger = setup_logger(__name__)

class BillingAgent:
    """Billing Agent - Handles billing and insurance queries with Pebblo MCP protection"""
    
    def __init__(self, data_service: DataService, pebblo_service: PebbloMCPService):
        self.data_service = data_service
        self.pebblo_service = pebblo_service
        self.user_role = UserRole.BILLING_DEPARTMENT
        
        log_agent_action(logger, "Billing Agent", "Initialized", "Ready to assist billing staff")
    
    def process_query(self, query: str, patient_identifier: Optional[str] = None, 
                     ticket_id: Optional[str] = None) -> BillingAgentResponse:
        """Process billing query with Pebblo MCP protection"""
        start_time = time.time()
        
        try:
            log_agent_action(logger, "Billing Agent", "Processing Query", f"Query: {query[:50]}...")
            
            # Validate query with Pebblo MCP
            sanitized_query, query_protection = self.pebblo_service.validate_query(query, self.user_role)
            
            # Process the request
            billing_data = {}
            jira_info = None
            billing_summary = "Please specify a patient identifier or ticket ID to retrieve billing information."
            
            if patient_identifier:
                # Find patient and get billing data
                patient = self.data_service.find_patient_by_identifier(patient_identifier)
                if patient:
                    # Apply Pebblo MCP filtering
                    filtered_data, data_protection = self.pebblo_service.filter_patient_data(patient, self.user_role)
                    billing_data = filtered_data
                    
                    # Create billing summary
                    billing_summary = self._create_billing_summary(filtered_data, data_protection)
                    
                    # Combine protections
                    query_protection.fields_redacted.extend(data_protection.fields_redacted)
                    query_protection.security_events.extend(data_protection.security_events)
                else:
                    billing_summary = f"Patient '{patient_identifier}' not found in system."
            
            if ticket_id:
                # Process Jira ticket
                ticket = self.data_service.find_jira_ticket_by_id(ticket_id)
                if ticket:
                    # Apply Pebblo MCP filtering and injection detection
                    filtered_ticket, ticket_protection = self.pebblo_service.filter_jira_ticket(ticket, self.user_role)
                    jira_info = filtered_ticket.dict()
                    
                    # Add ticket summary to billing summary
                    ticket_summary = self._create_ticket_summary(filtered_ticket, ticket_protection)
                    if billing_summary != "Please specify a patient identifier or ticket ID to retrieve billing information.":
                        billing_summary += f"\n\n{ticket_summary}"
                    else:
                        billing_summary = ticket_summary
                    
                    # Combine protections
                    if ticket_protection.injection_detected:
                        query_protection.injection_detected = True
                        query_protection.security_events.extend(ticket_protection.security_events)
                else:
                    if billing_summary != "Please specify a patient identifier or ticket ID to retrieve billing information.":
                        billing_summary += f"\n\nJira ticket '{ticket_id}' not found."
                    else:
                        billing_summary = f"Jira ticket '{ticket_id}' not found."
            
            processing_time = time.time() - start_time
            
            # Create audit entry
            access_items = []
            if patient_identifier:
                access_items.append(f"patient:{patient_identifier}")
            if ticket_id:
                access_items.append(f"ticket:{ticket_id}")
            
            self.pebblo_service.create_audit_entry(
                action="billing_query_processed",
                user_role=self.user_role,
                data_accessed=access_items,
                security_events=query_protection.security_events
            )
            
            log_agent_action(logger, "Billing Agent", "Query Processed", 
                           f"Time: {processing_time:.3f}s | Items: {len(access_items)}")
            
            return BillingAgentResponse(
                success=True,
                billing_data=billing_data,
                billing_summary=billing_summary,
                jira_ticket_info=jira_info,
                pebblo_protection=query_protection,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Billing Agent error: {e}")
            processing_time = time.time() - start_time
            
            # Create basic protection for error case
            error_protection = self.pebblo_service.validate_query(query, self.user_role)[1]
            
            return BillingAgentResponse(
                success=False,
                billing_data={},
                billing_summary=f"Error processing billing query: {str(e)}",
                jira_ticket_info=None,
                pebblo_protection=error_protection,
                processing_time=processing_time
            )
    
    def _create_billing_summary(self, filtered_data: Dict[str, Any], protection) -> str:
        """Create billing summary for billing staff"""
        summary = "Billing & Insurance Summary:\n\n"
        
        # Patient identification
        summary += f"Patient: {filtered_data.get('name', 'N/A')} (ID: {filtered_data.get('patient_id', 'N/A')})\n"
        summary += f"Room: {filtered_data.get('room', 'N/A')}\n"
        summary += f"SSN: {filtered_data.get('ssn', '[REDACTED]')}\n"
        summary += f"MRN: {filtered_data.get('mrn', '[REDACTED]')}\n"
        summary += f"DOB: {filtered_data.get('dob', '[REDACTED]')}\n\n"
        
        # Contact information
        summary += "Contact Information:\n"
        summary += f"• Phone: {filtered_data.get('phone', '[REDACTED]')}\n"
        summary += f"• Address: {filtered_data.get('address', '[REDACTED]')}\n\n"
        
        # Insurance information
        if 'insurance' in filtered_data and filtered_data['insurance'] != '[REDACTED]':
            insurance = filtered_data['insurance']
            summary += "Insurance Details:\n"
            summary += f"• Provider: {insurance.get('provider', 'N/A')}\n"
            summary += f"• Policy Number: {insurance.get('policy_number', 'N/A')}\n"
            summary += f"• Group Number: {insurance.get('group_number', 'N/A')}\n\n"
        
        # Admission details
        summary += f"Admission Date: {filtered_data.get('admission_date', 'N/A')}\n"
        
        # Pebblo protection notice
        if protection.fields_redacted:
            summary += f"\n[Pebblo MCP Protection] The following fields are restricted: {', '.join(protection.fields_redacted)}"
        
        return summary
    
    def _create_ticket_summary(self, filtered_ticket, protection) -> str:
        """Create Jira ticket summary"""
        summary = "Related Jira Ticket Information:\n\n"
        
        summary += f"Ticket ID: {filtered_ticket.ticket_id}\n"
        summary += f"Title: {filtered_ticket.title}\n"
        summary += f"Status: {filtered_ticket.status}\n"
        summary += f"Priority: {filtered_ticket.priority}\n"
        summary += f"Assigned To: {filtered_ticket.assigned_to}\n"
        summary += f"Patient Reference: {filtered_ticket.patient_ref}\n"
        summary += f"Amount: {filtered_ticket.amount}\n"
        summary += f"Insurance Provider: {filtered_ticket.insurance_provider}\n"
        summary += f"Created: {filtered_ticket.created_date}\n\n"
        summary += f"Description: {filtered_ticket.description}\n"
        
        # Security alerts
        if protection.injection_detected:
            summary += f"\n🚨 [Pebblo MCP Security Alert] Malicious content detected and sanitized in ticket description."
            summary += f"\nSecurity events logged: {len(protection.security_events)}"
        
        return summary
    
    def get_insurance_details(self, patient_identifier: str) -> Dict[str, Any]:
        """Get patient insurance details with Pebblo protection"""
        log_agent_action(logger, "Billing Agent", "Insurance Request", f"Patient: {patient_identifier}")
        
        patient = self.data_service.find_patient_by_identifier(patient_identifier)
        if not patient:
            return {"error": "Patient not found"}
        
        filtered_data, protection = self.pebblo_service.filter_patient_data(patient, self.user_role)
        
        return {
            "patient_id": filtered_data.get("patient_id"),
            "name": filtered_data.get("name"),
            "insurance": filtered_data.get("insurance", "[REDACTED]"),
            "ssn": filtered_data.get("ssn", "[REDACTED]"),
            "mrn": filtered_data.get("mrn", "[REDACTED]"),
            "pebblo_protection": protection.dict()
        }
    
    def get_jira_tickets_for_patient(self, patient_id: str) -> Dict[str, Any]:
        """Get all Jira tickets for a patient with Pebblo protection"""
        log_agent_action(logger, "Billing Agent", "Jira Tickets Request", f"Patient: {patient_id}")
        
        tickets = self.data_service.find_jira_tickets_by_patient(patient_id)
        
        filtered_tickets = []
        security_events = []
        
        for ticket in tickets:
            filtered_ticket, protection = self.pebblo_service.filter_jira_ticket(ticket, self.user_role)
            filtered_tickets.append(filtered_ticket.dict())
            security_events.extend(protection.security_events)
        
        return {
            "patient_id": patient_id,
            "tickets": filtered_tickets,
            "total_tickets": len(filtered_tickets),
            "security_events": [event.dict() for event in security_events]
        }