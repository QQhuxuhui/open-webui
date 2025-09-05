// Profile management type definitions

export interface ProfileData {
  id: string;
  name: string;
  email?: string;
  nickname?: string;
  real_name?: string;
  avatar_url?: string;
  avatar?: string; // Legacy field
  
  // Phone information
  phone_number?: string;
  phone_verified: boolean;
  
  // Verification status
  real_name_verified: boolean;
  real_name_verified_at?: string;
  
  // Account settings
  interface_language?: string;
  interface_theme?: string;
  timezone?: string;
  
  // Account status
  status: string;
  last_active_at?: string;
  created_at: string;
  updated_at: string;
  
  // Consent information
  consents: Record<string, ConsentInfo>;
  
  // Profile completion
  profile_completion: number;
}

export interface ConsentInfo {
  version: string;
  consented_at: string;
  ip_address?: string;
}

export interface ProfileUpdateRequest {
  nickname?: string;
  real_name?: string;
  email?: string;
  interface_language?: string;
  interface_theme?: string;
  timezone?: string;
}

export interface ProfileChangeLog {
  id: string;
  change_type: string;
  old_value?: string;
  new_value?: string;
  ip_address?: string;
  user_agent?: string;
  reason?: string;
  created_at: string;
}

export interface PhoneChangeRequest {
  new_phone: string;
  old_phone_code?: string;
  new_phone_code: string;
}

export interface IdentityVerificationRequest {
  method: 'sms' | 'email';
  phone?: string;
  email?: string;
  code: string;
}

export interface IdentityVerificationResponse {
  success: boolean;
  verification_token?: string;
  expires_in?: number;
  message?: string;
}

export interface ProfileStatistics {
  profile_completion: number;
  recent_changes_30d: number;
  total_consents: number;
  account_age_days: number;
  last_profile_update: string;
  verification_status: {
    phone_verified: boolean;
    real_name_verified: boolean;
    email_verified: boolean;
  };
}

export interface AvatarUploadResponse {
  success: boolean;
  avatar_url?: string;
  message?: string;
  error?: string;
}

// API Response types
export interface ProfileResponse {
  success: boolean;
  data?: ProfileData;
  error?: string;
  message?: string;
}

export interface ProfileChangeHistoryResponse {
  success: boolean;
  data?: ProfileChangeLog[];
  error?: string;
}

export interface ProfileStatisticsResponse {
  success: boolean;
  data?: ProfileStatistics;
  error?: string;
}

// Form validation types
export interface ProfileFormErrors {
  nickname?: string;
  real_name?: string;
  email?: string;
  phone_number?: string;
  general?: string;
}

export interface PhoneChangeFormErrors {
  new_phone?: string;
  old_phone_code?: string;
  new_phone_code?: string;
  general?: string;
}

// Avatar cropping types (from react-easy-crop)
export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface CropPoint {
  x: number;
  y: number;
}

// File upload types
export interface FileUploadOptions {
  maxSize?: number;
  allowedTypes?: string[];
  quality?: number;
}

export interface FileValidationResult {
  valid: boolean;
  error?: string;
  file?: File;
}

// Security and audit types
export interface SecurityEvent {
  id: string;
  event_type: string;
  description: string;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface IdentityToken {
  token: string;
  expires_at: string;
  purpose: string;
}

// Profile settings enums
export enum ProfileChangeType {
  NICKNAME = 'nickname',
  REAL_NAME = 'real_name',
  EMAIL = 'email',
  PHONE_NUMBER = 'phone_number',
  AVATAR = 'avatar',
  VERIFICATION = 'verification',
  PASSWORD = 'password',
  SETTINGS = 'profile_settings'
}

export enum VerificationMethod {
  SMS = 'sms',
  EMAIL = 'email'
}

export enum AccountStatus {
  ACTIVE = 'active',
  PENDING = 'pending',
  SUSPENDED = 'suspended',
  CLOSED = 'closed'
}

// Utility types
export type ProfileField = keyof ProfileUpdateRequest;
export type ProfileChangeTypeValue = `${ProfileChangeType}`;
export type VerificationMethodValue = `${VerificationMethod}`;

// Component prop types
export interface ProfileEditProps {
  initialData?: ProfileData;
  onUpdate?: (data: ProfileData) => void;
  readOnly?: boolean;
}

export interface AvatarCropperProps {
  file: File;
  onCropped: (croppedFile: File) => void;
  onClose: () => void;
  aspectRatio?: number;
  cropShape?: 'rect' | 'round';
}

export interface PhoneChangeModalProps {
  currentPhone?: string | null;
  onChanged: (newPhone: string) => void;
  onClose: () => void;
}

export interface ProfileHistoryProps {
  onClose: () => void;
  userId?: string;
  changeType?: ProfileChangeType;
}

// Hook return types
export interface UseProfileReturn {
  profile: ProfileData | null;
  isLoading: boolean;
  error: string | null;
  updateProfile: (updates: ProfileUpdateRequest) => Promise<void>;
  uploadAvatar: (file: File) => Promise<string>;
  changePhone: (newPhone: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
}

export interface UsePhoneChangeReturn {
  isChanging: boolean;
  error: string | null;
  sendOldPhoneVerification: (phone: string) => Promise<void>;
  sendNewPhoneVerification: (phone: string) => Promise<void>;
  verifyOldPhone: (phone: string, code: string) => Promise<void>;
  verifyNewPhone: (phone: string, code: string) => Promise<void>;
  confirmChange: (newPhone: string) => Promise<void>;
  reset: () => void;
}

export interface UseProfileHistoryReturn {
  changes: ProfileChangeLog[];
  isLoading: boolean;
  error: string | null;
  loadMore: () => Promise<void>;
  hasMore: boolean;
  filter: ProfileChangeType | null;
  setFilter: (filter: ProfileChangeType | null) => void;
}