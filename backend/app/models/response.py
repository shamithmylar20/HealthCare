from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SecurityEvent(BaseModel):
    """Security event detected by Pebblo MCP"""
    event_type: str = Field(..., description="Type of security event")
    detected_pattern: Optional[str] = Field(None, description="Malicious pattern detected")
    action_taken: str = Field(..., description="Action taken by Pebblo MCP")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class PebbloProtection(BaseModel):
    """Pebblo MCP protection details"""
    fields_redacted: List[str] = Field(default=[], description="Fields redacted by Pebblo")
    injection_detected: bool = Field(default=False, description="Whether injection attack was detected")
    security_events: List[SecurityEvent] = Field(default=[], description="Security events logged")
    policy_applied: str = Field(..., description="Policy applied based on user role")
    access_level: str = Field(..., description="Access level granted")

class AgentResponse(BaseModel):
    """Base response from agents"""
    success: bool = Field(..., description="Whether the request was successful")
    agent_type: str = Field(..., description="Type of agent that processed the request")
    response_data: Dict[str, Any] = Field(..., description="Actual response data")
    pebblo_protection: PebbloProtection = Field(..., description="Pebblo MCP protection details")
    processing_time: float = Field(..., description="Time taken to process request in seconds")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class NurseAgentResponse(BaseModel):
    """Response from Nurse Agent"""
    success: bool = Field(default=True)
    patient_data: Dict[str, Any] = Field(..., description="Patient data (filtered by Pebblo)")
    clinical_summary: str = Field(..., description="Clinical summary for nursing care")
    pebblo_protection: PebbloProtection
    processing_time: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "patient_data": {
                    "patient_id": "PT_001",
                    "name": "Maria Lopez", 
                    "room": "308",
                    "vitals": {
                        "blood_pressure": "120/80",
                        "heart_rate": "72 bpm"
                    },
                    "ssn": "[REDACTED]",
                    "insurance": "[REDACTED]"
                },
                "clinical_summary": "Patient in room 308 has stable vitals, allergic to Penicillin",
                "pebblo_protection": {
                    "fields_redacted": ["ssn", "mrn", "insurance", "phone", "address"],
                    "policy_applied": "nursing_group",
                    "access_level": "clinical_data_only"
                }
            }
        }

class BillingAgentResponse(BaseModel):
    """Response from Billing Agent"""
    success: bool = Field(default=True)
    billing_data: Dict[str, Any] = Field(..., description="Billing data (filtered by Pebblo)")
    billing_summary: str = Field(..., description="Billing summary for insurance processing")
    jira_ticket_info: Optional[Dict[str, Any]] = Field(None, description="Related Jira ticket information")
    pebblo_protection: PebbloProtection
    processing_time: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = Field(default=False)
    error_type: str = Field(..., description="Type of error")
    error_message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class DashboardResponse(BaseModel):
    """Dashboard metrics response"""
    total_queries: int = Field(..., description="Total queries processed")
    security_events: int = Field(..., description="Security events detected")
    policies_enforced: int = Field(..., description="Policies enforced")
    agents_active: List[str] = Field(..., description="Active agents")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())