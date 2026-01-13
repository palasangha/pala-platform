export interface User {
  id: string;
  email: string;
  name: string;
  google_id?: string;
  created_at: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string;
  image_count: number;
  created_at: string;
  updated_at: string;
}

export interface Image {
  id: string;
  project_id: string;
  filename: string;
  filepath: string;
  original_filename: string;
  file_type?: 'image' | 'pdf';
  ocr_text: string | null;
  ocr_status: 'pending' | 'processing' | 'completed' | 'failed';
  ocr_processed_at: string | null;
  confidence?: number;
  detected_language?: string;
  file_info?: Record<string, any>;
  metadata?: Record<string, any>;
  blocks_count?: number;
  words_count?: number;
  provider?: string;
  languages?: string[];
  handwriting?: boolean;
  retry_count?: number;
  pages_processed?: number;
  intermediate_images?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface OCRResult {
  image_id: string;
  text: string;
  confidence: number;
  blocks?: Array<{ text: string; confidence?: number }>;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
}

export interface ProcessImageRequest {
  languages?: string[];
  handwriting?: boolean;
  provider?: string;
  custom_prompt?: string;
}

export interface OCRProvider {
  name: string;
  display_name: string;
  available: boolean;
}
