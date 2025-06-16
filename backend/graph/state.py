from typing import Optional, Dict, Any, List, Annotated
from pydantic import BaseModel, Field

# Import Agents
from agents.info_gathering_agent import RawScriptData
from agents.cost_analysis_agent import CostBreakdown
from agents.props_extraction_agent import PropsBreakdown
from agents.location_analysis_agent import LocationBreakdown
from agents.character_analysis_agent import CharacterBreakdown
from agents.scene_breakdown_agent import SceneBreakdown
from agents.timeline_agent import TimelineBreakdown

# Simplified reducers
def merge_dict(left: Dict, right: Dict) -> Dict:
    """Generic dictionary merger"""
    if not left: return right
    if not right: return left
    return {**left, **right}

def merge_list(left: List, right: List) -> List:
    """Generic list merger"""
    if not left: return right
    if not right: return left
    return left + right

def merge_bool(left: bool, right: bool) -> bool:
    """Boolean merger using OR logic"""
    return left or right

def merge_string(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """String merger - take most recent"""
    return right if right is not None else left

class ScriptAnalysisState(BaseModel):
    """Simplified state for script analysis workflow"""
    # Core input
    script_content: str = Field(description="Original script content")
    
    # Workflow state
    current_agent: Annotated[Optional[str], merge_string] = Field(default=None)
    task_complete: Annotated[bool, merge_bool] = Field(default=False)
    
    # Data extraction
    raw_data: Optional[RawScriptData] = Field(default=None)
    extraction_complete: bool = Field(default=False)
    
    # Analysis results
    cost_analysis: Optional[CostBreakdown] = Field(default=None)
    props_analysis: Optional[PropsBreakdown] = Field(default=None)
    location_analysis: Optional[LocationBreakdown] = Field(default=None)
    character_analysis: Optional[CharacterBreakdown] = Field(default=None)
    scene_analysis: Optional[SceneBreakdown] = Field(default=None)
    timeline_analysis: Optional[TimelineBreakdown] = Field(default=None)

    # Review state
    human_review_complete: Annotated[bool, merge_bool] = Field(default=False)
    human_feedback: Annotated[Dict[str, str], merge_dict] = Field(default_factory=dict)
    needs_revision: Annotated[Dict[str, bool], merge_dict] = Field(
        default_factory=lambda: {
            "cost": False, "props": False, "location": False,
            "character": False, "scene": False, "timeline": False
        }
    )
    
    # Completion tracking
    analyses_complete: Annotated[Dict[str, bool], merge_dict] = Field(
        default_factory=lambda: {
            "cost": False, "props": False, "location": False,
            "character": False, "scene": False, "timeline": False
        }
    )
    
    # Metadata and errors
    processing_metadata: Annotated[Dict[str, Any], merge_dict] = Field(default_factory=dict)
    errors: Annotated[List[str], merge_list] = Field(default_factory=list)