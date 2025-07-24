import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
import uvicorn
from dotenv import load_dotenv

from app.models import (
    NurseAgentRequest, BillingAgentRequest, DemoRequest, UserRole, AgentType,
    NurseAgentResponse, BillingAgentResponse, AgentResponse, DashboardResponse
)
from app.services import DataService, PebbloMCPService
from app.agents import HealthcareAgentCrew
from app.utils.logger import setup_logger, log_agent_action

# Load environment variables
load_dotenv()

logger = setup_logger(__name__)

# Global services (will be initialized in lifespan)
data_service: Optional[DataService] = None
pebblo_service: Optional[PebbloMCPService] = None
healthcare_crew: Optional[HealthcareAgentCrew] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global data_service, pebblo_service, healthcare_crew
    
    # Startup
    logger.info("🚀 Starting Healthcare AI Agent System...")
    
    try:
        # Initialize services
        data_service = DataService()
        pebblo_service = PebbloMCPService()
        healthcare_crew = HealthcareAgentCrew(data_service, pebblo_service)
        
        logger.info("✅ All services initialized successfully")
        logger.info("🏥 Healthcare AI Agents: Nurse Agent + Billing Agent")
        logger.info("🛡️ Security: Pebblo MCP Protection Active")
        logger.info("🌐 API Server ready for requests")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Healthcare AI Agent System...")

# Create FastAPI app
app = FastAPI(
    title="Healthcare AI Agent System",
    description="Multi-agent healthcare system with Pebblo MCP protection",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get services
def get_healthcare_crew() -> HealthcareAgentCrew:
    if healthcare_crew is None:
        raise HTTPException(status_code=503, detail="Services not initialized")
    return healthcare_crew

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Healthcare AI Agent System",
        "version": "1.0.0",
        "agents": ["nurse_agent", "billing_agent"],
        "security": "Pebblo MCP Protection",
        "status": "operational"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if healthcare_crew is None:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "message": "Services not initialized"}
            )
        
        metrics = healthcare_crew.get_dashboard_metrics()
        
        return {
            "status": "healthy",
            "timestamp": metrics.get("last_activity"),
            "agents": metrics.get("agents_status", {}),
            "pebblo_mcp": "active"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
        )

# Demo endpoints for frontend
@app.get("/api/demo/nurse/{patient_name}")
async def demo_nurse_query(
    patient_name: str,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Demo nurse agent query"""
    try:
        result = crew.demo_nurse_query(patient_name)
        return result
    except Exception as e:
        logger.error(f"Demo nurse query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo/billing/{patient_name}")
async def demo_billing_query(
    patient_name: str,
    ticket_id: Optional[str] = None,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Demo billing agent query"""
    try:
        result = crew.demo_billing_query(patient_name, ticket_id)
        return result
    except Exception as e:
        logger.error(f"Demo billing query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent-specific endpoints
@app.post("/api/nurse/query", response_model=NurseAgentResponse)
async def nurse_agent_query(
    request: NurseAgentRequest,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Process nurse agent query"""
    try:
        response = crew.nurse_agent.process_query(
            query=request.query,
            patient_identifier=request.patient_identifier
        )
        return response
    except Exception as e:
        logger.error(f"Nurse agent query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/billing/query", response_model=BillingAgentResponse)
async def billing_agent_query(
    request: BillingAgentRequest,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Process billing agent query"""
    try:
        response = crew.billing_agent.process_query(
            query=request.query,
            patient_identifier=request.patient_identifier,
            ticket_id=request.ticket_id
        )
        return response
    except Exception as e:
        logger.error(f"Billing agent query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Generic agent router
@app.post("/api/agents/query", response_model=AgentResponse)
async def route_agent_query(
    query: str,
    user_role: UserRole,
    agent_type: AgentType,
    patient_identifier: Optional[str] = None,
    ticket_id: Optional[str] = None,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Route query to appropriate agent"""
    try:
        response = crew.route_query(
            query=query,
            user_role=user_role,
            agent_type=agent_type,
            patient_identifier=patient_identifier,
            ticket_id=ticket_id
        )
        return response
    except Exception as e:
        logger.error(f"Agent routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Security testing endpoints for demo
@app.get("/api/demo/test-injection")
async def test_injection_attack(
    user_role: UserRole = UserRole.BILLING_DEPARTMENT,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Test injection attack protection"""
    try:
        result = crew.test_injection_attack(user_role)
        return result
    except Exception as e:
        logger.error(f"Injection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo/test-pii-protection")
async def test_pii_protection(
    patient_name: str = "Maria Lopez",
    user_role: UserRole = UserRole.NURSING_GROUP,
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Test PII protection"""
    try:
        result = crew.test_pii_protection(patient_name, user_role)
        return result
    except Exception as e:
        logger.error(f"PII protection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard and monitoring
@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard_metrics(
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Get dashboard metrics"""
    try:
        metrics = crew.get_dashboard_metrics()
        
        return DashboardResponse(
            total_queries=metrics.get("total_queries_processed", 0),
            security_events=metrics.get("security_events_detected", 0),
            policies_enforced=metrics.get("policies_enforced", 0),
            agents_active=list(metrics.get("agents_status", {}).keys())
        )
    except Exception as e:
        logger.error(f"Dashboard metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def system_status(
    crew: HealthcareAgentCrew = Depends(get_healthcare_crew)
):
    """Get detailed system status"""
    try:
        return crew.get_dashboard_metrics()
    except Exception as e:
        logger.error(f"System status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Main entry point
if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    
    uvicorn.run(
        "app.main:app",  # Fixed the module path
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )