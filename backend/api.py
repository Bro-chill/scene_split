from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import tempfile
from pathlib import Path
import uuid
import sys
import os
import json
import traceback

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from graph.workflow import run_analyze_script_workflow, resume_workflow, get_workflow_state
from graph.workflow import run_analyze_script_workflow_from_file

app = FastAPI(title="Script Analysis API", version="1.0.0")

# Add CORS middleware with JSON-specific headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type"]  # Expose content-type header
)

class ScriptRequest(BaseModel):
    script_content: str

class FeedbackRequest(BaseModel):
    thread_id: str
    feedback: Dict[str, str]
    needs_revision: Dict[str, bool]

def convert_result_to_dict(result):
    """Convert Pydantic models to dictionaries for JSON serialization"""
    try:
        return {
            "raw_data": result.raw_data.dict() if result.raw_data else None,
            "cost_analysis": result.cost_analysis.dict() if result.cost_analysis else None,
            "character_analysis": result.character_analysis.dict() if result.character_analysis else None,
            "location_analysis": result.location_analysis.dict() if result.location_analysis else None,
            "props_analysis": result.props_analysis.dict() if result.props_analysis else None,
            "scene_analysis": result.scene_analysis.dict() if result.scene_analysis else None,
            "timeline_analysis": result.timeline_analysis.dict() if result.timeline_analysis else None,
            "task_complete": result.task_complete,
            "human_review_complete": result.human_review_complete,
            "analyses_complete": result.analyses_complete,
            "errors": result.errors
        }
    except Exception as e:
        print(f"❌ Error converting result to dict: {str(e)}")
        return {
            "raw_data": None,
            "cost_analysis": None,
            "character_analysis": None,
            "location_analysis": None,
            "props_analysis": None,
            "scene_analysis": None,
            "timeline_analysis": None,
            "task_complete": False,
            "human_review_complete": False,
            "analyses_complete": {},
            "errors": [f"Data conversion error: {str(e)}"]
        }

def create_success_response(data: dict, message: str = "Success") -> JSONResponse:
    """Create standardized success JSON response"""
    response_data = {
        "success": True,
        "message": message,
        **data
    }
    return JSONResponse(
        content=response_data,
        headers={"Content-Type": "application/json"}
    )

def create_error_response(message: str, status_code: int = 500, details: str = None) -> JSONResponse:
    """Create standardized error JSON response"""
    response_data = {
        "success": False,
        "error": message,
        "message": message
    }
    if details:
        response_data["details"] = details
    
    return JSONResponse(
        content=response_data,
        status_code=status_code,
        headers={"Content-Type": "application/json"}
    )

@app.post("/analyze-script-file")
async def analyze_script_file(file: UploadFile = File(...)):
    """Analyze script from uploaded PDF or text file"""
    try:
        # Validate file type
        allowed_types = ['.pdf', '.txt', '.fountain']
        file_suffix = Path(file.filename).suffix.lower() if file.filename else ''
        
        if file_suffix not in allowed_types:
            return create_error_response(
                f"Unsupported file type. Allowed: {', '.join(allowed_types)}",
                status_code=400
            )
        
        # # Save uploaded file temporarily
        # import tempfile
        # from pathlib import Path
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            thread_id = f"script_{uuid.uuid4().hex[:8]}"
            print(f"🚀 Starting analysis for uploaded file: {file.filename}")
            
            # Use the file-based workflow
            result = await run_analyze_script_workflow_from_file(
                temp_file_path, 
                thread_id=thread_id
            )
            
            response_data = {
                "thread_id": thread_id,
                "filename": file.filename,
                "needs_human_review": not result.task_complete,
                "data": convert_result_to_dict(result)
            }
            
            return create_success_response(
                response_data,
                f"Analysis completed for {file.filename}. Please review the results."
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except Exception as e:
        print(f"❌ File analysis failed: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_error_response(
            "File analysis failed",
            details=str(e)
        )

@app.post("/analyze-script")
async def analyze_script(request: ScriptRequest):
    """Initial script analysis"""
    try:
        thread_id = f"script_{uuid.uuid4().hex[:8]}"
        print(f"🚀 Starting analysis for thread: {thread_id}")
        
        result = await run_analyze_script_workflow(
            request.script_content, 
            thread_id=thread_id
        )
        
        response_data = {
            "thread_id": thread_id,
            "needs_human_review": not result.task_complete,
            "data": convert_result_to_dict(result)
        }
        
        return create_success_response(
            response_data,
            "Initial analysis completed. Please review the results."
        )
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_error_response(
            "Analysis failed",
            details=str(e)
        )

@app.post("/submit-feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit human feedback and trigger revisions"""
    try:
        print(f"📝 Processing feedback for thread: {request.thread_id}")
        print(f"Revisions requested: {[k for k, v in request.needs_revision.items() if v]}")
        
        # Check if any revisions are actually needed
        if not any(request.needs_revision.values()):
            # No revisions needed - just mark as complete
            current_state = await get_workflow_state(request.thread_id)
            if current_state:
                current_state.human_review_complete = True
                current_state.task_complete = True
                
                response_data = {
                    "thread_id": request.thread_id,
                    "needs_human_review": False,
                    "data": convert_result_to_dict(current_state)
                }
                
                return create_success_response(
                    response_data,
                    "All analyses approved. Analysis complete!"
                )
        
        # Process revisions
        human_feedback = {
            "feedback": request.feedback,
            "needs_revision": request.needs_revision
        }
        
        result = await resume_workflow(request.thread_id, human_feedback)
        
        response_data = {
            "thread_id": request.thread_id,
            "needs_human_review": not result.task_complete,
            "data": convert_result_to_dict(result)
        }
        
        message = ("Revisions processed. Please review the updated results." 
                  if not result.task_complete else "All revisions complete!")
        
        return create_success_response(response_data, message)
        
    except Exception as e:
        print(f"❌ Feedback processing failed: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return create_error_response(
            "Feedback processing failed",
            details=str(e)
        )

@app.get("/workflow-status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """Get current workflow status"""
    try:
        state = await get_workflow_state(thread_id)
        if not state:
            return create_error_response(
                "Workflow not found",
                status_code=404
            )
        
        response_data = {
            "thread_id": thread_id,
            "task_complete": state.task_complete,
            "human_review_complete": state.human_review_complete,
            "analyses_complete": state.analyses_complete,
            "needs_revision": state.needs_revision
        }
        
        return create_success_response(response_data, "Status retrieved successfully")
        
    except Exception as e:
        print(f"❌ Status check failed: {str(e)}")
        return create_error_response(
            "Failed to get workflow status",
            details=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return create_success_response(
        {"status": "healthy"},
        "Script Analysis API is running"
    )

# Add global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler to ensure JSON responses"""
    print(f"❌ Unhandled exception: {str(exc)}")
    print(f"Full traceback: {traceback.format_exc()}")
    
    return create_error_response(
        "Internal server error",
        status_code=500,
        details=str(exc)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)