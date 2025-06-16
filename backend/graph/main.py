import asyncio
import uuid
from graph.workflow import run_analyze_script_workflow, get_workflow_state, resume_workflow

async def main():
    """Main function to demonstrate the workflow with checkpointing"""
    
    # Generate a unique thread ID for this workflow run
    thread_id = f"script_analysis_{uuid.uuid4().hex[:8]}"
    
    sample_script = """
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
    
    try:
        print(f"🆔 Using thread ID: {thread_id}")
        
        # Run initial workflow
        result = await run_analyze_script_workflow(sample_script, thread_id=thread_id)
        
        print("\n" + "=" * 60)
        print("📋 DETAILED RESULTS")
        print("=" * 60)
        
        # Display results using simplified structure
        _display_results(result)
        
        # Demonstrate checkpoint retrieval
        print("\n" + "=" * 60)
        print("🔍 CHECKPOINT DEMONSTRATION")
        print("=" * 60)
        
        saved_state = await get_workflow_state(thread_id)
        if saved_state:
            print(f"✅ Successfully retrieved saved state for thread: {thread_id}")
            print(f"   - Task complete: {saved_state.task_complete}")
            print(f"   - Analyses complete: {sum(1 for v in saved_state.analyses_complete.values() if v)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error in main: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        raise

def _display_results(result):
    """Display analysis results in organized format"""
    sections = [
        ("📊 RAW DATA SUMMARY", result.raw_data, [
            ("Total Scenes", lambda x: len(getattr(x, 'scenes', []))),
            ("Total Characters", lambda x: len(getattr(x, 'total_characters', []))),
            ("Total Locations", lambda x: len(getattr(x, 'total_locations', []))),
            ("Language", lambda x: getattr(x, 'language_detected', 'N/A')),
            ("Estimated Pages", lambda x: f"{getattr(x, 'estimated_total_pages', 0):.1f}")
        ]),
        ("💰 COST ANALYSIS", result.cost_analysis, [
            ("Budget Range", lambda x: getattr(x, 'total_budget_range', 'N/A')),
            ("Shooting Days", lambda x: getattr(x, 'estimated_total_days', 'N/A')),
            ("Scene Costs", lambda x: len(getattr(x, 'scene_costs', [])))
        ]),
        ("👥 CHARACTER ANALYSIS", result.character_analysis, [
            ("Main Characters", lambda x: len(getattr(x, 'main_characters', []))),
            ("Supporting Characters", lambda x: len(getattr(x, 'supporting_characters', []))),
            ("Scene Character Breakdowns", lambda x: len(getattr(x, 'scene_characters', [])))
        ]),
        ("📍 LOCATION ANALYSIS", result.location_analysis, [
            ("Unique Locations", lambda x: len(getattr(x, 'unique_locations', []))),
            ("Scene Location Breakdowns", lambda x: len(getattr(x, 'scene_locations', []))),
            ("Location Types", lambda x: _format_location_types(getattr(x, 'locations_by_type', {})))
        ]),
        ("🎭 PROPS ANALYSIS", result.props_analysis, [
            ("Total Props", lambda x: len(getattr(x, 'master_props_list', []))),
            ("Scene Prop Breakdowns", lambda x: len(getattr(x, 'scene_props', []))),
            ("Prop Categories", lambda x: _format_prop_categories(getattr(x, 'props_by_category', {})))
        ]),
        ("🎬 SCENE ANALYSIS", result.scene_analysis, [
            ("Detailed Scene Breakdowns", lambda x: len(getattr(x, 'detailed_scenes', []))),
            ("Three-Act Structure", lambda x: len(getattr(x, 'three_act_structure', [])))
        ]),
        ("⏰ TIMELINE ANALYSIS", result.timeline_analysis, [
            ("Scene Timeline Breakdowns", lambda x: len(getattr(x, 'scene_timelines', []))),
            ("Total Shooting Days", lambda x: getattr(x, 'total_shooting_days', 'N/A')),
            ("Cast Scheduling", lambda x: len(getattr(x, 'cast_scheduling', {})))
        ])
    ]
    
    for title, data, fields in sections:
        print(f"\n{title}:")
        if data:
            for field_name, field_func in fields:
                try:
                    value = field_func(data)
                    print(f"   {field_name}: {value}")
                except Exception:
                    print(f"   {field_name}: N/A")
        else:
            print("   No data available")

def _format_location_types(locations_by_type):
    """Format location types for display"""
    if not locations_by_type:
        return "N/A"
    return ", ".join([f"{loc_type}: {len(locations)}" for loc_type, locations in locations_by_type.items() if locations])

def _format_prop_categories(props_by_category):
    """Format prop categories for display"""
    if not props_by_category:
        return "N/A"
    return ", ".join([f"{category}: {len(props)}" for category, props in props_by_category.items() if props])

if __name__ == "__main__":
    asyncio.run(main())