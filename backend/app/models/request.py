from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from enum import Enum

class UserRole(str, Enum):
    """Valid user roles in the system"""
    NURSING_GROUP = "nursing_group"
    BILLING_DEPARTMENT = "billing_department"

class AgentType(str, Enum):
    """Available agent types"""
    NURSE_AGENT = "nurse_agent"
    BILLING_AGENT = "billing_agent"

class AgentRequest(BaseModel):
    """Base request model for agent interactions"""
    query: str = Field(..., description="Natural language query for the agent")
    user_role: UserRole = Field(..., description="Role of the user making the request")
    agent_type: AgentType = Field(..., description="Type of agent to handle the request")
    patient_id: Optional[str] = Field(None, description="Specific patient ID if applicable")
    room_number: Optional[str] = Field(None, description="Room number if applicable")

class NurseAgentRequest(BaseModel):
    """Specific request model for Nurse Agent"""
    query: str = Field(..., description="Nursing-related query")
    user_role: UserRole = Field(default=UserRole.NURSING_GROUP)
    patient_identifier: Optional[str] = Field(None, description="Patient name, ID, or room number")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Give me the vitals and insurance ID for patient Maria Lopez, room 308",
                "user_role": "nursing_group",
                "patient_identifier": "Maria Lopez"
            }
        }

class BillingAgentRequest(BaseModel):
    """Specific request model for Billing Agent"""
    query: str = Field(..., description="Billing-related query")
    user_role: UserRole = Field(default=UserRole.BILLING_DEPARTMENT)
    patient_identifier: Optional[str] = Field(None, description="Patient name, ID, or room number")
    ticket_id: Optional[str] = Field(None, description="Jira ticket ID if applicable")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Fetch insurance and billing details for Maria Lopez, room 308",
                "user_role": "billing_department", 
                "patient_identifier": "Maria Lopez",
                "ticket_id": "BILL-1299"
            }
        }

class DemoRequest(BaseModel):
    """Simple demo request for testing"""
    patient_name: str = Field(..., description="Patient name to lookup")
    user_role: UserRole = Field(..., description="User role for access control")
    query_type: str = Field(default="general", description="Type of query")
    
    class Config:
        schema_extra = {
            "example": {
                "patient_name": "Maria Lopez",
                "user_role": "nursing_group",
                "query_type": "vitals_check"
            }
        }