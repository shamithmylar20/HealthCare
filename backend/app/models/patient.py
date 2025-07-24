from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Insurance(BaseModel):
    provider: str
    policy_number: str
    group_number: str

class Vitals(BaseModel):
    blood_pressure: str
    heart_rate: str
    temperature: str
    oxygen_saturation: str
    last_updated: str

class MedicalHistory(BaseModel):
    allergies: List[str]
    conditions: List[str]
    medications: List[str]

class Patient(BaseModel):
    patient_id: str
    name: str
    room: str
    ssn: str
    mrn: str
    dob: str
    phone: str
    address: str
    insurance: Insurance
    vitals: Vitals
    medical_history: MedicalHistory
    admission_date: str
    attending_physician: str

class FilteredPatient(BaseModel):
    """Patient data after Pebblo MCP filtering"""
    patient_id: str
    name: Optional[str] = None
    room: Optional[str] = None
    ssn: Optional[str] = "[REDACTED]"
    mrn: Optional[str] = "[REDACTED]"
    dob: Optional[str] = "[REDACTED]"
    phone: Optional[str] = "[REDACTED]"
    address: Optional[str] = "[REDACTED]"
    insurance: Optional[Insurance] = None
    vitals: Optional[Vitals] = None
    medical_history: Optional[MedicalHistory] = None
    admission_date: Optional[str] = None
    attending_physician: Optional[str] = None
    pebblo_filtered: bool = Field(default=True, description="Indicates data was filtered by Pebblo MCP")
    access_level: str = Field(..., description="Access level applied")

class JiraTicket(BaseModel):
    """Jira ticket model"""
    ticket_id: str
    title: str
    description: str
    status: str
    priority: str
    assigned_to: str
    created_date: str
    patient_ref: str
    amount: str
    insurance_provider: str

class FilteredJiraTicket(BaseModel):
    """Filtered Jira ticket after Pebblo MCP processing"""
    ticket_id: str
    title: str
    description: str  # This will be sanitized if malicious content detected
    status: str
    priority: str
    assigned_to: str
    created_date: str
    patient_ref: str
    amount: str
    insurance_provider: str
    pebblo_sanitized: bool = Field(default=False, description="Whether content was sanitized")
    security_events: List[str] = Field(default=[], description="Security events detected")