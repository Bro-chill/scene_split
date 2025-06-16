from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class SceneCostBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    location_cost_category: str = Field(description='Low/Medium/High location cost')
    equipment_needs: List[str] = Field(description='Equipment needed for this scene')
    crew_size_needed: str = Field(description='Minimal/Standard/Large crew requirement')
    estimated_shoot_hours: int = Field(description='Estimated shooting hours')
    complexity_factors: List[str] = Field(description='Factors affecting cost/complexity')

class CostBreakdown(BaseModel):
    scene_costs: List[SceneCostBreakdown] = Field(description='Cost breakdown per scene')
    total_budget_range: str = Field(description='Low/Medium/High/Premium budget category')
    estimated_total_days: int = Field(description='Total estimated shooting days')
    major_cost_drivers: List[str] = Field(description='Top factors driving overall costs')
    cost_optimization_tips: List[str] = Field(description='Specific ways to reduce costs')

scene_cost_agent = Agent(
    model,
    output_type=SceneCostBreakdown,
    system_prompt="""Analyze production costs for this scene considering location, 
    equipment, crew, and special requirements. Provide realistic cost assessments."""
)

overall_cost_agent = Agent(
    model,
    output_type=CostBreakdown,
    system_prompt="""Analyze overall production costs and provide actionable 
    cost optimization strategies."""
)

async def analyze_costs(raw_data: RawScriptData) -> CostBreakdown:
    """Analyze costs scene by scene and overall"""
    scene_costs = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_cost_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Location: {scene.location} ({scene.scene_type})\n"
                f"Characters: {', '.join(scene.characters_present)}\n"
                f"Special: {', '.join(scene.special_requirements)}"
            )
            scene_cost = scene_analysis.output
            scene_cost.scene_number = scene.scene_number
            scene_costs.append(scene_cost)
        except Exception as e:
            print(f"Cost analysis failed for scene {scene.scene_number}: {e}")
            scene_costs.append(_create_fallback_scene_cost(scene))
    
    try:
        overall_analysis = await overall_cost_agent.run(
            f"Total scenes: {raw_data.total_scene_count}\n"
            f"Locations: {', '.join(raw_data.total_locations)}\n"
            f"Scene costs: {[sc.location_cost_category for sc in scene_costs]}"
        )
        cost_breakdown = overall_analysis.output
        cost_breakdown.scene_costs = scene_costs
        return cost_breakdown
    except Exception as e:
        print(f"Overall cost analysis failed: {e}")
        return _create_fallback_cost_breakdown(scene_costs, raw_data)

def _create_fallback_scene_cost(scene: SceneData) -> SceneCostBreakdown:
    """Create fallback scene cost estimation"""
    location_cost = "High" if scene.scene_type == "EXT" or scene.special_requirements else "Medium"
    
    equipment_needs = ["Camera", "Lighting", "Sound"]
    if scene.scene_type == "EXT":
        equipment_needs.extend(["Generator", "Weather protection"])
    
    crew_size = "Large" if scene.special_requirements else "Standard"
    shoot_hours = max(2, int(scene.estimated_pages * 2))
    complexity = scene.special_requirements or ["Standard dialogue scene"]
    
    return SceneCostBreakdown(
        scene_number=scene.scene_number,
        location_cost_category=location_cost,
        equipment_needs=equipment_needs,
        crew_size_needed=crew_size,
        estimated_shoot_hours=shoot_hours,
        complexity_factors=complexity
    )

def _create_fallback_cost_breakdown(scene_costs: List[SceneCostBreakdown], 
                                  raw_data: RawScriptData) -> CostBreakdown:
    """Create fallback overall cost estimation"""
    total_hours = sum(sc.estimated_shoot_hours for sc in scene_costs)
    total_days = max(1, total_hours // 8)
    
    high_cost_scenes = len([sc for sc in scene_costs if sc.location_cost_category == "High"])
    budget_range = "High" if high_cost_scenes > len(scene_costs) // 2 else "Medium"
    
    major_cost_drivers = ["Location rentals", "Equipment", "Crew", "Talent", "Post-production"]
    optimization_tips = ["Group scenes by location", "Use natural lighting when possible"]
    
    return CostBreakdown(
        scene_costs=scene_costs,
        total_budget_range=budget_range,
        estimated_total_days=total_days,
        major_cost_drivers=major_cost_drivers,
        cost_optimization_tips=optimization_tips
    )