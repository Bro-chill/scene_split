from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class SceneTimelineBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    estimated_shoot_time: int = Field(description='Estimated shooting time in hours')
    setup_time: int = Field(description='Setup time required in hours')
    crew_requirements: List[str] = Field(description='Crew needed for this scene')
    scheduling_priority: str = Field(description='High/Medium/Low scheduling priority')

class TimelineBreakdown(BaseModel):
    scene_timelines: List[SceneTimelineBreakdown] = Field(description='Timeline breakdown per scene')
    total_shooting_days: int = Field(description='Total estimated shooting days')
    shooting_schedule_by_location: List[str] = Field(description='Recommended shooting order by location')
    cast_scheduling: Dict[str, List[int]] = Field(description='Which scenes each actor is needed for')
    pre_production_timeline: List[str] = Field(description='Pre-production milestones')
    post_production_timeline: List[str] = Field(description='Post-production phases')

scene_timeline_agent = Agent(
    model,
    output_type=SceneTimelineBreakdown,
    system_prompt="""Analyze shooting timeline for this scene considering setup time, 
    crew needs, and scheduling priorities. Provide realistic time estimates."""
)

overall_timeline_agent = Agent(
    model,
    output_type=TimelineBreakdown,
    system_prompt="""Analyze overall production timeline and provide comprehensive 
    production scheduling guidance."""
)

async def analyze_timeline(raw_data: RawScriptData) -> TimelineBreakdown:
    """Analyze timeline and scheduling scene by scene and overall"""
    scene_timelines = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_timeline_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Location: {scene.location} ({scene.scene_type})\n"
                f"Characters: {', '.join(scene.characters_present)}\n"
                f"Estimated pages: {scene.estimated_pages}"
            )
            scene_timeline = scene_analysis.output
            scene_timeline.scene_number = scene.scene_number
            scene_timelines.append(scene_timeline)
        except Exception as e:
            print(f"Timeline analysis failed for scene {scene.scene_number}: {e}")
            scene_timelines.append(_create_fallback_scene_timeline(scene))
    
    # Create cast scheduling
    cast_scheduling = {}
    for scene in raw_data.scenes:
        for char in scene.characters_present:
            if char not in cast_scheduling:
                cast_scheduling[char] = []
            cast_scheduling[char].append(scene.scene_number)
    
    try:
        total_hours = sum(st.estimated_shoot_time + st.setup_time for st in scene_timelines)
        
        overall_analysis = await overall_timeline_agent.run(
            f"Total estimated hours: {total_hours}\n"
            f"Locations: {raw_data.total_locations}\n"
            f"Cast scheduling: {cast_scheduling}"
        )
        timeline_breakdown = overall_analysis.output
        timeline_breakdown.scene_timelines = scene_timelines
        timeline_breakdown.cast_scheduling = cast_scheduling
        return timeline_breakdown
    except Exception as e:
        print(f"Overall timeline analysis failed: {e}")
        return _create_fallback_timeline_breakdown(scene_timelines, cast_scheduling, raw_data)
    
def _create_fallback_scene_timeline(scene: SceneData) -> SceneTimelineBreakdown:
    """Create fallback scene timeline estimation"""
    base_shoot_time = max(2, int(scene.estimated_pages * 2))
    setup_time = 2
    
    if scene.special_requirements:
        base_shoot_time *= 2
        setup_time += 2
    
    priority = "High" if scene.special_requirements else "Medium"
    crew_requirements = ["Director", "DP", "Sound", "Gaffer"]
    
    return SceneTimelineBreakdown(
        scene_number=scene.scene_number,
        estimated_shoot_time=base_shoot_time,
        setup_time=setup_time,
        crew_requirements=crew_requirements,
        scheduling_priority=priority
    )

def _create_fallback_timeline_breakdown(scene_timelines: List[SceneTimelineBreakdown], 
                                      cast_scheduling: Dict[str, List[int]], 
                                      raw_data: RawScriptData) -> TimelineBreakdown:
    """Create fallback overall timeline estimation"""
    total_hours = sum(st.estimated_shoot_time + st.setup_time for st in scene_timelines)
    total_days = max(1, total_hours // 8)
    
    # Group scenes by location
    location_groups = {}
    for scene in raw_data.scenes:
        if scene.location not in location_groups:
            location_groups[scene.location] = []
        location_groups[scene.location].append(scene.scene_number)
    
    shooting_schedule = [f"Shoot scenes {scenes} at {loc}" 
                        for loc, scenes in location_groups.items()]
    
    pre_production_timeline = [
        "Week 1-2: Pre-production planning",
        "Week 3-4: Location scouting and casting",
        "Week 5-6: Final preparations"
    ]
    
    post_production_timeline = [
        "Week 1-4: Editing",
        "Week 5-6: Sound and color",
        "Week 7-8: Final delivery"
    ]
    
    return TimelineBreakdown(
        scene_timelines=scene_timelines,
        total_shooting_days=total_days,
        shooting_schedule_by_location=shooting_schedule,
        cast_scheduling=cast_scheduling,
        pre_production_timeline=pre_production_timeline,
        post_production_timeline=post_production_timeline
    )