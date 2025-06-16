from pydantic_ai import Agent
from pydantic import BaseModel, Field
from typing import List, Dict
from dataclasses import dataclass
import sys
import os
import re
from datetime import datetime
from agents.pdf_utils import extract_text_from_pdf, validate_script_content
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model

model = get_model()

@dataclass
class ScriptContext:
    analysis_timestamp: datetime = None
    
    def __post_init__(self):
        if self.analysis_timestamp is None:
            self.analysis_timestamp = datetime.now()

class SceneData(BaseModel):
    scene_number: int = Field(description='Scene sequence number')
    scene_header: str = Field(description='Complete scene header line')
    location: str = Field(description='Scene location name')
    time_of_day: str = Field(description='Time of day (DAY/NIGHT/DAWN/DUSK)')
    scene_type: str = Field(description='Interior or Exterior (INT/EXT)')
    characters_present: List[str] = Field(description='Characters appearing in this scene')
    dialogue_lines: List[str] = Field(description='Sample dialogue lines from this scene')
    action_lines: List[str] = Field(description='Action/description lines from this scene')
    estimated_pages: float = Field(description='Estimated page count for this scene')
    props_mentioned: List[str] = Field(description='Props explicitly mentioned in scene')
    special_requirements: List[str] = Field(description='Special effects, stunts, or technical requirements')

class RawScriptData(BaseModel):
    scenes: List[SceneData] = Field(description='List of all scenes with their detailed data')
    total_characters: List[str] = Field(description='All unique characters across the script')
    total_locations: List[str] = Field(description='All unique locations across the script')
    locations_by_type: Dict[str, List[str]] = Field(description='Locations grouped by INT/EXT')
    language_detected: str = Field(description='Primary language detected')
    estimated_total_pages: float = Field(description='Total estimated page count')
    total_scene_count: int = Field(description='Number of scenes detected')

scene_analysis_agent = Agent(
    model,
    output_type=SceneData,
    system_prompt="""Extract scene data: header details, characters, dialogue samples, 
    action lines, props mentioned, and special requirements. Be precise and thorough.""",
    deps_type=ScriptContext,
    retries=2
)

async def extract_script_data_from_file(file_path: str) -> RawScriptData:
    """Extract raw data from script file (PDF or text)"""
    try:
        file_path = Path(file_path)
        print(f"📄 Processing file: {file_path.name}")
        
        # Determine file type and extract content
        if file_path.suffix.lower() == '.pdf':
            print("🔍 Extracting text from PDF...")
            script_content = extract_text_from_pdf(str(file_path))
            
            # Validate extracted content
            if not validate_script_content(script_content):
                print("⚠️ Warning: Extracted content may not be a valid script format")
            
        elif file_path.suffix.lower() in ['.txt', '.fountain']:
            print("📝 Reading text file...")
            with open(file_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")
        
        print(f"✅ Successfully extracted {len(script_content)} characters")
        
        # Use existing extraction logic
        return await extract_script_data(script_content)
        
    except Exception as e:
        print(f"❌ File processing failed: {e}")
        raise

async def extract_script_data(script_content: str) -> RawScriptData:
    """Extract raw data from script content, organized by scenes"""
    try:
        print(f"📄 Processing script content ({len(script_content)} characters)")
        
        scenes_raw_data = _parse_scenes(script_content)
        print(f"🎬 Found {len(scenes_raw_data)} scenes to process")
        
        processed_scenes = []
        context = ScriptContext()
        
        for i, (scene_text, scene_num) in enumerate(scenes_raw_data):
            print(f"🔍 Processing scene {i+1}/{len(scenes_raw_data)}")
            try:
                limited_scene = scene_text[:2000] if len(scene_text) > 2000 else scene_text
                result = await scene_analysis_agent.run(f"Scene {scene_num + 1}:\n{limited_scene}", deps=context)
                scene_data = result.output
                scene_data.scene_number = scene_num + 1
            except Exception as e:
                print(f"⚠️ AI analysis failed for scene {scene_num + 1}: {e}")
                scene_data = _parse_scene_manual(scene_text, scene_num)
            
            processed_scenes.append(scene_data)
        
        print(f"✅ Successfully processed {len(processed_scenes)} scenes")
        return _aggregate_data(processed_scenes, script_content)
        
    except Exception as e:
        print(f"❌ Scene-based extraction failed: {e}")
        return _fallback_extraction(script_content)

def _parse_scenes(script_content: str) -> List[tuple]:
    """Split script into scenes based on scene headers"""
    lines = script_content.split('\n')
    scenes = []
    current_scene = []
    
    # Enhanced scene header patterns for your script format
    scene_header_patterns = [
        r'^(INT\.?|EXT\.?)\s*\.?\s*\w+\s*-?\s*(DAY|NIGHT|DAWN|DUSK)',  # INT.HOUSE- DAY
        r'^\d+\s*$',  # Standalone numbers like "1", "2", "3"
        r'^(INT\.?|EXT\.?)',  # Any INT./EXT. start
        r'^BABAK\s+\d+:\s*(INT\.?|EXT\.?)',  # Your original pattern
    ]
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check if this line is a scene header
        is_scene_header = any(re.match(pattern, line_stripped, re.IGNORECASE) 
                             for pattern in scene_header_patterns)
        
        # Also check if it's a numbered scene (like "1", "2", "3")
        is_numbered_scene = (line_stripped.isdigit() and 
                           i < len(lines) - 1 and 
                           any(re.match(r'^(INT\.?|EXT\.?)', lines[i+1].strip(), re.IGNORECASE)))
        
        if is_scene_header or is_numbered_scene:
            # Save previous scene if it has content
            if current_scene and any(l.strip() for l in current_scene):
                scenes.append(('\n'.join(current_scene), len(scenes)))
            current_scene = [line]
        else:
            current_scene.append(line)
    
    # Don't forget the last scene
    if current_scene and any(l.strip() for l in current_scene):
        scenes.append(('\n'.join(current_scene), len(scenes)))
    
    print(f"🎬 Parsed {len(scenes)} scenes")
    return scenes

def _parse_scene_manual(scene_text: str, scene_num: int) -> SceneData:
    """Manual parsing of a single scene"""
    lines = scene_text.split('\n')
    
    # Initialize defaults
    scene_header = ""
    location = "UNKNOWN LOCATION"
    time_of_day = "DAY"
    scene_type = "INT"
    characters = set()
    dialogue_lines = []
    action_lines = []
    props_mentioned = []
    special_requirements = []
    
    # Parse scene header
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        babak_match = re.match(r'^BABAK\s+\d+:\s*(INT\.?|EXT\.?)\s*(.+)', line, re.IGNORECASE)
        standard_match = re.match(r'^(INT\.?|EXT\.?)\s+(.+)', line, re.IGNORECASE)
        
        if babak_match or standard_match:
            scene_header = line
            match = babak_match or standard_match
            scene_type = "EXT" if match.group(1).upper().startswith("EXT") else "INT"
            location_time = match.group(2).strip()
            
            # Parse location and time
            for separator in [' – ', ' - ']:
                if separator in location_time:
                    location, time_of_day = location_time.split(separator, 1)
                    location = location.strip()
                    time_of_day = time_of_day.strip().upper()
                    break
            else:
                location = location_time
            break
    
    if not scene_header:
        scene_header = f"BABAK {scene_num + 1}: INT. UNKNOWN LOCATION – DAY"
    
    # Parse content
    excluded_prefixes = ('BABAK', 'INT.', 'EXT.', 'FADE', 'CUT', 'CONTINUE')
    prop_keywords = [
        'gun', 'phone', 'car', 'knife', 'bag', 'laptop', 'camera', 'cup', 'coffee',
        'table', 'chair', 'desk', 'door', 'window', 'book', 'paper', 'pen',
        'telefon', 'kereta', 'meja', 'kerusi', 'pintu', 'tingkap', 'buku',
        'topi', 'komputer', 'radio', 'jam', 'cermin', 'batu', 'bola'
    ]
    special_keywords = [
        'explosion', 'stunt', 'effect', 'buzzes', 'rings', 'crash', 'gunshot',
        'letupan', 'bunyi', 'kemalangan', 'tembakan', 'jeritan'
    ]
    
    for line in lines[1:]:  # Skip header line
        line = line.strip()
        if not line:
            continue
            
        # Detect character names
        if (line.isupper() and len(line.split()) <= 4 and len(line) > 1 and
            not line.startswith(excluded_prefixes)):
            clean_name = re.sub(r'\s*\([^)]*\)', '', line).strip()
            if clean_name:
                characters.add(clean_name)
        
        elif not line.isupper():
            # Detect props
            for prop in prop_keywords:
                if prop.lower() in line.lower():
                    props_mentioned.append(prop)
            
            # Detect special requirements
            if any(special in line.lower() for special in special_keywords):
                special_requirements.append(line)
            
            # Categorize as dialogue or action
            if any(char.lower() in line.lower() for char in characters) or '(' in line:
                if len(dialogue_lines) < 5:
                    dialogue_lines.append(line[:150])
            else:
                if len(action_lines) < 5:
                    action_lines.append(line[:150])
    
    return SceneData(
        scene_number=scene_num + 1,
        scene_header=scene_header,
        location=location,
        time_of_day=time_of_day,
        scene_type=scene_type,
        characters_present=list(characters),
        dialogue_lines=dialogue_lines,
        action_lines=action_lines,
        estimated_pages=max(0.1, len(scene_text.split()) / 250),
        props_mentioned=list(set(props_mentioned)),
        special_requirements=special_requirements
    )

def _aggregate_data(scenes: List[SceneData], script_content: str) -> RawScriptData:
    """Aggregate scene data into overall script statistics"""
    all_characters = set()
    all_locations = set()
    locations_by_type = {"INT": [], "EXT": []}
    
    for scene in scenes:
        all_characters.update(scene.characters_present)
        if scene.location:
            all_locations.add(scene.location)
            if scene.location not in locations_by_type[scene.scene_type]:
                locations_by_type[scene.scene_type].append(scene.location)
    
    # Language detection
    text_lower = script_content.lower()
    malay_indicators = ['yang', 'dan', 'dengan', 'untuk', 'adalah', 'terima kasih']
    english_indicators = ['the', 'and', 'with', 'for', 'is', 'thank you']
    
    malay_count = sum(1 for word in malay_indicators if word in text_lower)
    english_count = sum(1 for word in english_indicators if word in text_lower)
    
    if malay_count > english_count * 1.3:
        language = "Malay"
    elif english_count > malay_count * 1.3:
        language = "English"
    else:
        language = "Mixed/Unknown"
    
    total_pages = sum(scene.estimated_pages for scene in scenes)
    
    print(f"📊 Aggregation complete: {len(all_characters)} characters, {len(all_locations)} locations")
    
    return RawScriptData(
        scenes=scenes,
        total_characters=list(all_characters),
        total_locations=list(all_locations),
        locations_by_type=locations_by_type,
        language_detected=language,
        estimated_total_pages=total_pages,
        total_scene_count=len(scenes)
    )

def _fallback_extraction(script_content: str) -> RawScriptData:
    """Fallback extraction when scene parsing fails"""
    lines = script_content.split('\n')
    characters = set()
    scene_headers = []
    
    excluded_prefixes = ('INT.', 'EXT.', 'FADE', 'CUT', 'DISSOLVE')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Find scene headers
        if (re.match(r'^(INT\.?|EXT\.?)\s+', line, re.IGNORECASE) or
            re.match(r'^BABAK\s+\d+:\s*(INT\.?|EXT\.?)', line, re.IGNORECASE)):
            scene_headers.append(line)
        
        # Find characters
        elif (line.isupper() and len(line.split()) <= 4 and len(line) > 1 and
              not line.startswith(excluded_prefixes)):
            clean_name = re.sub(r'\s*\([^)]*\)', '', line).strip()
            if clean_name:
                characters.add(clean_name)
    
    # Create scenes
    if scene_headers:
        scenes = []
        for i, header in enumerate(scene_headers):
            scene_type = "EXT" if header.upper().startswith("EXT") else "INT"
            
            scene = SceneData(
                scene_number=i + 1,
                scene_header=header,
                location="UNKNOWN LOCATION",
                time_of_day="DAY",
                scene_type=scene_type,
                characters_present=list(characters),
                dialogue_lines=[],
                action_lines=[],
                estimated_pages=max(1.0, len(script_content) / (250 * len(scene_headers))),
                props_mentioned=[],
                special_requirements=[]
            )
            scenes.append(scene)
    else:
        scenes = [SceneData(
            scene_number=1,
            scene_header="INT. UNKNOWN LOCATION - DAY",
            location="UNKNOWN LOCATION",
            time_of_day="DAY",
            scene_type="INT",
            characters_present=list(characters),
            dialogue_lines=[],
            action_lines=[],
            estimated_pages=max(1.0, len(script_content) / 250),
            props_mentioned=[],
            special_requirements=[]
        )]
    
    print(f"🔧 Fallback extraction: {len(scenes)} scenes, {len(characters)} characters")
    
    return RawScriptData(
        scenes=scenes,
        total_characters=list(characters),
        total_locations=["UNKNOWN LOCATION"],
        locations_by_type={"INT": ["UNKNOWN LOCATION"], "EXT": []},
        language_detected="English",
        estimated_total_pages=sum(scene.estimated_pages for scene in scenes),
        total_scene_count=len(scenes)
    )