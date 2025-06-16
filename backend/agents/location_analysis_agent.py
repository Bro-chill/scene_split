from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class SceneLocationBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    location_name: str = Field(description='Location name')
    location_type: str = Field(description='INT/EXT and specific type')
    time_of_day: str = Field(description='Time requirements')
    setup_complexity: str = Field(description='Simple/Moderate/Complex setup')
    permit_needed: bool = Field(description='Whether permits are required')

class LocationBreakdown(BaseModel):
    scene_locations: List[SceneLocationBreakdown] = Field(description='Location breakdown per scene')
    unique_locations: List[str] = Field(description='All unique locations needed')
    locations_by_type: Dict[str, List[str]] = Field(description='Locations grouped by INT/EXT')
    location_shooting_groups: List[str] = Field(description='Recommended shooting groups by location')
    permit_requirements: List[str] = Field(description='Permit needs by location')

scene_location_agent = Agent(
    model,
    output_type=SceneLocationBreakdown,
    system_prompt="""Analyze location requirements for this scene including setup needs, 
    permits, and logistics. Provide practical location management guidance."""
)

overall_location_agent = Agent(
    model,
    output_type=LocationBreakdown,
    system_prompt="""Analyze overall location strategy for efficient shooting and 
    comprehensive location department planning."""
)

async def analyze_locations(raw_data: RawScriptData) -> LocationBreakdown:
    """Analyze locations scene by scene and overall"""
    scene_locations = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_location_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Location: {scene.location} ({scene.scene_type})\n"
                f"Time: {scene.time_of_day}"
            )
            scene_loc = scene_analysis.output
            scene_loc.scene_number = scene.scene_number
            scene_locations.append(scene_loc)
        except Exception as e:
            print(f"Location analysis failed for scene {scene.scene_number}: {e}")
            scene_locations.append(_create_fallback_scene_location(scene))
    
    try:
        overall_analysis = await overall_location_agent.run(
            f"All locations: {raw_data.total_locations}\n"
            f"INT locations: {raw_data.locations_by_type['INT']}\n"
            f"EXT locations: {raw_data.locations_by_type['EXT']}"
        )
        location_breakdown = overall_analysis.output
        location_breakdown.scene_locations = scene_locations
        return location_breakdown
    except Exception as e:
        print(f"Overall location analysis failed: {e}")
        return _create_fallback_location_breakdown(scene_locations, raw_data)

def _create_fallback_scene_location(scene: SceneData) -> SceneLocationBreakdown:
    """Create fallback scene location analysis"""
    permit_needed = scene.scene_type == "EXT" or "public" in scene.location.lower()
    
    return SceneLocationBreakdown(
        scene_number=scene.scene_number,
        location_name=scene.location,
        location_type=f"{scene.scene_type} - {scene.location}",
        time_of_day=scene.time_of_day,
        setup_complexity="Moderate",
        permit_needed=permit_needed
    )

def _create_fallback_location_breakdown(scene_locations: List[SceneLocationBreakdown], 
                                      raw_data: RawScriptData) -> LocationBreakdown:
    """Create fallback overall location analysis"""
    location_groups = {}
    for scene_loc in scene_locations:
        loc = scene_loc.location_name
        if loc not in location_groups:
            location_groups[loc] = []
        location_groups[loc].append(scene_loc.scene_number)
    
    shooting_groups = [f"Shoot scenes {scenes} at {loc}" for loc, scenes in location_groups.items()]
    permit_requirements = [f"Permit for {loc}" for loc in raw_data.locations_by_type["EXT"]]
    
    return LocationBreakdown(
        scene_locations=scene_locations,
        unique_locations=raw_data.total_locations,
        locations_by_type=raw_data.locations_by_type,
        location_shooting_groups=shooting_groups,
        permit_requirements=permit_requirements
    )