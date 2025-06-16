import { defineStore } from "pinia";
import axios, { AxiosResponse, AxiosError } from "axios";

// Enhanced types for better TypeScript support
interface ScriptAnalysisData {
  raw_data: any;
  cost_analysis: any;
  character_analysis: any;
  location_analysis: any;
  props_analysis: any;
  scene_analysis: any;
  timeline_analysis: any;
  task_complete: boolean;
  human_review_complete: boolean;
  analyses_complete: Record<string, boolean>;
  errors: string[];
}

interface ApiResponse {
  success: boolean;
  thread_id: string;
  needs_human_review: boolean;
  data: ScriptAnalysisData;
  message: string;
  filename?: string;
  error?: string;
  details?: string;
}

interface FeedbackData {
  feedback: Record<string, string>;
  needs_revision: Record<string, boolean>;
}

// Create configured axios instance
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000, // 60 second timeout for long-running analysis
  headers: {
    'Accept': 'application/json',
  }
});

// Request interceptor to ensure JSON requests
api.interceptors.request.use(
  (config) => {
    // Always request JSON responses
    config.headers['Accept'] = 'application/json';
    
    // Set content-type for non-FormData requests
    if (config.data && !(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    }
    
    console.log('🚀 API Request:', {
      method: config.method?.toUpperCase(),
      url: config.url,
      headers: config.headers,
      dataType: config.data instanceof FormData ? 'FormData' : typeof config.data
    });
    
    return config;
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor to validate JSON
api.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log('✅ API Response received:', {
      status: response.status,
      contentType: response.headers['content-type'],
      dataType: typeof response.data,
      hasSuccess: 'success' in response.data
    });
    
    // Validate content type
    const contentType = response.headers['content-type'];
    if (contentType && !contentType.includes('application/json')) {
      console.warn('⚠️ Response is not JSON:', contentType);
      throw new Error(`Expected JSON response, got ${contentType}`);
    }
    
    // Validate response structure
    if (typeof response.data !== 'object' || response.data === null) {
      console.error('❌ Response data is not an object:', response.data);
      throw new Error('Invalid response format - expected JSON object');
    }
    
    // Check for required fields
    if (!('success' in response.data)) {
      console.error('❌ Response missing success field:', response.data);
      throw new Error('Invalid API response format');
    }
    
    return response;
  },
  (error: AxiosError) => {
    console.error('❌ API Response Error:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    
    // Try to extract error message from response
    if (error.response?.data && typeof error.response.data === 'object') {
      const errorData = error.response.data as any;
      if (errorData.message || errorData.error) {
        error.message = errorData.message || errorData.error;
      }
    }
    
    return Promise.reject(error);
  }
);

// Type guards for runtime validation
function isApiResponse(data: any): data is ApiResponse {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.success === 'boolean' &&
    (data.success === false || (
      typeof data.thread_id === 'string' &&
      typeof data.needs_human_review === 'boolean' &&
      data.data &&
      typeof data.message === 'string'
    ))
  );
}

function isScriptAnalysisData(data: any): data is ScriptAnalysisData {
  return (
    data &&
    typeof data === 'object' &&
    typeof data.task_complete === 'boolean' &&
    typeof data.human_review_complete === 'boolean' &&
    Array.isArray(data.errors)
  );
}

export const useScriptStore = defineStore('script', {
  state: () => ({
    // Analysis data
    analysisData: null as ScriptAnalysisData | null,
    
    // Workflow state
    threadId: null as string | null,
    isAnalyzing: false,
    isSubmittingFeedback: false,
    needsHumanReview: false,
    taskComplete: false,
    
    // File handling
    uploadedFile: null as File | null,
    fileName: '',
    
    // User feedback
    userFeedback: {} as Record<string, string>,
    revisionsNeeded: {} as Record<string, boolean>,
    
    // UI state
    currentStep: 'upload' as 'upload' | 'analyzing' | 'review' | 'complete',
    error: null as string | null,
    successMessage: null as string | null,
    
    // Analysis sections for review
    analysisSections: [
      { key: 'cost', label: 'Cost Analysis', icon: '💰' },
      { key: 'character', label: 'Character Analysis', icon: '👥' },
      { key: 'location', label: 'Location Analysis', icon: '📍' },
      { key: 'props', label: 'Props Analysis', icon: '🎭' },
      { key: 'scene', label: 'Scene Analysis', icon: '🎬' },
      { key: 'timeline', label: 'Timeline Analysis', icon: '⏰' }
    ]
  }),

  getters: {
    // Check if analysis is available
    hasAnalysisData: (state) => state.analysisData !== null,
    
    // Get specific analysis sections
    costAnalysis: (state) => state.analysisData?.cost_analysis,
    characterAnalysis: (state) => state.analysisData?.character_analysis,
    locationAnalysis: (state) => state.analysisData?.location_analysis,
    propsAnalysis: (state) => state.analysisData?.props_analysis,
    sceneAnalysis: (state) => state.analysisData?.scene_analysis,
    timelineAnalysis: (state) => state.analysisData?.timeline_analysis,
    rawData: (state) => state.analysisData?.raw_data,
    
    // Progress tracking
    completedAnalyses: (state) => {
      if (!state.analysisData?.analyses_complete) return 0;
      return Object.values(state.analysisData.analyses_complete).filter(Boolean).length;
    },
    
    totalAnalyses: (state) => state.analysisSections.length,
    
    progressPercentage: (state) => {
      const completed = Object.values(state.analysisData?.analyses_complete || {}).filter(Boolean).length;
      const total = state.analysisSections.length;
      return total > 0 ? Math.round((completed / total) * 100) : 0;
    },
    
    // Check if any revisions are pending
    hasPendingRevisions: (state) => {
      return Object.values(state.revisionsNeeded).some(Boolean);
    },
    
    // Get sections that need revision
    sectionsNeedingRevision: (state) => {
      return Object.entries(state.revisionsNeeded)
        .filter(([_, needs]) => needs)
        .map(([key, _]) => key);
    }
  },

  actions: {
    // Set uploaded file
    setUploadedFile(file: File) {
      this.uploadedFile = file;
      this.fileName = file.name;
      this.currentStep = 'upload';
      this.clearMessages();
    },

    // Analyze script from file upload
    async analyzeScriptFile(file: File) {
      this.isAnalyzing = true;
      this.currentStep = 'analyzing';
      this.clearMessages();
      
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        console.log('📤 Uploading file for analysis:', file.name);
        
        const response = await api.post<ApiResponse>(
          '/analyze-script-file',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
              'Accept': 'application/json'
            }
          }
        );
        
        // Validate response structure
        if (!isApiResponse(response.data)) {
          throw new Error('Invalid response format from server');
        }
        
        if (response.data.success) {
          console.log('✅ File analysis successful');
          this.handleAnalysisResponse(response.data);
        } else {
          throw new Error(response.data.error || 'Analysis failed');
        }
      } catch (error) {
        this.handleError('Failed to analyze script file', error);
      } finally {
        this.isAnalyzing = false;
      }
    },

    // Analyze script from text content
    async analyzeScriptText(scriptContent: string) {
      this.isAnalyzing = true;
      this.currentStep = 'analyzing';
      this.clearMessages();
      
      try {
        console.log('📤 Sending script text for analysis');
        
        const response = await api.post<ApiResponse>(
          '/analyze-script',
          { script_content: scriptContent }
        );
        
        // Validate response structure
        if (!isApiResponse(response.data)) {
          throw new Error('Invalid response format from server');
        }
        
        if (response.data.success) {
          console.log('✅ Text analysis successful');
          this.handleAnalysisResponse(response.data);
        } else {
          throw new Error(response.data.error || 'Analysis failed');
        }
      } catch (error) {
        this.handleError('Failed to analyze script text', error);
      } finally {
        this.isAnalyzing = false;
      }
    },

    // Submit human feedback
    async submitFeedback() {
      if (!this.threadId) {
        this.error = 'No active analysis session';
        return;
      }

      this.isSubmittingFeedback = true;
      this.clearMessages();
      
      try {
        const feedbackData: FeedbackData = {
          feedback: this.userFeedback,
          needs_revision: this.revisionsNeeded
        };
        
        console.log('📤 Submitting feedback:', feedbackData);
        
        const response = await api.post<ApiResponse>(
          '/submit-feedback',
          {
            thread_id: this.threadId,
            ...feedbackData
          }
        );
        
        // Validate response structure
        if (!isApiResponse(response.data)) {
          throw new Error('Invalid response format from server');
        }
        
        if (response.data.success) {
          console.log('✅ Feedback submission successful');
          this.handleAnalysisResponse(response.data);
          this.successMessage = response.data.message;
          
          // Clear feedback if no more revisions needed
          if (!response.data.needs_human_review) {
            this.clearFeedback();
          }
        } else {
          throw new Error(response.data.error || 'Feedback submission failed');
        }
      } catch (error) {
        this.handleError('Failed to submit feedback', error);
      } finally {
        this.isSubmittingFeedback = false;
      }
    },

    // Check workflow status
    async checkWorkflowStatus() {
      if (!this.threadId) return;
      
      try {
        console.log('📤 Checking workflow status for:', this.threadId);
        
        const response = await api.get<ApiResponse>(
          `/workflow-status/${this.threadId}`
        );
        
        if (!isApiResponse(response.data)) {
          throw new Error('Invalid response format from server');
        }
        
        if (response.data.success) {
          this.taskComplete = response.data.data?.task_complete || false;
          this.needsHumanReview = !response.data.data?.human_review_complete;
          
          if (this.taskComplete) {
            this.currentStep = 'complete';
          }
          
          console.log('✅ Status check successful');
        } else {
          throw new Error(response.data.error || 'Status check failed');
        }
      } catch (error) {
        console.error('Failed to check workflow status:', error);
      }
    },

    // Handle API response
    handleAnalysisResponse(response: ApiResponse) {
      console.log('📥 Handling analysis response:', response);
      
      // Validate data structure
      if (response.data && !isScriptAnalysisData(response.data)) {
        console.warn('⚠️ Analysis data structure may be invalid');
      }
      
      this.threadId = response.thread_id;
      this.analysisData = response.data;
      this.needsHumanReview = response.needs_human_review;
      this.taskComplete = response.data?.task_complete || false;
      
      if (response.filename) {
        this.fileName = response.filename;
      }
      
      // Update current step based on response
      if (this.taskComplete) {
        this.currentStep = 'complete';
      } else if (this.needsHumanReview) {
        this.currentStep = 'review';
      }
      
      this.successMessage = response.message;
      
      console.log('✅ Response handled successfully');
    },

    // Update user feedback for a specific section
    updateFeedback(section: string, feedback: string) {
      this.userFeedback[section] = feedback;
      console.log(`📝 Updated feedback for ${section}:`, feedback);
    },

    // Toggle revision needed for a section
    toggleRevision(section: string, needsRevision: boolean) {
      this.revisionsNeeded[section] = needsRevision;
      console.log(`🔄 Revision ${needsRevision ? 'requested' : 'cleared'} for ${section}`);
    },

    // Clear all feedback
    clearFeedback() {
      this.userFeedback = {};
      this.revisionsNeeded = {};
      console.log('🧹 Feedback cleared');
    },

    // Reset entire store
    resetStore() {
      console.log('🔄 Resetting store');
      this.analysisData = null;
      this.threadId = null;
      this.isAnalyzing = false;
      this.isSubmittingFeedback = false;
      this.needsHumanReview = false;
      this.taskComplete = false;
      this.uploadedFile = null;
      this.fileName = '';
      this.currentStep = 'upload';
      this.clearFeedback();
      this.clearMessages();
    },

    // Utility methods
    clearMessages() {
      this.error = null;
      this.successMessage = null;
    },

    handleError(message: string, error: any) {
      console.error('❌', message, error);
      
      let errorMessage = message;
      
      if (axios.isAxiosError(error)) {
        if (error.response?.data) {
          const errorData = error.response.data as any;
          errorMessage = errorData.message || errorData.error || errorData.detail || error.message;
        } else if (error.message) {
          errorMessage = error.message;
        }
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      this.error = errorMessage;
      this.currentStep = 'upload';
    },

    // Export analysis data
    exportAnalysisData() {
      if (!this.analysisData) {
        console.warn('⚠️ No analysis data to export');
        return null;
      }
      
      try {
        const exportData = {
          fileName: this.fileName,
          threadId: this.threadId,
          analysisDate: new Date().toISOString(),
          data: this.analysisData
        };
        
        const jsonString = JSON.stringify(exportData, null, 2);
        const blob = new Blob([jsonString], {
          type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `script-analysis-${this.fileName || 'export'}.json`;
        link.click();
        
        URL.revokeObjectURL(url);
        
        console.log('✅ Analysis data exported successfully');
      } catch (error) {
        console.error('❌ Failed to export analysis data:', error);
        this.error = 'Failed to export analysis data';
      }
    },

    // Validate current analysis data
    validateAnalysisData(): boolean {
      if (!this.analysisData) {
        console.warn('⚠️ No analysis data available');
        return false;
      }
      
      const requiredFields = [
        'task_complete',
        'human_review_complete',
        'analyses_complete',
        'errors'
      ];
      
      for (const field of requiredFields) {
        if (!(field in this.analysisData)) {
          console.warn(`⚠️ Missing required field: ${field}`);
          return false;
        }
      }
      
      console.log('✅ Analysis data validation passed');
      return true;
    }
  }
});

// Export the configured API instance for use in other files
export { api };