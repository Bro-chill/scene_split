from typing import Any, List, Dict
import asyncio
import inspect
import json
from graph.state import ScriptAnalysisState

def extract_result(result: Any) -> Any:
    """Extract actual result from agent response and ensure JSON serializable"""
    try:
        # Extract result from different response formats
        for attr in ['output', 'data', 'content']:
            if hasattr(result, attr):
                extracted = getattr(result, attr)
                # Ensure it's JSON serializable
                return ensure_json_serializable(extracted)
        
        # If no special attributes, return the result itself
        return ensure_json_serializable(result)
    except Exception as e:
        print(f"⚠️ Error extracting result: {e}")
        return {"error": f"Result extraction failed: {str(e)}"}

def ensure_json_serializable(data: Any) -> Any:
    """Ensure data is JSON serializable"""
    try:
        # Test if it's already JSON serializable
        json.dumps(data, default=str)
        return data
    except (TypeError, ValueError) as e:
        print(f"⚠️ Data not JSON serializable, converting: {e}")
        return convert_to_json_serializable(data)

def convert_to_json_serializable(obj: Any) -> Any:
    """Convert objects to JSON serializable format"""
    if hasattr(obj, 'dict'):
        # Pydantic models
        try:
            return obj.dict()
        except Exception:
            pass
    
    if hasattr(obj, '__dict__'):
        # Regular objects with __dict__
        try:
            return {k: convert_to_json_serializable(v) for k, v in obj.__dict__.items()}
        except Exception:
            pass
    
    if isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    
    # Fallback: convert to string
    return str(obj)

async def safe_call_agent(agent_func, *args, **kwargs):
    """Safely call an agent function with error handling and JSON validation"""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 Calling {getattr(agent_func, '__name__', 'unknown')} (attempt {attempt + 1})")
            
            # Handle different function types
            if inspect.iscoroutinefunction(agent_func):
                result = await agent_func(*args, **kwargs)
            else:
                result = agent_func(*args, **kwargs)
                if inspect.iscoroutine(result):
                    result = await result
            
            if result is None:
                raise ValueError("Agent returned None result")
            
            # Ensure result is JSON serializable
            json_result = ensure_json_serializable(result)
            print(f"✅ Agent call successful: {getattr(agent_func, '__name__', 'unknown')}")
            return json_result
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {str(e)}")
            
            if attempt == max_retries - 1:
                print(f"❌ All attempts failed for {getattr(agent_func, '__name__', 'unknown')}")
                return create_fallback_result(getattr(agent_func, '__name__', 'unknown'))
            
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

def create_fallback_result(agent_name: str) -> Dict[str, Any]:
    """Create JSON-serializable fallback result when agent fails"""
    print(f"🔧 Creating JSON fallback result for {agent_name}")
    
    fallback_map = {
        'analyze_costs': {
            'scene_costs': [],
            'total_budget_range': "Unable to estimate - API Error",
            'estimated_total_days': 0,
            'major_cost_drivers': ["API Error - Unable to analyze"],
            'cost_optimization_tips': ["Please retry analysis"]
        },
        'analyze_props': {
            'scene_props': [],
            'master_props_list': ["Unable to analyze - API Error"],
            'props_by_category': {"error": ["API Error"]},
            'costume_by_character': {},
            'prop_budget_estimate': "Unknown - API Error"
        },
        'analyze_locations': {
            'scene_locations': [],
            'unique_locations': ["Unable to analyze - API Error"],
            'locations_by_type': {"error": ["API Error"]},
            'location_shooting_groups': ["Unable to group - API Error"],
            'permit_requirements': ["Unable to determine - API Error"]
        },
        'analyze_characters': {
            'scene_characters': [],
            'main_characters': ["Unable to analyze - API Error"],
            'supporting_characters': [],
            'character_scene_count': {},
            'casting_requirements': ["Unable to determine - API Error"]
        },
        'analyze_scenes': {
            'detailed_scenes': [],
            'three_act_structure': ["Unable to analyze - API Error"],
            'pacing_analysis': "Unable to analyze - API Error",
            'key_dramatic_scenes': [],
            'action_heavy_scenes': [],
            'dialogue_heavy_scenes': []
        },
        'analyze_timeline': {
            'scene_timelines': [],
            'total_shooting_days': 0,
            'shooting_schedule_by_location': ["Unable to estimate - API Error"],
            'cast_scheduling': {},
            'pre_production_timeline': ["Unable to plan - API Error"],
            'post_production_timeline': ["Unable to plan - API Error"]
        }
    }
    
    return fallback_map.get(agent_name, {
        "error": f"Unable to process {agent_name} - API Error",
        "message": "Please retry the analysis"
    })

def should_revise(state: ScriptAnalysisState) -> List[str]:
    """Determine which nodes need revision"""
    node_mapping = {
        "cost": "cost_node",
        "props": "props_node", 
        "location": "location_node",
        "character": "character_node",
        "scene": "scene_node",
        "timeline": "timeline_node"
    }
    
    revisions_needed = []
    if state.needs_revision:
        for analysis_type, needs_revision in state.needs_revision.items():
            if needs_revision and analysis_type in node_mapping:
                revisions_needed.append(node_mapping[analysis_type])
    
    return revisions_needed

def validate_json_structure(data: Any, expected_fields: List[str] = None) -> bool:
    """Validate that data has expected JSON structure"""
    try:
        # Test JSON serialization
        json.dumps(data, default=str)
        
        # Check expected fields if provided
        if expected_fields and isinstance(data, dict):
            missing_fields = [field for field in expected_fields if field not in data]
            if missing_fields:
                print(f"⚠️ Missing expected fields: {missing_fields}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ JSON validation failed: {e}")
        return False

def sanitize_for_json(data: Any) -> Any:
    """Sanitize data to ensure JSON compatibility"""
    if data is None:
        return None
    
    if isinstance(data, (str, int, float, bool)):
        return data
    
    if isinstance(data, (list, tuple)):
        return [sanitize_for_json(item) for item in data]
    
    if isinstance(data, dict):
        return {str(k): sanitize_for_json(v) for k, v in data.items()}
    
    if hasattr(data, 'dict'):
        try:
            return sanitize_for_json(data.dict())
        except Exception:
            pass
    
    if hasattr(data, '__dict__'):
        try:
            return sanitize_for_json(data.__dict__)
        except Exception:
            pass
    
    # Convert to string as last resort
    return str(data)