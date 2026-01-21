/**
 * Verification Service
 * API calls for the verification workflow
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface VerificationQueueParams {
  status?: 'pending_verification' | 'verified' | 'rejected';
  skip?: number;
  limit?: number;
}

export interface VerificationImage {
  id: string;
  project_id: string;
  filename: string;
  filepath?: string;
  original_filename: string;
  file_type: string;
  ocr_text?: string;
  ocr_status: string;
  ocr_processed_at?: string;
  verification_status: 'pending_verification' | 'verified' | 'rejected';
  verified_by?: string;
  verified_at?: string;
  version: number;
  created_at?: string;
  updated_at?: string;
}

export interface AuditEntry {
  id: string;
  image_id: string;
  user_id: string;
  action: 'edit' | 'verify' | 'reject' | 'undo' | 'redo';
  field_name?: string;
  old_value?: string;
  new_value?: string;
  notes?: string;
  created_at: string;
}

export interface VerificationQueueResponse {
  success: boolean;
  items: VerificationImage[];
  total: number;
  skip: number;
  limit: number;
}

export interface QueueCountsResponse {
  success: boolean;
  counts: {
    pending_verification: number;
    verified: number;
    rejected: number;
  };
}

export interface ImageDetailsResponse {
  success: boolean;
  image: VerificationImage;
  audit_trail: AuditEntry[];
}

export interface EditImageRequest {
  ocr_text: string;
  version?: number;
  notes?: string;
}

export interface VerifyImageRequest {
  version?: number;
  notes?: string;
}

export interface RejectImageRequest {
  version?: number;
  notes: string;
}

export interface BatchVerifyRequest {
  image_ids: string[];
  notes?: string;
}

export interface BatchRejectRequest {
  image_ids: string[];
  notes: string;
}

export interface BatchOperationResponse {
  success: boolean;
  verified_count?: number;
  rejected_count?: number;
  total_count: number;
  errors: Array<{ image_id: string; error: string }>;
}

export interface AuditTrailResponse {
  success: boolean;
  audit_trail: AuditEntry[];
  count: number;
}

/**
 * Get verification queue
 */
export async function getVerificationQueue(params: VerificationQueueParams = {}) {
  const { data } = await api.get<VerificationQueueResponse>('/verification/queue', { params });
  return data;
}

/**
 * Get counts for each verification status
 */
export async function getQueueCounts() {
  const { data } = await api.get<QueueCountsResponse>('/verification/queue/counts');
  return data;
}

/**
 * Get image details with audit trail
 */
export async function getImageForVerification(imageId: string) {
  const { data } = await api.get<ImageDetailsResponse>(`/verification/image/${imageId}`);
  return data;
}

/**
 * Edit image metadata
 */
export async function editImageMetadata(imageId: string, request: EditImageRequest) {
  const { data } = await api.put<ImageDetailsResponse>(`/verification/image/${imageId}/edit`, request);
  return data;
}

/**
 * Verify image
 */
export async function verifyImage(imageId: string, request: VerifyImageRequest) {
  const { data } = await api.post<ImageDetailsResponse>(`/verification/image/${imageId}/verify`, request);
  return data;
}

/**
 * Reject image
 */
export async function rejectImage(imageId: string, request: RejectImageRequest) {
  const { data } = await api.post<ImageDetailsResponse>(`/verification/image/${imageId}/reject`, request);
  return data;
}

/**
 * Batch verify images
 */
export async function batchVerify(request: BatchVerifyRequest) {
  const { data } = await api.post<BatchOperationResponse>('/verification/batch/verify', request);
  return data;
}

/**
 * Batch reject images
 */
export async function batchReject(request: BatchRejectRequest) {
  const { data } = await api.post<BatchOperationResponse>('/verification/batch/reject', request);
  return data;
}

/**
 * Get audit trail for an image
 */
export async function getAuditTrail(imageId: string) {
  const { data } = await api.get<AuditTrailResponse>(`/verification/audit/${imageId}`);
  return data;
}
