from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model
from .info_gathering_agent import RawScriptData, SceneData

model = get_model()

class SceneCharacterBreakdown(BaseModel):
    scene_number: int = Field(description='Scene number')
    characters_in_scene: List[str] = Field(description='Characters present in this scene')
    character_interactions: List[str] = Field(description='Key character interactions/relationships shown')
    dialogue_complexity: str = Field(description='Simple/Moderate/Complex dialogue requirements')
    emotional_beats: List[str] = Field(description='Emotional moments for characters in scene')

class CharacterBreakdown(BaseModel):
    scene_characters: List[SceneCharacterBreakdown] = Field(description='Character breakdown per scene')
    main_characters: List[str] = Field(description='Main characters with descriptions')
    supporting_characters: List[str] = Field(description='Supporting characters')
    character_scene_count: Dict[str, int] = Field(description='Number of scenes each character appears in')
    casting_requirements: List[str] = Field(description='Casting specifications for each character')

scene_character_agent = Agent(
    model,
    output_type=SceneCharacterBreakdown,
    system_prompt="""Analyze character dynamics in this scene focusing on interactions, 
    dialogue complexity, and emotional content for casting and directing needs."""
)

overall_character_agent = Agent(
    model,
    output_type=CharacterBreakdown,
    system_prompt="""Analyze overall character requirements across the script for 
    comprehensive casting and character direction guidance."""
)

async def analyze_characters(raw_data: RawScriptData) -> CharacterBreakdown:
    """Analyze characters scene by scene and overall"""
    scene_characters = []
    
    for scene in raw_data.scenes:
        try:
            scene_analysis = await scene_character_agent.run(
                f"Scene {scene.scene_number}: {scene.scene_header}\n"
                f"Characters: {', '.join(scene.characters_present)}\n"
                f"Dialogue: {' | '.join(scene.dialogue_lines[:3])}"
            )
            scene_char = scene_analysis.output
            scene_char.scene_number = scene.scene_number
            scene_characters.append(scene_char)
        except Exception as e:
            print(f"Character analysis failed for scene {scene.scene_number}: {e}")
            scene_characters.append(_create_fallback_scene_character(scene))
    
    # Count character appearances
    char_counts = {}
    for scene in raw_data.scenes:
        for char in scene.characters_present:
            char_counts[char] = char_counts.get(char, 0) + 1
    
    try:
        overall_analysis = await overall_character_agent.run(
            f"Characters and scene counts: {char_counts}\n"
            f"Total scenes: {raw_data.total_scene_count}"
        )
        character_breakdown = overall_analysis.output
        character_breakdown.scene_characters = scene_characters
        character_breakdown.character_scene_count = char_counts
        return character_breakdown
    except Exception as e:
        print(f"Overall character analysis failed: {e}")
        return _create_fallback_character_breakdown(scene_characters, char_counts, raw_data)

def _create_fallback_scene_character(scene: SceneData) -> SceneCharacterBreakdown:
    """Create fallback scene character analysis"""
    interactions = []
    if len(scene.characters_present) > 1:
        interactions = [f"Interaction between {', '.join(scene.characters_present)}"]
    
    emotional_beats = []
    if scene.dialogue_lines:
        emotional_beats = ["Character development moment"]
    
    return SceneCharacterBreakdown(
        scene_number=scene.scene_number,
        characters_in_scene=scene.characters_present,
        character_interactions=interactions,
        dialogue_complexity="Moderate",
        emotional_beats=emotional_beats
    )

def _create_fallback_character_breakdown(scene_characters: List[SceneCharacterBreakdown], 
                                       char_counts: Dict[str, int], 
                                       raw_data: RawScriptData) -> CharacterBreakdown:
    """Create fallback overall character analysis"""
    total_scenes = raw_data.total_scene_count
    main_threshold = total_scenes * 0.3
    
    main_chars = [f"{char} - appears in {char_counts[char]} scenes" 
                  for char, count in char_counts.items() if count > main_threshold]
    supporting_chars = [f"{char} - appears in {char_counts[char]} scenes" 
                       for char, count in char_counts.items() if count <= main_threshold]
    casting_requirements = [f"Cast {char} - {char_counts[char]} scenes" 
                           for char in raw_data.total_characters]
    
    return CharacterBreakdown(
        scene_characters=scene_characters,
        main_characters=main_chars,
        supporting_characters=supporting_chars,
        character_scene_count=char_counts,
        casting_requirements=casting_requirements
    )