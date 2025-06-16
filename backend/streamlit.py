import streamlit as st
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict

from graph.workflow import run_analyze_script_workflow
from agents.pdf_utils import extract_text_from_pdf, validate_script_content

# Configure page
st.set_page_config(
    page_title="Script Analysis Tool",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS styles
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; color: #1f77b4; text-align: center; margin-bottom: 2rem; }
    .error-message { background-color: #ffe6e6; color: #d63384; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #d63384; }
    .success-message { background-color: #e6ffe6; color: #198754; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #198754; }
    .progress-container { background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    .analysis-status { display: flex; align-items: center; margin-bottom: 0.5rem; }
    .status-pending { color: #6c757d; }
    .status-running { color: #fd7e14; }
    .status-complete { color: #198754; }
    .status-error { color: #dc3545; }
    .file-upload-section { background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; }
</style>
""", unsafe_allow_html=True)

# Utility functions
def safe_get(obj, attr, default=None):
    """Safely get attribute with fallback"""
    return getattr(obj, attr, default) if obj else default

def display_metrics(data, metrics_config):
    """Display metrics in columns"""
    cols = st.columns(len(metrics_config))
    for i, (label, getter, default) in enumerate(metrics_config):
        with cols[i]:
            value = getter(data) if callable(getter) else safe_get(data, getter, default)
            st.metric(label, value)

def display_list(items, title, max_show=5):
    """Display list with optional expansion"""
    if not items:
        return
    
    st.markdown(f"#### {title}")
    for item in items[:max_show]:
        st.write(f"• {item}")
    
    if len(items) > max_show:
        st.info(f"... and {len(items) - max_show} more items")

def display_scenes(scenes, title, max_show=5):
    """Display scene breakdown"""
    if not scenes:
        return
    
    st.markdown(f"#### {title}")
    for scene in scenes[:max_show]:
        scene_num = safe_get(scene, 'scene_number', 'N/A')
        with st.expander(f"Scene {scene_num}"):
            attrs = ['scene_purpose', 'dramatic_weight', 'emotional_tone', 'production_complexity',
                    'location_cost_category', 'crew_size_needed', 'estimated_shoot_hours',
                    'props_needed', 'costume_requirements', 'setup_complexity', 'permit_needed']
            
            for attr in attrs:
                value = safe_get(scene, attr)
                if value:
                    label = attr.replace('_', ' ').title()
                    if isinstance(value, list):
                        st.write(f"**{label}:** {', '.join(map(str, value))}")
                    else:
                        st.write(f"**{label}:** {value}")
    
    if len(scenes) > max_show:
        st.info(f"... and {len(scenes) - max_show} more scenes")

# File processing functions
def extract_script_content(uploaded_file, input_method):
    """Extract script content from uploaded file or text input"""
    try:
        if input_method == "Upload PDF" and uploaded_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_file_path = temp_file.name
            
            try:
                # Extract text from PDF
                script_content = extract_text_from_pdf(temp_file_path)
                
                # Validate content
                if not validate_script_content(script_content):
                    st.warning("⚠️ The extracted content may not be in standard script format. Analysis will proceed but results may vary.")
                
                return script_content, uploaded_file.name
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        elif input_method == "Upload Text File" and uploaded_file is not None:
            # Handle text file upload
            content = uploaded_file.getvalue()
            
            # Try to decode as UTF-8, fallback to other encodings
            try:
                script_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    script_content = content.decode('latin-1')
                except UnicodeDecodeError:
                    script_content = content.decode('utf-8', errors='ignore')
                    st.warning("⚠️ Some characters may not have been decoded correctly.")
            
            return script_content, uploaded_file.name
            
        else:
            return None, None
            
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        return None, None

def show_file_info(filename, script_content):
    """Display information about the uploaded file"""
    if filename and script_content:
        st.markdown('<div class="file-upload-section">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 File", filename)
        with col2:
            st.metric("📝 Characters", f"{len(script_content):,}")
        with col3:
            word_count = len(script_content.split())
            st.metric("📊 Words", f"{word_count:,}")
        
        # Show preview
        with st.expander("📖 Script Preview (First 500 characters)"):
            preview = script_content[:500]
            if len(script_content) > 500:
                preview += "..."
            st.text(preview)
        
        st.markdown('</div>', unsafe_allow_html=True)

# Analysis display functions (keeping all existing functions)
def show_script_overview(raw_data):
    """Display script overview"""
    if not raw_data:
        return
    
    st.markdown("### 📊 Script Overview")
    
    metrics = [
        ("Total Scenes", lambda x: len(safe_get(x, 'scenes', [])), 0),
        ("Characters", lambda x: len(safe_get(x, 'total_characters', [])), 0),
        ("Locations", lambda x: len(safe_get(x, 'total_locations', [])), 0),
        ("Est. Pages", lambda x: f"{safe_get(x, 'estimated_total_pages', 0):.1f}", "0.0")
    ]
    display_metrics(raw_data, metrics)
    
    col1, col2 = st.columns(2)
    with col1:
        language = safe_get(raw_data, 'language_detected', 'Unknown')
        st.info(f"**Language:** {language}")
    
    with col2:
        locations_by_type = safe_get(raw_data, 'locations_by_type', {})
        if locations_by_type:
            int_count = len(locations_by_type.get('INT', []))
            ext_count = len(locations_by_type.get('EXT', []))
            st.info(f"**Scene Types:** {int_count} INT, {ext_count} EXT")

def show_cost_analysis(cost_analysis):
    """Display cost analysis"""
    st.markdown("### 💰 Cost Analysis")
    if not cost_analysis:
        st.warning("No cost analysis data available")
        return
    
    metrics = [
        ("Budget Range", 'total_budget_range', 'N/A'),
        ("Shoot Days", 'estimated_total_days', 'N/A'),
        ("Scene Costs", lambda x: len(safe_get(x, 'scene_costs', [])), 0)
    ]
    display_metrics(cost_analysis, metrics)
    
    scene_costs = safe_get(cost_analysis, 'scene_costs', [])
    display_scenes(scene_costs, "📋 Scene Cost Breakdown")
    
    tips = safe_get(cost_analysis, 'cost_optimization_tips', [])
    display_list(tips, "💡 Cost Optimization Tips")

def show_props_analysis(props_analysis):
    """Display props analysis"""
    st.markdown("### 🎭 Props Analysis")
    if not props_analysis:
        st.warning("No props analysis data available")
        return
    
    metrics = [
        ("Total Props", lambda x: len(safe_get(x, 'master_props_list', [])), 0),
        ("Scene Breakdowns", lambda x: len(safe_get(x, 'scene_props', [])), 0),
        ("Budget Estimate", 'prop_budget_estimate', 'N/A')
    ]
    display_metrics(props_analysis, metrics)
    
    props_by_category = safe_get(props_analysis, 'props_by_category', {})
    if props_by_category:
        st.markdown("#### 📦 Props by Category")
        for category, props in props_by_category.items():
            if props:
                with st.expander(f"{category.title()} ({len(props)} items)"):
                    for prop in props:
                        st.write(f"• {prop}")
    
    scene_props = safe_get(props_analysis, 'scene_props', [])
    display_scenes(scene_props, "🎬 Props by Scene")

def show_location_analysis(location_analysis):
    """Display location analysis"""
    st.markdown("### 📍 Location Analysis")
    if not location_analysis:
        st.warning("No location analysis data available")
        return
    
    metrics = [
        ("Unique Locations", lambda x: len(safe_get(x, 'unique_locations', [])), 0),
        ("Scene Breakdowns", lambda x: len(safe_get(x, 'scene_locations', [])), 0),
        ("Permits Needed", lambda x: len(safe_get(x, 'permit_requirements', [])), 0)
    ]
    display_metrics(location_analysis, metrics)
    
    locations_by_type = safe_get(location_analysis, 'locations_by_type', {})
    if locations_by_type:
        col1, col2 = st.columns(2)
        with col1:
            display_list(locations_by_type.get('INT', []), "🏠 Interior Locations")
        with col2:
            display_list(locations_by_type.get('EXT', []), "🌍 Exterior Locations")
    
    scene_locations = safe_get(location_analysis, 'scene_locations', [])
    display_scenes(scene_locations, "📍 Location by Scene")
    
    shooting_groups = safe_get(location_analysis, 'location_shooting_groups', [])
    display_list(shooting_groups, "📅 Recommended Shooting Groups")

def show_character_analysis(character_analysis):
    """Display character analysis"""
    st.markdown("### 👥 Character Analysis")
    if not character_analysis:
        st.warning("No character analysis data available")
        return
    
    metrics = [
        ("Main Characters", lambda x: len(safe_get(x, 'main_characters', [])), 0),
        ("Supporting Characters", lambda x: len(safe_get(x, 'supporting_characters', [])), 0),
        ("Scene Breakdowns", lambda x: len(safe_get(x, 'scene_characters', [])), 0)
    ]
    display_metrics(character_analysis, metrics)
    
    char_scene_count = safe_get(character_analysis, 'character_scene_count', {})
    if char_scene_count:
        st.markdown("#### 📊 Character Appearances")
        sorted_chars = sorted(char_scene_count.items(), key=lambda x: x[1], reverse=True)
        for char, count in sorted_chars:
            st.write(f"**{char}:** {count} scenes")
    
    col1, col2 = st.columns(2)
    with col1:
        main_chars = safe_get(character_analysis, 'main_characters', [])
        display_list(main_chars, "⭐ Main Characters")
    with col2:
        supporting_chars = safe_get(character_analysis, 'supporting_characters', [])
        display_list(supporting_chars, "🎭 Supporting Characters")
    
    scene_characters = safe_get(character_analysis, 'scene_characters', [])
    display_scenes(scene_characters, "👥 Characters by Scene")

def show_scene_analysis(scene_analysis):
    """Display scene analysis"""
    st.markdown("### 🎬 Scene Analysis")
    if not scene_analysis:
        st.warning("No scene analysis data available")
        return
    
    detailed_scenes = safe_get(scene_analysis, 'detailed_scenes', [])
    
    metrics = [
        ("Total Scenes", lambda x: len(detailed_scenes), 0),
        ("Action Scenes", lambda x: len(safe_get(x, 'action_heavy_scenes', [])), 0),
        ("Dialogue Scenes", lambda x: len(safe_get(x, 'dialogue_heavy_scenes', [])), 0)
    ]
    display_metrics(scene_analysis, metrics)
    
    three_act = safe_get(scene_analysis, 'three_act_structure', [])
    display_list(three_act, "📖 Three-Act Structure")
    
    key_scenes = safe_get(scene_analysis, 'key_dramatic_scenes', [])
    display_list(key_scenes, "⭐ Key Dramatic Scenes")
    
    display_scenes(detailed_scenes, "🎬 Detailed Scene Breakdown")

def show_timeline_analysis(timeline_analysis):
    """Display timeline analysis"""
    st.markdown("### ⏰ Timeline Analysis")
    if not timeline_analysis:
        st.warning("No timeline analysis data available")
        return
    
    metrics = [
        ("Total Shooting Days", 'total_shooting_days', 0),
        ("Scene Timelines", lambda x: len(safe_get(x, 'scene_timelines', [])), 0),
        ("Characters Scheduled", lambda x: len(safe_get(x, 'cast_scheduling', {})), 0)
    ]
    display_metrics(timeline_analysis, metrics)
    
    shooting_schedule = safe_get(timeline_analysis, 'shooting_schedule_by_location', [])
    display_list(shooting_schedule, "📅 Recommended Shooting Schedule")
    
    cast_scheduling = safe_get(timeline_analysis, 'cast_scheduling', {})
    if cast_scheduling:
        st.markdown("#### 👥 Cast Scheduling")
        for character, scenes in cast_scheduling.items():
            if isinstance(scenes, list):
                scene_list = ", ".join(map(str, scenes))
                st.write(f"**{character}:** Scenes {scene_list}")
    
    scene_timelines = safe_get(timeline_analysis, 'scene_timelines', [])
    display_scenes(scene_timelines, "⏱️ Scene Timeline Breakdown")
    
    col1, col2 = st.columns(2)
    with col1:
        pre_production = safe_get(timeline_analysis, 'pre_production_timeline', [])
        display_list(pre_production, "📋 Pre-Production Timeline")
    with col2:
        post_production = safe_get(timeline_analysis, 'post_production_timeline', [])
        display_list(post_production, "🎞️ Post-Production Timeline")

# Progress tracking
def show_progress():
    """Display analysis progress"""
    steps = [
        ("📊 Script Parsing", "raw_data"),
        ("💰 Cost Analysis", "cost_analysis"),
        ("🎭 Props Analysis", "props_analysis"),
        ("📍 Location Analysis", "location_analysis"),
        ("👥 Character Analysis", "character_analysis"),
        ("🎬 Scene Analysis", "scene_analysis"),
        ("⏰ Timeline Analysis", "timeline_analysis")
    ]
    
    if 'analysis_progress' not in st.session_state:
        st.session_state.analysis_progress = {step[1]: 'pending' for step in steps}
    
    st.markdown('<div class="progress-container">', unsafe_allow_html=True)
    st.markdown("### 🔄 Analysis Progress")
    
    status_icons = {
        'pending': ("⏳", "status-pending", "Waiting..."),
        'running': ("🔄", "status-running", "Running..."),
        'complete': ("✅", "status-complete", "Complete"),
        'error': ("❌", "status-error", "Error")
    }
    
    for step_name, step_key in steps:
        status = st.session_state.analysis_progress.get(step_key, 'pending')
        icon, css_class, status_text = status_icons.get(status, status_icons['pending'])
        
        st.markdown(f'''
        <div class="analysis-status">
            <span class="{css_class}">{icon}</span>
            <span><strong>{step_name}:</strong> {status_text}</span>
        </div>
        ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    completed = sum(1 for status in st.session_state.analysis_progress.values() if status == 'complete')
    total = len(steps)
    st.progress(completed / total)
    st.caption(f"Progress: {completed}/{total} analyses complete")

def update_progress(step_key, status):
    """Update progress for a step"""
    if 'analysis_progress' not in st.session_state:
        st.session_state.analysis_progress = {}
    st.session_state.analysis_progress[step_key] = status

async def run_workflow_with_progress(script_content: str, human_feedback: Optional[Dict] = None):
    """Run workflow with progress updates"""
    try:
        update_progress('raw_data', 'running')
        await asyncio.sleep(0.1)
        
        result = await run_analyze_script_workflow(script_content, human_feedback)
        
        # Mark all steps as complete
        steps = ['raw_data', 'cost_analysis', 'props_analysis', 'location_analysis', 
                'character_analysis', 'scene_analysis', 'timeline_analysis']
        
        for step in steps:
            update_progress(step, 'complete')
            await asyncio.sleep(0.1)
        
        return result, None
        
    except Exception as e:
        # Mark running steps as error
        for key, status in st.session_state.analysis_progress.items():
            if status == 'running':
                update_progress(key, 'error')
        return None, str(e)

def run_analysis(script_content: str, human_feedback: Optional[Dict] = None):
    """Run analysis synchronously"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_workflow_with_progress(script_content, human_feedback))
        loop.close()
        return result
    except Exception as e:
        return None, str(e)

def collect_feedback():
    """Collect user feedback for revisions"""
    st.markdown("## 👤 Human Review")
    st.markdown("Review each analysis above. Check boxes and provide feedback for any revisions needed:")
    
    analysis_types = ["cost", "props", "location", "character", "scene", "timeline"]
    needs_revision = {}
    feedback = {}
    
    for analysis_type in analysis_types:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            needs_revision[analysis_type] = st.checkbox(
                f"Revise {analysis_type.title()}", 
                key=f"revise_{analysis_type}"
            )
        
        with col2:
            if needs_revision[analysis_type]:
                feedback[analysis_type] = st.text_area(
                    f"Feedback for {analysis_type}:",
                    key=f"feedback_{analysis_type}",
                    placeholder=f"What changes would you like to see in the {analysis_type} analysis?"
                )
            else:
                feedback[analysis_type] = ""
    
    return needs_revision, feedback

def get_sample_script():
    """Return sample script content"""
    return """
INT. COFFEE SHOP - DAY

SARAH, 25, sits at a corner table with her laptop. She nervously checks her phone.

SARAH
(into phone)
I can't do this anymore, Mom. The pressure is killing me.

The BARISTA, 20s, approaches with a steaming cup.

BARISTA
One large coffee, extra shot.

SARAH
Thanks.

Sarah's phone BUZZES. She looks at the screen - "BOSS CALLING"

SARAH (CONT'D)
(answering)
Hello, Mr. Peterson?

CUT TO:

EXT. CITY STREET - DAY

MIKE, 30, walks briskly down the sidewalk, talking on his phone.

MIKE
The deal fell through. We need a backup plan.

A BLACK SUV pulls up beside him. Two MEN in suits get out.

MIKE (CONT'D)
(panicked)
I have to go.

Mike hangs up and starts running.
"""

def main():
    """Main application"""
    
    # Initialize session state
    for key in ['analysis_result', 'review_mode', 'analysis_running', 'script_content', 'filename']:
        if key not in st.session_state:
            st.session_state[key] = False if 'running' in key or 'mode' in key else None
    
    # Header
    st.markdown('<h1 class="main-header">🎬 Script Analysis Tool</h1>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 📝 Script Input")
        
        # Input method selection
        input_method = st.radio(
            "Choose input method:",
            ["Type/Paste Text", "Upload PDF", "Upload Text File", "Use Sample Script"],
            index=0
        )
        
        script_content = None
        filename = None
        
        if input_method == "Upload PDF":
            st.markdown("### 📄 Upload PDF Script")
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Upload a PDF file containing your script"
            )
            
            if uploaded_file is not None:
                with st.spinner("🔍 Extracting text from PDF..."):
                    script_content, filename = extract_script_content(uploaded_file, input_method)
                
                if script_content:
                    st.success(f"✅ Successfully extracted text from {filename}")
                    # Show file info
                    show_file_info(filename, script_content)
                else:
                    st.error("❌ Failed to extract text from PDF")
        
        elif input_method == "Upload Text File":
            st.markdown("### 📝 Upload Text Script")
            uploaded_file = st.file_uploader(
                "Choose a text file",
                type=['txt', 'fountain'],
                help="Upload a .txt or .fountain file containing your script"
            )
            
            if uploaded_file is not None:
                script_content, filename = extract_script_content(uploaded_file, input_method)
                
                if script_content:
                    st.success(f"✅ Successfully loaded {filename}")
                    # Show file info
                    show_file_info(filename, script_content)
                else:
                    st.error("❌ Failed to read text file")
        
        elif input_method == "Use Sample Script":
            script_content = get_sample_script()
            filename = "sample_script.txt"
            st.text_area("Sample Script Content", value=script_content, height=200, disabled=True)
            
        else:  # Type/Paste Text
            script_content = st.text_area(
                "Paste your script here:",
                height=300,
                placeholder="Enter your script content here..."
            )
            if script_content:
                filename = "pasted_script.txt"
        
        # Button logic
        if not st.session_state.review_mode and not st.session_state.analysis_running:
            analyze_button = st.button(
                "🚀 Analyze Script", 
                type="primary", 
                use_container_width=True,
                disabled=not script_content or not script_content.strip()
            )
        elif st.session_state.analysis_running:
            st.info("🔄 Analysis in progress...")
            if st.button("❌ Cancel Analysis", use_container_width=True):
                st.session_state.analysis_running = False
                st.session_state.analysis_progress = {}
                st.rerun()
        else:
            st.info("📋 Review the results below and provide feedback if needed.")
            if st.button("🔄 Start New Analysis", use_container_width=True):
                for key in ['analysis_result', 'review_mode', 'analysis_running', 'analysis_progress', 'script_content', 'filename']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        # Show current file info in sidebar
        if st.session_state.get('filename'):
            st.markdown("---")
            st.markdown("### 📄 Current File")
            st.info(f"**File:** {st.session_state.filename}")
            if st.session_state.get('script_content'):
                word_count = len(st.session_state.script_content.split())
                st.info(f"**Words:** {word_count:,}")
    
    # Main content logic
    if (not st.session_state.review_mode and not st.session_state.analysis_running and 
        'analyze_button' in locals() and analyze_button and script_content and script_content.strip()):
        
        st.session_state.analysis_running = True
        st.session_state.script_content = script_content
        st.session_state.filename = filename
        st.rerun()
    
    elif st.session_state.analysis_running:
        # Show file info during analysis
        if st.session_state.get('filename') and st.session_state.get('script_content'):
            show_file_info(st.session_state.filename, st.session_state.script_content)
            st.markdown("---")
        
        show_progress()
        
        result, error = run_analysis(st.session_state.script_content)
        
        if error:
            st.markdown(f'<div class="error-message">❌ Error: {error}</div>', unsafe_allow_html=True)
            st.session_state.analysis_running = False
            return
        
        if not result:
            st.markdown('<div class="error-message">❌ No results returned from analysis</div>', unsafe_allow_html=True)
            st.session_state.analysis_running = False
            return
        
        st.session_state.analysis_result = result
        st.session_state.review_mode = True
        st.session_state.analysis_running = False
        st.rerun()
    
    elif st.session_state.review_mode and st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        # Show file info at top of results
        if st.session_state.get('filename') and st.session_state.get('script_content'):
            show_file_info(st.session_state.filename, st.session_state.script_content)
            st.markdown("---")
        
        st.markdown('<div class="success-message">✅ Analysis completed! Please review the results below.</div>', unsafe_allow_html=True)
        
        # Show overview
        if result.raw_data:
            show_script_overview(result.raw_data)
            st.markdown("---")
        
        # Show analysis tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "💰 Cost", "🎭 Props", "📍 Locations", 
            "👥 Characters", "🎬 Scenes", "⏰ Timeline"
        ])
        
        with tab1:
            show_cost_analysis(result.cost_analysis)
        with tab2:
            show_props_analysis(result.props_analysis)
        with tab3:
            show_location_analysis(result.location_analysis)
        with tab4:
            show_character_analysis(result.character_analysis)
        with tab5:
            show_scene_analysis(result.scene_analysis)
        with tab6:
            show_timeline_analysis(result.timeline_analysis)
        
        # Review section
        st.markdown("---")
        needs_revision, feedback = collect_feedback()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Approve All", type="primary", use_container_width=True):
                st.success("🎉 All analyses approved! Analysis complete.")
                st.session_state.review_mode = False
                st.balloons()
        
        with col2:
            any_revisions = any(needs_revision.values())
            if any_revisions and st.button("🔄 Submit Revisions", type="secondary", use_container_width=True):
                missing_feedback = [analysis_type for analysis_type, needs_rev in needs_revision.items() 
                                  if needs_rev and not feedback[analysis_type].strip()]
                
                if missing_feedback:
                    st.error(f"Please provide feedback for: {', '.join(missing_feedback)}")
                else:
                    human_feedback = {
                        'needs_revision': needs_revision,
                        'feedback': feedback
                    }
                    st.session_state.analysis_running = True
                    st.session_state.human_feedback = human_feedback
                    st.rerun()
        
        with col3:
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state.analysis_result = None
                st.session_state.review_mode = False
                st.rerun()
        
        if any_revisions:
            revision_list = [analysis_type.title() for analysis_type, needs_rev in needs_revision.items() if needs_rev]
            st.info(f"📝 Revisions requested for: {', '.join(revision_list)}")
    
    elif ('analyze_button' in locals() and analyze_button and 
          (not script_content or not script_content.strip())):
        st.warning("⚠️ Please provide a script to analyze")
    
    else:
        # Welcome screen
        st.markdown("""
        ## Welcome to the Script Analysis Tool! 🎬
        
        This tool provides comprehensive **scene-by-scene analysis** of your screenplay including:
        
        - **📊 Script Overview**: Scene count, characters, locations, and structure
        - **💰 Cost Analysis**: Budget estimates with scene-level cost breakdowns
        - **🎭 Props Analysis**: Categorized props with scene-specific requirements
        - **📍 Location Analysis**: Location breakdown with shooting group recommendations
        - **👥 Character Analysis**: Character appearances and scene-by-scene presence
        - **🎬 Scene Analysis**: Detailed scene breakdown with dramatic structure
        - **⏰ Timeline Analysis**: Scene-level scheduling with production timelines
        
        ### How to use:
        1. **Choose your input method** in the sidebar:
           - **📄 Upload PDF**: Upload a PDF script file (most common)
           - **📝 Upload Text File**: Upload .txt or .fountain files
           - **✏️ Type/Paste Text**: Directly paste script content
           - **📋 Use Sample Script**: Try with our sample script
        
        2. **Upload or enter your script** using your chosen method
        
        3. **Click "Analyze Script"** to get comprehensive scene-by-scene breakdowns
        
        4. **Watch real-time progress** as each analysis component completes
        
        5. **Review detailed results** organized by analysis type in tabs
        
        6. **Provide feedback** for any analysis you want revised
        
        7. **Approve or request revisions** for specific analyses
        
        ### Supported File Formats:
        - **PDF files** (.pdf) - Automatically extracts text from script PDFs
        - **Text files** (.txt) - Plain text script files
        - **Fountain files** (.fountain) - Fountain markup format
        - **Direct text input** - Copy and paste script content
        
        ### Features:
        - **PDF Text Extraction**: Advanced PDF processing with multiple extraction methods
        - **Content Validation**: Automatically detects if content looks like a script
        - **File Information**: Shows file details, character count, and preview
        - **Progress Tracking**: Real-time analysis progress with status indicators
        - **Interactive Review**: Request revisions for specific analysis components
        - **Export Ready**: Results formatted for production planning
        
        **Note:** For best results with PDF files, ensure your script is text-based (not scanned images). Analysis progress will be shown in real-time as each component completes.
        """)
        
        # Show supported formats with examples
        with st.expander("📋 Supported Script Formats & Examples"):
            st.markdown("""
            ### Standard Screenplay Format:
            ```
            INT. COFFEE SHOP - DAY
            
            SARAH sits at a corner table with her laptop.
            
            SARAH
            (into phone)
            I can't do this anymore.
            
            The BARISTA approaches with coffee.
            
            BARISTA
            One large coffee, extra shot.
            ```
            
            ### Fountain Format:
            ```
            INT. COFFEE SHOP - DAY
            
            SARAH sits at a corner table with her laptop.
            
            SARAH
            (into phone)
            I can't do this anymore.
            ```
            
            ### BABAK Format (Malaysian):
            ```
            BABAK 1: INT. KEDAI KOPI - HARI
            
            SARAH duduk di meja sudut dengan laptop.
            
            SARAH
            (ke telefon)
            Saya tak boleh buat ni lagi.
            ```
            """)
        
        # Show tips for better results
        with st.expander("💡 Tips for Better Analysis Results"):
            st.markdown("""
            ### For PDF Files:
            - Ensure PDFs contain selectable text (not scanned images)
            - Use standard screenplay formatting
            - Avoid heavily formatted or watermarked PDFs
            
            ### For Text Files:
            - Use standard screenplay format with scene headers
            - Include character names in ALL CAPS
            - Use proper scene transitions (CUT TO:, FADE IN:, etc.)
            
            ### General Tips:
            - Include complete scene headers (INT./EXT. LOCATION - TIME)
            - Use consistent character naming throughout
            - Include action lines and dialogue for better analysis
            - Ensure proper formatting for scene breaks
            
            ### What the Tool Analyzes:
            - **Scene Structure**: Headers, locations, time of day
            - **Characters**: Names, appearances, interactions
            - **Props & Costumes**: Mentioned items and requirements
            - **Locations**: Interior/exterior, permits needed
            - **Production Costs**: Budget estimates and optimization
            - **Timeline**: Shooting schedule and crew requirements
            """)

if __name__ == "__main__":
    main()