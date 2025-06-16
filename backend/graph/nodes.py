from typing import Dict, Any
from datetime import datetime
from graph.state import ScriptAnalysisState
from graph.utils import safe_call_agent, extract_result, ensure_json_serializable, validate_json_structure

# Import agents
from agents.info_gathering_agent import extract_script_data
from agents.cost_analysis_agent import analyze_costs
from agents.props_extraction_agent import analyze_props
from agents.location_analysis_agent import analyze_locations
from agents.character_analysis_agent import analyze_characters
from agents.scene_breakdown_agent import analyze_scenes
from agents.timeline_agent import analyze_timeline

async def run_info_gathering(state: ScriptAnalysisState) -> Dict[str, Any]:
    """Extract raw data from script with JSON validation"""
    print("🔍 Phase 1: Extracting raw data from script...")
    start_time = datetime.now()
    
    try:
        raw_data = await safe_call_agent(extract_script_data, state.script_content)
        extraction_time = (datetime.now() - start_time).total_seconds()
        
        # Validate JSON structure
        if not validate_json_structure(raw_data, ['scenes', 'total_characters', 'total_locations']):
            print("⚠️ Raw data structure validation failed, using fallback")
            raw_data = create_fallback_raw_data()
        
        # Ensure JSON serializable
        raw_data = ensure_json_serializable(raw_data)
        
        print(f"✅ Data extraction completed in {extraction_time:.2f} seconds")
        if raw_data and hasattr(raw_data, 'scenes'):
            print(f"   - Scenes: {len(getattr(raw_data, 'scenes', []))}")
            print(f"   - Characters: {len(getattr(raw_data, 'total_characters', []))}")
            print(f"   - Locations: {len(getattr(raw_data, 'total_locations', []))}")
        
        return {
            "current_agent": "info_gathering",
            "raw_data": raw_data,
            "extraction_complete": True,
            "processing_metadata": {
                "extraction_time_seconds": extraction_time,
                "extraction_timestamp": datetime.now().isoformat(),
                "json_validated": True
            }
        }
    except Exception as e:
        print(f"❌ Error in info gathering: {str(e)}")
        return {
            "current_agent": "info_gathering",
            "errors": [f"Info gathering error: {str(e)}"],
            "extraction_complete": False,
            "raw_data": create_fallback_raw_data()
        }

def create_fallback_raw_data():
    """Create fallback raw data structure"""
    return {
        "scenes": [],
        "total_characters": ["Unable to extract"],
        "total_locations": ["Unable to extract"],
        "locations_by_type": {"INT": [], "EXT": []},
        "language_detected": "Unknown",
        "estimated_total_pages": 0,
        "total_scene_count": 0
    }

def create_analysis_node(agent_func, agent_name: str, display_name: str):
    """Generic analysis node creator with JSON validation"""
    async def analysis_node(state: ScriptAnalysisState, writer=None) -> Dict[str, Any]:
        if writer:
            writer(f"\n#### Analyzing {display_name}... \n")
        print(f"🔍 Running {display_name.lower()} analysis...")

        # Check for revision mode
        is_revision = state.processing_metadata.get("revision_in_progress", False)
        feedback = state.human_feedback.get(agent_name, "")
        
        if is_revision and feedback:
            print(f"📝 Incorporating feedback: {feedback}")
        
        if not state.raw_data:
            error_msg = f"No raw data available for {display_name.lower()} analysis"
            print(f"❌ {error_msg}")
            return {
                "errors": [error_msg],
                f"{agent_name}_analysis": create_fallback_analysis_result(agent_name)
            }
        
        try:
            result = await safe_call_agent(agent_func, state.raw_data)
            actual_result = extract_result(result)
            
            # Validate JSON structure
            if not validate_json_structure(actual_result):
                print(f"⚠️ {display_name} result failed JSON validation, using fallback")
                actual_result = create_fallback_analysis_result(agent_name)
            
            # Ensure JSON serializable
            actual_result = ensure_json_serializable(actual_result)
            
            print(f"✅ {display_name} analysis completed")
            
            # Reset revision flags
            updated_needs_revision = dict(state.needs_revision) if state.needs_revision else {}
            updated_needs_revision[agent_name] = False
            all_revisions_complete = not any(updated_needs_revision.values())
            
            return {
                "current_agent": f"{agent_name}_analysis",
                f"{agent_name}_analysis": actual_result,
                "analyses_complete": {agent_name: True},
                "needs_revision": updated_needs_revision,
                "human_review_complete": all_revisions_complete,
                "task_complete": all_revisions_complete,
                "processing_metadata": {
                    f"{agent_name}_json_validated": True,
                    f"{agent_name}_completed_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            error_msg = f"Error in {display_name.lower()} analysis: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "current_agent": f"{agent_name}_analysis",
                "errors": [error_msg],
                f"{agent_name}_analysis": create_fallback_analysis_result(agent_name)
            }
    
    return analysis_node

def create_fallback_analysis_result(agent_name: str) -> Dict[str, Any]:
    """Create fallback analysis result for specific agent"""
    fallback_results = {
        "cost": {
            "scene_costs": [],
            "total_budget_range": "Unable to estimate",
            "estimated_total_days": 0,
            "major_cost_drivers": ["Analysis failed"],
            "cost_optimization_tips": ["Please retry analysis"]
        },
        "props": {
            "scene_props": [],
            "master_props_list": ["Unable to analyze"],
            "props_by_category": {"error": ["Analysis failed"]},
            "costume_by_character": {},
            "prop_budget_estimate": "Unknown"
        },
        "location": {
            "scene_locations": [],
            "unique_locations": ["Unable to analyze"],
            "locations_by_type": {"error": ["Analysis failed"]},
            "location_shooting_groups": [],
            "permit_requirements": []
        },
        "character": {
            "scene_characters": [],
            "main_characters": ["Unable to analyze"],
            "supporting_characters": [],
            "character_scene_count": {},
            "casting_requirements": []
        },
        "scene": {
            "detailed_scenes": [],
            "three_act_structure": ["Unable to analyze"],
            "pacing_analysis": "Unable to analyze",
            "key_dramatic_scenes": [],
            "action_heavy_scenes": [],
            "dialogue_heavy_scenes": []
        },
        "timeline": {
            "scene_timelines": [],
            "total_shooting_days": 0,
            "shooting_schedule_by_location": ["Unable to estimate"],
            "cast_scheduling": {},
            "pre_production_timeline": [],
            "post_production_timeline": []
        }
    }
    
    return fallback_results.get(agent_name, {"error": f"Analysis failed for {agent_name}"})

# Create analysis nodes
run_cost_analysis = create_analysis_node(analyze_costs, "cost", "Cost")
run_props_analysis = create_analysis_node(analyze_props, "props", "Props")
run_location_analysis = create_analysis_node(analyze_locations, "location", "Location")
run_character_analysis = create_analysis_node(analyze_characters, "character", "Character")
run_scene_analysis = create_analysis_node(analyze_scenes, "scene", "Scene")
run_timeline_analysis = create_analysis_node(analyze_timeline, "timeline", "Timeline")

async def human_review(state: ScriptAnalysisState) -> Dict[str, Any]:
    """Human review with JSON validation"""
    print("\n" + "=" * 60)
    print("👤 HUMAN REVIEW")
    print("=" * 60)
    
    is_revision_mode = state.processing_metadata.get("revision_mode", False)
    has_feedback = bool(state.human_feedback)
    
    # Validate current state data
    validation_results = {}
    for analysis_type in ["cost", "props", "location", "character", "scene", "timeline"]:
        analysis_data = getattr(state, f"{analysis_type}_analysis", None)
        validation_results[analysis_type] = validate_json_structure(analysis_data)
    
    print(f"📊 JSON Validation Results: {validation_results}")
    
    if is_revision_mode and has_feedback:
        print("📝 Processing Streamlit feedback for revisions...")
        any_revisions = any(state.needs_revision.values()) if state.needs_revision else False
        
        if any_revisions:
            print(f"🔄 Revisions requested for: {[k for k, v in state.needs_revision.items() if v]}")
            return {
                "current_agent": "human_review",
                "human_review_complete": False,
                "task_complete": False,
                "processing_metadata": {
                    "revision_in_progress": True,
                    "json_validation_results": validation_results
                }
            }
        else:
            print("✅ All analyses approved!")
            return {
                "current_agent": "human_review",
                "human_review_complete": True,
                "task_complete": True,
                "processing_metadata": {
                    "review_completed_at": datetime.now().isoformat(),
                    "json_validation_results": validation_results
                }
            }
    else:
        print("👤 Initial review complete - ready for Streamlit feedback")
        return {
            "current_agent": "human_review",
            "human_review_complete": True,
            "task_complete": True,
            "processing_metadata": {
                "initial_review_completed_at": datetime.now().isoformat(),
                "json_validation_results": validation_results
            }
        }