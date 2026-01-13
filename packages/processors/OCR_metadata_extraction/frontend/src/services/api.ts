import axios from 'axios';
import type {
  AuthResponse,
  User,
  Project,
  Image,
  CreateProjectRequest,
  UpdateProjectRequest,
  ProcessImageRequest,
  OCRResult,
  OCRProvider,
} from '@/types';
import { useAuthStore } from '@/stores/authStore';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second default timeout
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    console.log(`[API-REQUEST] ${config.method?.toUpperCase()} ${config.url} - Auth: ✓`);
  } else {
    console.warn(`[API-REQUEST] ${config.method?.toUpperCase()} ${config.url} - Auth: ✗ (NO TOKEN)`);
  }
  return config;
});

// Response interceptor to handle token refresh and log errors
api.interceptors.response.use(
  (response) => {
    console.log(`[API-RESPONSE] ${response.config.method?.toUpperCase()} ${response.config.url} - Status: ${response.status} ✓`);
    return response;
  },
  async (error) => {
    const config = error.config;
    const method = config?.method?.toUpperCase() || 'UNKNOWN';
    const url = config?.url || 'UNKNOWN';
    
    if (error.response) {
      console.error(`[API-ERROR] ${method} ${url} - Status: ${error.response.status}`, error.response.data);
    } else if (error.request) {
      console.error(`[API-ERROR] ${method} ${url} - No response (Network Error)`, error.code, error.message);
    } else {
      console.error(`[API-ERROR] ${method} ${url} - Request failed`, error.message);
    }

    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          // Update both localStorage and auth store
          useAuthStore.getState().updateAccessToken(data.access_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Clear auth on refresh failure
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  register: async (email: string, password: string, name?: string): Promise<AuthResponse> => {
    const { data } = await api.post('/auth/register', { email, password, name });
    return data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const { data } = await api.post('/auth/login', { email, password });
    return data;
  },

  googleLogin: async (): Promise<{ auth_url: string }> => {
    const { data } = await api.get('/auth/google');
    return data;
  },

  getCurrentUser: async (): Promise<{ user: User }> => {
    const { data } = await api.get('/auth/me');
    return data;
  },

  refreshToken: async (refreshToken: string): Promise<{ access_token: string }> => {
    const { data } = await api.post('/auth/refresh', { refresh_token: refreshToken });
    return data;
  },
};

// Project APIs
export const projectAPI = {
  getProjects: async (skip = 0, limit = 50): Promise<{ projects: Project[]; count: number }> => {
    const { data } = await api.get('/projects', { params: { skip, limit } });
    return data;
  },

  getProject: async (projectId: string): Promise<{ project: Project }> => {
    const { data } = await api.get(`/projects/${projectId}`);
    return data;
  },

  createProject: async (projectData: CreateProjectRequest): Promise<{ project: Project }> => {
    const { data } = await api.post('/projects', projectData);
    return data;
  },

  updateProject: async (
    projectId: string,
    projectData: UpdateProjectRequest
  ): Promise<{ project: Project }> => {
    const { data } = await api.put(`/projects/${projectId}`, projectData);
    return data;
  },

  deleteProject: async (projectId: string): Promise<void> => {
    await api.delete(`/projects/${projectId}`);
  },

  getProjectImages: async (
    projectId: string,
    skip = 0,
    limit = 100
  ): Promise<{ images: Image[]; count: number }> => {
    const { data } = await api.get(`/projects/${projectId}/images`, {
      params: { skip, limit },
    });
    return data;
  },

  uploadImage: async (projectId: string, file: File): Promise<{ image: Image }> => {
    const formData = new FormData();
    formData.append('file', file);

    const { data } = await api.post(`/projects/${projectId}/images`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  deleteImage: async (projectId: string, imageId: string): Promise<void> => {
    await api.delete(`/projects/${projectId}/images/${imageId}`);
  },
};

// OCR APIs
export const ocrAPI = {
  getProviders: async (): Promise<{ providers: OCRProvider[] }> => {
    const { data } = await api.get('/ocr/providers');
    return data;
  },

  processImage: async (
    imageId: string,
    options?: ProcessImageRequest
  ): Promise<OCRResult> => {
    const { data } = await api.post(`/ocr/process/${imageId}`, options);
    return data;
  },

  getImage: async (imageId: string): Promise<Blob> => {
    const { data } = await api.get(`/ocr/image/${imageId}`, {
      responseType: 'blob',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return data;
  },

  getImageDetails: async (imageId: string): Promise<{ image: Image }> => {
    const { data } = await api.get(`/ocr/image/${imageId}/details`);
    return data;
  },

  updateImageText: async (imageId: string, text: string): Promise<{ image: Image }> => {
    const { data } = await api.put(`/ocr/image/${imageId}/text`, { text });
    return data;
  },

  updateImageJSON: async (imageId: string, jsonData: any): Promise<{ image: Image }> => {
    const { data } = await api.put(`/ocr/image/${imageId}/json`, jsonData);
    return data;
  },

  pushToArchipelago: async (imageId: string, metadata?: {
    title?: string;
    tags?: string[];
    custom_metadata?: Record<string, any>;
  }): Promise<{
    success: boolean;
    archipelago_node_id?: string;
    archipelago_url?: string;
    message: string;
  }> => {
    const { data } = await api.post('/archipelago/push-document', {
      image_id: imageId,
      ...metadata,
    });
    return data;
  },

  batchProcessImages: async (
    imageIds: string[],
    options?: ProcessImageRequest
  ): Promise<{ results: Array<{ image_id: string; status: string; text?: string; error?: string }> }> => {
    const { data } = await api.post('/ocr/batch-process', {
      image_ids: imageIds,
      ...options,
    });
    return data;
  },
};

// OCR Chain APIs
export const chainAPI = {
  // Template management
  getTemplates: async (skip = 0, limit = 50): Promise<{ templates: any[]; total: number }> => {
    const { data } = await api.get('/ocr-chains/templates', {
      params: { skip, limit },
    });
    return data;
  },

  getTemplate: async (templateId: string): Promise<{ template: any }> => {
    const { data } = await api.get(`/ocr-chains/templates/${templateId}`);
    return data;
  },

  createTemplate: async (templateData: {
    name: string;
    description?: string;
    steps: any[];
    is_public?: boolean;
  }): Promise<{ template: any }> => {
    const { data } = await api.post('/ocr-chains/templates', templateData);
    return data;
  },

  updateTemplate: async (
    templateId: string,
    updates: {
      name?: string;
      description?: string;
      steps?: any[];
      is_public?: boolean;
    }
  ): Promise<{ template: any }> => {
    const { data } = await api.put(`/ocr-chains/templates/${templateId}`, updates);
    return data;
  },

  deleteTemplate: async (templateId: string): Promise<{ success: boolean }> => {
    const { data } = await api.delete(`/ocr-chains/templates/${templateId}`);
    return data;
  },

  duplicateTemplate: async (templateId: string, newName: string): Promise<{ template: any }> => {
    const { data } = await api.post(`/ocr-chains/templates/${templateId}/duplicate`, {
      name: newName,
    });
    return data;
  },

  // Chain execution
  startChainJob: async (jobData: {
    folder_path: string;
    chain_config: {
      template_id?: string;
      steps: any[];
    };
    languages?: string[];
    handwriting?: boolean;
    recursive?: boolean;
    export_formats?: string[];
  }): Promise<{ job_id: string; job: any }> => {
    const { data } = await api.post('/ocr-chains/execute', jobData);
    return data;
  },

  getChainResults: async (jobId: string): Promise<{ job: any }> => {
    const { data } = await api.get(`/ocr-chains/results/${jobId}`);
    return data;
  },

  exportChainResults: async (jobId: string): Promise<Blob> => {
    const { data } = await api.get(`/ocr-chains/export/${jobId}`, {
      responseType: 'blob',
    });
    return data;
  },

  // Folder browsing
  listFolders: async (path: string): Promise<{ path: string; folders: Array<{ name: string; path: string; is_readable: boolean }>; total: number }> => {
    const { data } = await api.get('/ocr-chains/folders', {
      params: { path },
    });
    return data;
  },
};

export default api;
