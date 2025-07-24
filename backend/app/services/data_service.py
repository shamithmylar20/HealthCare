import json
from typing import List, Optional, Dict, Any
from pathlib import Path

from app.models import Patient, JiraTicket, UserRole
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class DataService:
    """Handles data access from various sources (mock data for demo)"""
    
    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.patients_data = self._load_patients()
        self.jira_data = self._load_jira_tickets()
    
    def _load_patients(self) -> List[Patient]:
        """Load patient data from JSON file"""
        try:
            patients_path = self.data_dir / "patients.json"
            with open(patients_path, 'r') as f:
                data = json.load(f)
                patients = [Patient(**patient) for patient in data["patients"]]
                logger.info(f"✅ Loaded {len(patients)} patients from {patients_path}")
                return patients
        except Exception as e:
            logger.error(f"❌ Failed to load patients: {e}")
            return []
    
    def _load_jira_tickets(self) -> List[JiraTicket]:
        """Load Jira ticket data from JSON file"""
        try:
            jira_path = self.data_dir / "jira_tickets.json"
            with open(jira_path, 'r') as f:
                data = json.load(f)
                tickets = [JiraTicket(**ticket) for ticket in data["tickets"]]
                logger.info(f"✅ Loaded {len(tickets)} Jira tickets from {jira_path}")
                return tickets
        except Exception as e:
            logger.error(f"❌ Failed to load Jira tickets: {e}")
            return []
    
    def find_patient_by_name(self, name: str) -> Optional[Patient]:
        """Find patient by name (case-insensitive)"""
        name_lower = name.lower()
        for patient in self.patients_data:
            if patient.name.lower() == name_lower:
                logger.info(f"🔍 Found patient: {patient.name} (ID: {patient.patient_id})")
                return patient
        
        logger.warning(f"⚠️ Patient not found: {name}")
        return None
    
    def find_patient_by_id(self, patient_id: str) -> Optional[Patient]:
        """Find patient by ID"""
        for patient in self.patients_data:
            if patient.patient_id == patient_id:
                logger.info(f"🔍 Found patient by ID: {patient.name} ({patient_id})")
                return patient
        
        logger.warning(f"⚠️ Patient not found by ID: {patient_id}")
        return None
    
    def find_patient_by_room(self, room: str) -> Optional[Patient]:
        """Find patient by room number"""
        for patient in self.patients_data:
            if patient.room == room:
                logger.info(f"🔍 Found patient in room {room}: {patient.name}")
                return patient
        
        logger.warning(f"⚠️ No patient found in room: {room}")
        return None
    
    def find_patient_by_identifier(self, identifier: str) -> Optional[Patient]:
        """Find patient by name, ID, or room number"""
        # Try by name first
        patient = self.find_patient_by_name(identifier)
        if patient:
            return patient
        
        # Try by ID
        patient = self.find_patient_by_id(identifier)
        if patient:
            return patient
        
        # Try by room
        patient = self.find_patient_by_room(identifier)
        if patient:
            return patient
        
        logger.warning(f"⚠️ Patient not found by any identifier: {identifier}")
        return None
    
    def get_all_patients(self, limit: Optional[int] = None) -> List[Patient]:
        """Get all patients with optional limit"""
        patients = self.patients_data[:limit] if limit else self.patients_data
        logger.info(f"📋 Retrieved {len(patients)} patients")
        return patients
    
    def find_jira_ticket_by_id(self, ticket_id: str) -> Optional[JiraTicket]:
        """Find Jira ticket by ID"""
        for ticket in self.jira_data:
            if ticket.ticket_id == ticket_id:
                logger.info(f"🎫 Found Jira ticket: {ticket_id}")
                return ticket
        
        logger.warning(f"⚠️ Jira ticket not found: {ticket_id}")
        return None
    
    def find_jira_tickets_by_patient(self, patient_id: str) -> List[JiraTicket]:
        """Find all Jira tickets for a specific patient"""
        tickets = [ticket for ticket in self.jira_data if ticket.patient_ref == patient_id]
        logger.info(f"🎫 Found {len(tickets)} Jira tickets for patient {patient_id}")
        return tickets
    
    def get_all_jira_tickets(self, limit: Optional[int] = None) -> List[JiraTicket]:
        """Get all Jira tickets with optional limit"""
        tickets = self.jira_data[:limit] if limit else self.jira_data
        logger.info(f"📋 Retrieved {len(tickets)} Jira tickets")
        return tickets
    
    def search_patients(self, query: str, user_role: UserRole, limit: int = 10) -> List[Patient]:
        """Search patients based on query and user role"""
        results = []
        query_lower = query.lower()
        
        for patient in self.patients_data:
            # Search in allowed fields based on user role
            if user_role == UserRole.NURSING_GROUP:
                searchable_text = f"{patient.name} {patient.room} {patient.patient_id}".lower()
            elif user_role == UserRole.BILLING_DEPARTMENT:
                searchable_text = f"{patient.name} {patient.room} {patient.patient_id} {patient.insurance.provider}".lower()
            else:
                searchable_text = f"{patient.name} {patient.patient_id}".lower()
            
            if query_lower in searchable_text:
                results.append(patient)
                if len(results) >= limit:
                    break
        
        logger.info(f"🔍 Search '{query}' found {len(results)} patients for role {user_role.value}")
        return results
    
    def get_patient_summary(self, patient: Patient, user_role: UserRole) -> Dict[str, Any]:
        """Get patient summary based on user role permissions"""
        if user_role == UserRole.NURSING_GROUP:
            return {
                "patient_id": patient.patient_id,
                "name": patient.name,
                "room": patient.room,
                "vitals": patient.vitals.dict(),
                "allergies": patient.medical_history.allergies,
                "medications": patient.medical_history.medications,
                "attending_physician": patient.attending_physician
            }
        elif user_role == UserRole.BILLING_DEPARTMENT:
            return {
                "patient_id": patient.patient_id,
                "name": patient.name,
                "room": patient.room,
                "ssn": patient.ssn,
                "mrn": patient.mrn,
                "dob": patient.dob,
                "insurance": patient.insurance.dict(),
                "phone": patient.phone,
                "address": patient.address,
                "admission_date": patient.admission_date
            }
        else:
            return {"patient_id": patient.patient_id, "name": patient.name}