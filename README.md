# High Level Definition For Each File

## Backend (agents)
### info_gathering_agent.py
* **extract_script_data_from_file()** -  Reads PDF/text files and extracts script content
* **extract_script_data()** - Main function that processes script text into structured data
* **_parse_scenes()** - Splits script into individual scenes
* **_parse_scene_manual()** - Manually extracts data from a single scene (fallback)
* **_aggregate_data()** - Combines all scene data into overall script statistics
* **_fallback_extraction()** - Basic extraction when main parsing fails

### character_analysis_agent.py
* **analyze_characters()** - Main function analyzing all character requirements
* **_create_fallback_scene_character()** -  Creates basic character data when AI fails
* **_create_fallback_character_breakdown()** - Creates basic overall character analysis

### cost_analysis_agent.py
* **analyze_costs()** - Main function estimating production costs
* **_create_fallback_scene_cost()** - Creates basic cost estimate when AI fails
* **_create_fallback_cost_breakdown()** - Creates basic overall cost analysis

### location_analysis_agent.py
* **analyze_locations()** - Main function analyzing filming locations
* **_create_fallback_scene_location()** - Creates basic location data when AI fails
* **_create_fallback_location_breakdown()** - Creates basic overall location analysis

### props_extraction_agent.py
* **analyze_props()** - Main function identifying props and costumes
* **_create_fallback_scene_props()** - Creates basic props list when AI fails
* **_create_fallback_props_breakdown()** - Creates basic overall props analysis

### scene_breakdown_agent.py
* **analyze_scenes()** - Main function analyzing scene structure and drama
* **_create_fallback_scene_breakdown()** - Creates basic scene analysis when AI fails
* **_create_fallback_scene_breakdown_overall()** - Creates basic overall scene analysis

### timeline_agent.py
* **analyze_timeline()** - Main function creating shooting schedules
* **_create_fallback_scene_timeline()** - Creates basic timeline when AI fails
* **_create_fallback_timeline_breakdown()** - Creates basic overall timeline

### pdf_utils.py
* **extract_text_from_pdf()** - Main PDF text extraction using multiple methods
* **extract_with_pdfplumber()** - Extracts text using pdfplumber library
* **extract_with_pypdf2()** - Extracts text using PyPDF2 library (backup)
* **clean_extracted_text()** - Cleans and formats extracted text
* **validate_script_content()** - Checks if text looks like a valid script

## Backend (graph)
### state.py
* **merge_dict()** - Combines two dictionaries
* **merge_list()** - Combines two lists
* **merge_bool()** - Combines boolean values using OR logic
* **merge_string()** - Takes the most recent string value

### utils.py
* **extract_result()** - Gets actual data from AI agent responses
* **ensure_json_serializable()** - Makes data compatible with JSON
* **convert_to_json_serializable()** - Converts objects to JSON format
* **safe_call_agent()** - Safely calls AI agents with error handling
* **create_fallback_result()** - Creates backup results when AI fails
* **should_revise()** - Determines which analyses need revision
* **validate_json_structure()** - Checks if data is valid JSON
* **sanitize_for_json()** - Cleans data for JSON compatibility

### nodes.py
* **run_info_gathering()** - Workflow step that extracts raw script data
* **create_fallback_raw_data()** - Creates backup raw data structure
* **create_analysis_node()** - Factory function creating analysis workflow steps
* **create_fallback_analysis_result()** - Creates backup analysis results
* **run_cost_analysis()** - Workflow step for cost analysis
* **run_props_analysis()** - Workflow step for props analysis
* **run_location_analysis()** - Workflow step for location analysis
* **run_character_analysis()** - Workflow step for character analysis
* **run_scene_analysis()** - Workflow step for scene analysis
* **run_timeline_analysis()** - Workflow step for timeline analysis
* **human_review()** - Workflow step for human feedback processing

### workflow.py
* **should_continue_or_end()** - Decides if workflow should continue or finish
* **create_script_analysis_workflow()** - Builds the complete workflow graph
* **run_analyze_script_workflow_from_file()** - Runs analysis from uploaded file
* **run_analyze_script_workflow()** - Runs analysis from text content
* **get_workflow_state()** - Retrieves saved workflow progress
* **resume_workflow()** - Continues workflow from checkpoint
* **_calculate_total_time()** - Calculates total processing time
* **validate_workflow_state()** - Checks workflow data integrity

### main.py
* **main()** - Demo function showing complete workflow
* **_display_results()** - Pretty-prints analysis results
* **_format_location_types()** - Formats location data for display
* **_format_prop_categories()** - Formats props data for display

## Backend (API)
### api.py
* **convert_result_to_dict()** - Converts analysis results to dictionary
* **create_success_response()** - Creates standardized success JSON response
* **create_error_response()** - Creates standardized error JSON response
* **analyze_script_file()** - API endpoint for file upload analysis
* **analyze_script()** - API endpoint for text analysis
* **submit_feedback()** - API endpoint for human feedback
* **get_workflow_status()** - API endpoint for checking progress
* **health_check()** - API endpoint for server health
* **global_exception_handler()** - Handles unexpected API errors

## Frontend (stores)
### scripts.ts
* **setUploadedFile()** - Stores uploaded file information
* **analyzeScriptFile()** - Sends file to backend for analysis
* **analyzeScriptText()** - Sends text to backend for analysis
* **submitFeedback()** - Sends user feedback to backend
* **checkWorkflowStatus()** - Checks analysis progress
* **handleAnalysisResponse()** - Processes backend response
* **updateFeedback()** - Updates user feedback for specific section
* **toggleRevision()** - Marks section as needing revision
* **clearFeedback()** - Removes all user feedback
* **resetStore()** - Resets all store data
* **clearMessages()** - Clears error/success messages
* **handleError()** - Processes and displays errors
* **exportAnalysisData()** - Downloads analysis as JSON file
* **validateAnalysisData()** - Checks if analysis data is complete
* **isApiResponse()** - Validates API response structure
* **isScriptAnalysisData()** - Validates analysis data structure