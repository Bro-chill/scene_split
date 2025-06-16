from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class DetailedSceneBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    scene_purpose: str = Field(description='Narrative purpose of this scene')
    dramatic_weight: str = Field(description='Low/Medium/High dramatic importance')
    emotional_tone: str = Field(description='Emotional tone of the scene')
    action_vs_dialogue_ratio: str = Field(description='Primarily action, dialogue, or balanced')
    production_complexity: str = Field(description='Simple/Moderate/Complex to shoot')

class SceneBreakdown(BaseModel):
    detailed_scenes: List[DetailedSceneBreakdown] = Field(description='Detailed breakdown of each scene')
    three_act_structure: List[str] = Field(description='Scenes grouped by act structure')
    pacing_analysis: str = Field(description='Overall pacing and rhythm assessment')
    key_dramatic_scenes: List[str] = Field(description='Most important scenes for the story')
    action_heavy_scenes: List[str] = Field(description='Scenes requiring complex action/stunts')
    dialogue_heavy_scenes: List[str] = Field(description='Scenes focused on dialogue/character')

scene_breakdown_agent = Agent(
    model,
    output_type=DetailedSceneBreakdown,
    system_prompt="""Analyze this scene's narrative and production elements focusing on 
    story purpose, dramatic importance, and production complexity."""
)

overall_structure_agent = Agent(
    model,
    output_type=SceneBreakdown,
    system_prompt="""Analyze overall script structure and provide comprehensive 
    script analysis for directors and producers."""
)

async def analyze_scenes(raw_data: RawScriptData) -> SceneBreakdown:
    """Analyze scene structure and dramatic elements"""
    detailed_scenes = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_breakdown_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Characters: {', '.join(scene.characters_present)}\n"
                f"Dialogue: {' | '.join(scene.dialogue_lines[:2])}\n"
                f"Special requirements: {', '.join(scene.special_requirements)}"
            )
            detailed_scene = scene_analysis.output
            detailed_scene.scene_number = scene.scene_number
            detailed_scenes.append(detailed_scene)
        except Exception as e:
            print(f"Scene breakdown failed for scene {scene.scene_number}: {e}")
            detailed_scenes.append(_create_fallback_scene_breakdown(scene))
    
    try:
        overall_analysis = await overall_structure_agent.run(
            f"Total scenes: {raw_data.total_scene_count}\n"
            f"Scene complexities: {[ds.production_complexity for ds in detailed_scenes]}\n"
            f"Dramatic weights: {[ds.dramatic_weight for ds in detailed_scenes]}"
        )
        scene_breakdown = overall_analysis.output
        scene_breakdown.detailed_scenes = detailed_scenes
        return scene_breakdown
    except Exception as e:
        print(f"Overall scene analysis failed: {e}")
        return _create_fallback_scene_breakdown_overall(detailed_scenes, raw_data)

def _create_fallback_scene_breakdown(scene: SceneData) -> DetailedSceneBreakdown:
    """Create fallback scene breakdown"""
    # Determine complexity
    complexity = "Simple"
    if scene.special_requirements:
        complexity = "Complex"
    elif len(scene.characters_present) > 3:
        complexity = "Moderate"
    
    # Determine action vs dialogue ratio
    action_ratio = "Balanced"
    if len(scene.dialogue_lines) > len(scene.action_lines):
        action_ratio = "Dialogue-heavy"
    elif scene.special_requirements:
        action_ratio = "Action-heavy"
    
    return DetailedSceneBreakdown(
        scene_number=scene.scene_number,
        scene_purpose="Story progression",
        dramatic_weight="Medium",
        emotional_tone="Neutral",
        action_vs_dialogue_ratio=action_ratio,
        production_complexity=complexity
    )

def _create_fallback_scene_breakdown_overall(detailed_scenes: List[DetailedSceneBreakdown], 
                                           raw_data: RawScriptData) -> SceneBreakdown:
    """Create fallback overall scene analysis"""
    total_scenes = len(detailed_scenes)
    act1_end = total_scenes // 4
    act2_end = total_scenes * 3 // 4
    
    three_act = [
        f"Act 1: Scenes 1-{act1_end}",
        f"Act 2: Scenes {act1_end + 1}-{act2_end}",
        f"Act 3: Scenes {act2_end + 1}-{total_scenes}"
    ]
    
    action_scenes = [f"Scene {ds.scene_number}" for ds in detailed_scenes 
                    if ds.action_vs_dialogue_ratio == "Action-heavy"]
    dialogue_scenes = [f"Scene {ds.scene_number}" for ds in detailed_scenes 
                      if ds.action_vs_dialogue_ratio == "Dialogue-heavy"]
    key_scenes = [f"Scene {ds.scene_number}" for ds in detailed_scenes 
                 if ds.dramatic_weight == "High"]
    
    if not key_scenes:
        key_scenes = [f"Scene {total_scenes // 2}"]
    
    return SceneBreakdown(
        detailed_scenes=detailed_scenes,
        three_act_structure=three_act,
        pacing_analysis="Balanced pacing with mix of action and dialogue",
        key_dramatic_scenes=key_scenes,
        action_heavy_scenes=action_scenes,
        dialogue_heavy_scenes=dialogue_scenes
    )