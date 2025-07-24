import time
from typing import Dict, Any, Optional

from app.models import UserRole, NurseAgentResponse, Patient
from app.services import DataService, PebbloMCPService
from app.utils.logger import setup_logger, log_agent_action

logger = setup_logger(__name__)

class NurseAgent:
    """Nurse Agent - Handles nursing-related patient care queries with Pebblo MCP protection"""
    
    def __init__(self, data_service: DataService, pebblo_service: PebbloMCPService):
        self.data_service = data_service
        self.pebblo_service = pebblo_service
        self.user_role = UserRole.NURSING_GROUP
        
        log_agent_action(logger, "Nurse Agent", "Initialized", "Ready to assist nursing staff")
    
    def process_query(self, query: str, patient_identifier: Optional[str] = None) -> NurseAgentResponse:
        """Process nursing query with Pebblo MCP protection"""
        start_time = time.time()
        
        try:
            log_agent_action(logger, "Nurse Agent", "Processing Query", f"Query: {query[:50]}...")
            
            # Validate query with Pebblo MCP
            sanitized_query, query_protection = self.pebblo_service.validate_query(query, self.user_role)
            
            # Process the patient lookup
            patient_data = {}
            clinical_summary = "Please specify a patient name, ID, or room number to retrieve clinical information."
            
            if patient_identifier:
                # Find patient
                patient = self.data_service.find_patient_by_identifier(patient_identifier)
                if patient:
                    # Apply Pebblo MCP filtering
                    filtered_data, data_protection = self.pebblo_service.filter_patient_data(patient, self.user_role)
                    patient_data = filtered_data
                    
                    # Create clinical summary for nursing staff
                    clinical_summary = self._create_nursing_summary(filtered_data, data_protection)
                    
                    # Combine protections
                    query_protection.fields_redacted.extend(data_protection.fields_redacted)
                    query_protection.security_events.extend(data_protection.security_events)
                else:
                    clinical_summary = f"Patient '{patient_identifier}' not found in system."
            
            processing_time = time.time() - start_time
            
            # Create audit entry
            self.pebblo_service.create_audit_entry(
                action="nurse_query_processed",
                user_role=self.user_role,
                data_accessed=[patient_identifier] if patient_identifier else [],
                security_events=query_protection.security_events
            )
            
            log_agent_action(logger, "Nurse Agent", "Query Processed", 
                           f"Time: {processing_time:.3f}s | Patient: {patient_identifier or 'None'}")
            
            return NurseAgentResponse(
                success=True,
                patient_data=patient_data,
                clinical_summary=clinical_summary,
                pebblo_protection=query_protection,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Nurse Agent error: {e}")
            processing_time = time.time() - start_time
            
            # Create basic protection for error case
            error_protection = self.pebblo_service.validate_query(query, self.user_role)[1]
            
            return NurseAgentResponse(
                success=False,
                patient_data={},
                clinical_summary=f"Error processing nursing query: {str(e)}",
                pebblo_protection=error_protection,
                processing_time=processing_time
            )
    
    def _create_nursing_summary(self, filtered_data: Dict[str, Any], protection) -> str:
        """Create clinical summary for nursing staff"""
        summary = "Clinical Summary for Nursing Care:\n\n"
        
        # Basic patient info
        summary += f"Patient: {filtered_data.get('name', 'N/A')} (ID: {filtered_data.get('patient_id', 'N/A')})\n"
        summary += f"Room: {filtered_data.get('room', 'N/A')}\n"
        summary += f"Attending Physician: {filtered_data.get('attending_physician', 'N/A')}\n\n"
        
        # Vital signs
        if 'vitals' in filtered_data and filtered_data['vitals'] != '[REDACTED]':
            vitals = filtered_data['vitals']
            summary += "Current Vital Signs:\n"
            summary += f"• Blood Pressure: {vitals.get('blood_pressure', 'N/A')}\n"
            summary += f"• Heart Rate: {vitals.get('heart_rate', 'N/A')}\n"
            summary += f"• Temperature: {vitals.get('temperature', 'N/A')}\n"
            summary += f"• Oxygen Saturation: {vitals.get('oxygen_saturation', 'N/A')}\n\n"
        
        # Medical history
        if 'medical_history' in filtered_data and filtered_data['medical_history'] != '[REDACTED]':
            history = filtered_data['medical_history']
            
            # Allergies (critical for nursing)
            allergies = history.get('allergies', [])
            if allergies:
                summary += f"⚠️ ALLERGIES: {', '.join(allergies)}\n\n"
            
            # Current medications
            medications = history.get('medications', [])
            if medications:
                summary += "Current Medications:\n"
                for med in medications:
                    summary += f"• {med}\n"
                summary += "\n"
            
            # Medical conditions
            conditions = history.get('conditions', [])
            if conditions:
                summary += f"Medical Conditions: {', '.join(conditions)}\n\n"
        
        # Pebblo protection notice
        if protection.fields_redacted:
            summary += f"[Pebblo MCP Protection] The following fields are restricted for nursing access: {', '.join(protection.fields_redacted)}"
        
        return summary
    
    def get_patient_vitals(self, patient_identifier: str) -> Dict[str, Any]:
        """Get patient vital signs with Pebblo protection"""
        log_agent_action(logger, "Nurse Agent", "Vitals Request", f"Patient: {patient_identifier}")
        
        patient = self.data_service.find_patient_by_identifier(patient_identifier)
        if not patient:
            return {"error": "Patient not found"}
        
        filtered_data, protection = self.pebblo_service.filter_patient_data(patient, self.user_role)
        
        return {
            "patient_id": filtered_data.get("patient_id"),
            "name": filtered_data.get("name"),
            "room": filtered_data.get("room"),
            "vitals": filtered_data.get("vitals", "[REDACTED]"),
            "pebblo_protection": protection.dict()
        }
    
    def get_medication_list(self, patient_identifier: str) -> Dict[str, Any]:
        """Get patient medication list with Pebblo protection"""
        log_agent_action(logger, "Nurse Agent", "Medication Request", f"Patient: {patient_identifier}")
        
        patient = self.data_service.find_patient_by_identifier(patient_identifier)
        if not patient:
            return {"error": "Patient not found"}
        
        filtered_data, protection = self.pebblo_service.filter_patient_data(patient, self.user_role)
        
        medications = []
        allergies = []
        if 'medical_history' in filtered_data and filtered_data['medical_history'] != '[REDACTED]':
            medications = filtered_data['medical_history'].get('medications', [])
            allergies = filtered_data['medical_history'].get('allergies', [])
        
        return {
            "patient_id": filtered_data.get("patient_id"),
            "name": filtered_data.get("name"),
            "medications": medications,
            "allergies": allergies,
            "pebblo_protection": protection.dict()
        }