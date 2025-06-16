from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class ScenePropsBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    props_needed: List[str] = Field(description='All props needed in this scene')
    costume_requirements: List[str] = Field(description='Costumes for characters in this scene')
    set_decoration: List[str] = Field(description='Set decoration items needed')
    prop_complexity: str = Field(description='Simple/Moderate/Complex prop requirements')

class PropsBreakdown(BaseModel):
    scene_props: List[ScenePropsBreakdown] = Field(description='Props breakdown per scene')
    master_props_list: List[str] = Field(description='Complete props list across all scenes')
    props_by_category: Dict[str, List[str]] = Field(description='Props organized by category')
    costume_by_character: Dict[str, List[str]] = Field(description='Costume requirements by character')
    prop_budget_estimate: str = Field(description='Low/Medium/High props budget category')

scene_props_agent = Agent(
    model,
    output_type=ScenePropsBreakdown,
    system_prompt="""Analyze props, costumes, and set decoration for this scene. 
    Be thorough and practical for production planning."""
)

overall_props_agent = Agent(
    model,
    output_type=PropsBreakdown,
    system_prompt="""Analyze overall props requirements and provide actionable 
    props department planning."""
)

async def analyze_props(raw_data: RawScriptData) -> PropsBreakdown:
    """Analyze props and costumes scene by scene and overall"""
    scene_props = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_props_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Location: {scene.location}\n"
                f"Characters: {', '.join(scene.characters_present)}\n"
                f"Props mentioned: {', '.join(scene.props_mentioned)}"
            )
            scene_prop = scene_analysis.output
            scene_prop.scene_number = scene.scene_number
            scene_props.append(scene_prop)
        except Exception as e:
            print(f"Props analysis failed for scene {scene.scene_number}: {e}")
            scene_props.append(_create_fallback_scene_props(scene))
    
    try:
        all_props = []
        for sp in scene_props:
            all_props.extend(sp.props_needed)
        
        overall_analysis = await overall_props_agent.run(
            f"All props from scenes: {', '.join(set(all_props))}\n"
            f"Characters: {', '.join(raw_data.total_characters)}\n"
            f"Locations: {', '.join(raw_data.total_locations)}"
        )
        props_breakdown = overall_analysis.output
        props_breakdown.scene_props = scene_props
        return props_breakdown
    except Exception as e:
        print(f"Overall props analysis failed: {e}")
        return _create_fallback_props_breakdown(scene_props, raw_data)

def _create_fallback_scene_props(scene: SceneData) -> ScenePropsBreakdown:
    """Create fallback scene props estimation"""
    props_needed = scene.props_mentioned.copy()
    
    # Add location-based props
    location_lower = scene.location.lower()
    if "office" in location_lower:
        props_needed.extend(["desk", "chair", "computer"])
    elif "kitchen" in location_lower:
        props_needed.extend(["table", "chairs", "dishes"])
    
    costume_requirements = [f"Costume for {char}" for char in scene.characters_present]
    set_decoration = [f"Dress {scene.location}"]
    
    return ScenePropsBreakdown(
        scene_number=scene.scene_number,
        props_needed=list(set(props_needed)),
        costume_requirements=costume_requirements,
        set_decoration=set_decoration,
        prop_complexity="Moderate"
    )

def _create_fallback_props_breakdown(scene_props: List[ScenePropsBreakdown], 
                                   raw_data: RawScriptData) -> PropsBreakdown:
    """Create fallback overall props estimation"""
    all_props = []
    for sp in scene_props:
        all_props.extend(sp.props_needed)
    master_props = list(set(all_props))
    
    # Categorize props
    furniture_keywords = ["chair", "table", "desk"]
    electronics_keywords = ["phone", "computer"]
    
    furniture_props = [p for p in master_props if any(f in p.lower() for f in furniture_keywords)]
    electronics_props = [p for p in master_props if any(e in p.lower() for e in electronics_keywords)]
    other_props = [p for p in master_props if p not in furniture_props + electronics_props]
    
    categories = {
        "Furniture": furniture_props,
        "Electronics": electronics_props,
        "Other": other_props
    }
    
    costume_by_character = {char: [f"Costume for {char}"] for char in raw_data.total_characters}
    
    return PropsBreakdown(
        scene_props=scene_props,
        master_props_list=master_props,
        props_by_category=categories,
        costume_by_character=costume_by_character,
        prop_budget_estimate="Medium"
    )