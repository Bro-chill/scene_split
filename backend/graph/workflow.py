from datetime import datetime
from typing import Optional, Dict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import ScriptAnalysisState
from graph.utils import should_revise, ensure_json_serializable, validate_json_structure
from graph.nodes import (
    run_info_gathering, run_cost_analysis, run_props_analysis,
    run_location_analysis, run_character_analysis, run_scene_analysis,
    run_timeline_analysis, human_review
)

from agents.info_gathering_agent import extract_script_data_from_file
import json

def should_continue_or_end(state: ScriptAnalysisState):
    """Determine next step after human review with JSON validation"""
    print("🔍 Checking workflow continuation...")
    
    # Validate current state
    try:
        state_dict = state.model_dump() if hasattr(state, 'dict') else state.__dict__
        json.dumps(state_dict, default=str)  # Test JSON serialization
        print("✅ State is JSON serializable")
    except Exception as e:
        print(f"⚠️ State JSON validation failed: {e}")
    
    if state.human_review_complete:
        print("✅ Human review complete - ending workflow")
        return "END"
    
    nodes_to_revise = should_revise(state)
    if nodes_to_revise:
        next_node = nodes_to_revise[0]
        print(f"🔄 Continuing to revision: {next_node}")
        return next_node
    
    print("✅ No revisions needed - ending workflow")
    return "END"

def create_script_analysis_workflow():
    """Create and return the script analysis workflow with JSON validation"""
    # Initialize memory saver for checkpointing
    memory = MemorySaver()
    
    workflow = StateGraph(ScriptAnalysisState)
    
    # Add nodes
    nodes = {
        "info_gathering": run_info_gathering,
        "cost_node": run_cost_analysis,
        "props_node": run_props_analysis,
        "location_node": run_location_analysis,
        "character_node": run_character_analysis,
        "scene_node": run_scene_analysis,
        "timeline_node": run_timeline_analysis,
        "human_review": human_review
    }
    
    for name, func in nodes.items():
        workflow.add_node(name, func)
    
    # Add edges
    workflow.add_edge(START, "info_gathering")
    
    # Info gathering fans out to all analysis nodes
    analysis_nodes = ["cost_node", "props_node", "location_node", "character_node", "scene_node", "timeline_node"]
    for node in analysis_nodes:
        workflow.add_edge("info_gathering", node)
        workflow.add_edge(node, "human_review")
    
    # Conditional edges from human review
    workflow.add_conditional_edges(
        "human_review",
        should_continue_or_end,
        {
            "END": END,
            **{node: node for node in analysis_nodes}
        }
    )
    
    # Compile with checkpointer
    return workflow.compile(checkpointer=memory)

# Create the compiled graph
analyze_script_workflow = create_script_analysis_workflow()

async def run_analyze_script_workflow_from_file(
    file_path: str,
    human_feedback: Optional[Dict] = None,
    thread_id: str = "default_thread"
) -> ScriptAnalysisState:
    """Run workflow from uploaded file with JSON validation"""
    
    # Extract content from file first
    from agents.pdf_utils import extract_text_from_pdf, validate_script_content
    from pathlib import Path
    
    file_path = Path(file_path)
    
    try:
        if file_path.suffix.lower() == '.pdf':
            script_content = extract_text_from_pdf(str(file_path))
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
        
        # Validate extracted content
        if not script_content or len(script_content.strip()) < 10:
            raise ValueError("Extracted content is too short or empty")
        
        print(f"✅ Successfully extracted {len(script_content)} characters from {file_path.name}")
        
        # Use existing workflow with extracted content
        return await run_analyze_script_workflow(
            script_content, 
            human_feedback, 
            thread_id
        )
        
    except Exception as e:
        print(f"❌ File processing failed: {e}")
        raise ValueError(f"Failed to process file {file_path.name}: {str(e)}")

async def run_analyze_script_workflow(
    script_content: str, 
    human_feedback: Optional[Dict] = None,
    thread_id: str = "default_thread"
) -> ScriptAnalysisState:
    """Run the complete script analysis workflow with JSON validation"""
    print("🎬 Starting Script Analysis Workflow")
    print("=" * 50)
    
    # Validate input
    if not script_content or len(script_content.strip()) < 10:
        raise ValueError("Script content is too short or empty")
    
    # Initialize state
    initial_state = ScriptAnalysisState(
        script_content=script_content,
        processing_metadata={
            "workflow_start_time": datetime.now().isoformat(),
            "json_validation_enabled": True
        }
    )
    
    # Add human feedback if provided
    if human_feedback:
        print("📝 Processing human feedback for revisions...")
        initial_state.human_feedback = human_feedback.get('feedback', {})
        initial_state.needs_revision = human_feedback.get('needs_revision', {})
        initial_state.processing_metadata["revision_mode"] = True
        initial_state.human_review_complete = False
    
    try:
        # Create config with thread_id for checkpointing
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 25
        }
        
        print(f"🚀 Running workflow with thread_id: {thread_id}")
        
        final_state_dict = await analyze_script_workflow.ainvoke(
            initial_state,
            config=config
        )
        
        # Validate final state JSON structure
        try:
            json.dumps(final_state_dict, default=str)
            print("✅ Final state is JSON serializable")
        except Exception as e:
            print(f"⚠️ Final state JSON validation failed: {e}")
            # Sanitize the state
            final_state_dict = ensure_json_serializable(final_state_dict)
        
        final_state = ScriptAnalysisState(**final_state_dict)
        
        print("\n" + "=" * 50)
        print("🎉 Script Analysis Workflow Completed!")
        
        # Summary statistics
        successful_analyses = sum(1 for completed in final_state.analyses_complete.values() if completed)
        total_time = _calculate_total_time(final_state)
        
        print(f"📊 Summary:")
        print(f"   - Thread ID: {thread_id}")
        print(f"   - Total processing time: {total_time:.2f} seconds")
        print(f"   - Successful analyses: {successful_analyses}")
        print(f"   - Extraction completed: {final_state.extraction_complete}")
        print(f"   - Task completed: {final_state.task_complete}")
        print(f"   - JSON validation: ✅")
        
        if final_state.errors:
            print(f"⚠️  Errors encountered: {len(final_state.errors)}")
        
        return final_state
        
    except Exception as e:
        print(f"❌ Workflow failed: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise

# Add utility functions for checkpoint management with JSON validation
async def get_workflow_state(thread_id: str) -> Optional[ScriptAnalysisState]:
    """Get the current state of a workflow thread with JSON validation"""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state_dict = await analyze_script_workflow.aget_state(config)
        
        if state_dict and state_dict.values:
            # Validate JSON structure
            try:
                json.dumps(state_dict.values, default=str)
                print(f"✅ Retrieved state for {thread_id} is JSON valid")
            except Exception as e:
                print(f"⚠️ Retrieved state JSON validation failed: {e}")
                # Sanitize the state
                state_dict.values = ensure_json_serializable(state_dict.values)
            
            return ScriptAnalysisState(**state_dict.values)
        return None
    except Exception as e:
        print(f"❌ Error getting workflow state: {str(e)}")
        return None

async def resume_workflow(thread_id: str, human_feedback: Optional[Dict] = None) -> ScriptAnalysisState:
    """Resume a workflow from its last checkpoint with JSON validation"""
    print(f"🔄 Resuming workflow for thread: {thread_id}")
    
    # Get current state
    current_state = await get_workflow_state(thread_id)
    if not current_state:
        raise ValueError(f"No workflow state found for thread: {thread_id}")
    
    # Apply human feedback if provided
    if human_feedback:
        print("📝 Applying human feedback...")
        current_state.human_feedback = human_feedback.get('feedback', {})
        current_state.needs_revision = human_feedback.get('needs_revision', {})
        current_state.processing_metadata["revision_mode"] = True
        current_state.human_review_complete = False
        
        # Validate feedback structure
        try:
            json.dumps(human_feedback, default=str)
            print("✅ Human feedback is JSON valid")
        except Exception as e:
            print(f"⚠️ Human feedback JSON validation failed: {e}")
    
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25
    }
    
    try:
        # Resume from checkpoint
        final_state_dict = await analyze_script_workflow.ainvoke(None, config=config)
        
        # Validate final state
        try:
            json.dumps(final_state_dict, default=str)
            print("✅ Resumed workflow final state is JSON valid")
        except Exception as e:
            print(f"⚠️ Resumed state JSON validation failed: {e}")
            final_state_dict = ensure_json_serializable(final_state_dict)
        
        return ScriptAnalysisState(**final_state_dict)
        
    except Exception as e:
        print(f"❌ Failed to resume workflow: {str(e)}")
        raise

def _calculate_total_time(final_state: ScriptAnalysisState) -> float:
    """Calculate total processing time"""
    start_time_str = final_state.processing_metadata.get("workflow_start_time")
    if start_time_str:
        try:
            start_time = datetime.fromisoformat(start_time_str)
            return (datetime.now() - start_time).total_seconds()
        except Exception:
            pass
    return final_state.processing_metadata.get("extraction_time_seconds", 0)

def validate_workflow_state(state: ScriptAnalysisState) -> Dict[str, bool]:
    """Validate all components of workflow state for JSON compatibility"""
    validation_results = {}
    
    # Check main analysis components
    analysis_components = [
        'raw_data', 'cost_analysis', 'character_analysis', 
        'location_analysis', 'props_analysis', 'scene_analysis', 'timeline_analysis'
    ]
    
    for component in analysis_components:
        data = getattr(state, component, None)
        validation_results[component] = validate_json_structure(data)
    
    # Check metadata
    validation_results['processing_metadata'] = validate_json_structure(state.processing_metadata)
    validation_results['human_feedback'] = validate_json_structure(state.human_feedback)
    validation_results['needs_revision'] = validate_json_structure(state.needs_revision)
    
    return validation_results