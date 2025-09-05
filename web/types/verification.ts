// Real name verification type definitions

export interface VerificationStatus {
  is_verified: boolean;
  status: 'not_submitted' | 'pending' | 'approved' | 'rejected' | 'expired';
  can_submit: boolean;
  verification_id?: string;
  submitted_at?: string;
  verified_at?: string;
  rejection_reason?: string;
  message: string;
}

export interface VerificationSubmissionData {
  real_name: string;
  id_type: string;
  id_number: string;
  front_document: File;
  back_document?: File;
}

export interface VerificationDetails {
  id: string;
  real_name: string;
  id_type: string;
  status: string;
  has_front_document: boolean;
  has_back_document: boolean;
  submitted_at: string;
  verified_at?: string;
  rejection_reason?: string;
  verification_time_days?: number;
}

export interface IDTypeOption {
  value: string;
  label: string;
}

export interface VerificationSubmissionResult {
  verification_id: string;
  status: string;
  message: string;
}

// API Response types
export interface VerificationStatusResponse {
  success: boolean;
  data?: VerificationStatus;
  error?: string;
}

export interface VerificationDetailsResponse {
  success: boolean;
  data?: VerificationDetails;
  error?: string;
}

export interface VerificationSubmissionResponse {
  success: boolean;
  data?: VerificationSubmissionResult;
  error?: string;
  message?: string;
}

export interface IDTypesResponse {
  success: boolean;
  data?: IDTypeOption[];
  error?: string;
}

// Form validation types
export interface VerificationFormErrors {
  real_name?: string;
  id_type?: string;
  id_number?: string;
  front_document?: string;
  back_document?: string;
  general?: string;
}

// File upload types
export interface DocumentUploadProps {
  file?: File;
  onFileChange: (file: File | undefined) => void;
  label: string;
  required?: boolean;
  accept?: string;
}

// Verification statuses enum
export enum VerificationStatusEnum {
  NOT_SUBMITTED = 'not_submitted',
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  EXPIRED = 'expired'
}

// ID Types enum
export enum IDTypeEnum {
  NATIONAL_ID = 'national_id',
  PASSPORT = 'passport',
  DRIVERS_LICENSE = 'drivers_license',
  OTHER = 'other'
}

// Component prop types
export interface RealNameVerificationProps {
  onVerificationUpdate?: (status: VerificationStatus) => void;
  onClose?: () => void;
}

export interface VerificationStatusCardProps {
  status: VerificationStatus;
  onSubmitNew?: () => void;
  onViewDetails?: () => void;
}

export interface DocumentUploadCardProps {
  title: string;
  description: string;
  file?: File;
  onFileChange: (file: File | undefined) => void;
  required?: boolean;
  error?: string;
}

export interface VerificationHistoryProps {
  verificationId: string;
  onClose: () => void;
}

// Admin/Moderator types
export interface PendingVerification {
  id: string;
  user_id: string;
  real_name: string;
  id_type: string;
  has_documents: boolean;
  submitted_at: string;
  waiting_days: number;
}

export interface PendingVerificationsResponse {
  success: boolean;
  data?: PendingVerification[];
  pagination?: {
    page: number;
    per_page: number;
    total: number;
  };
  error?: string;
}

export interface VerificationUpdateRequest {
  verification_id: string;
  status: string;
  rejection_reason?: string;
}

// Utility types
export type VerificationStep = 'form' | 'upload' | 'review' | 'submit';

export interface VerificationFormData {
  real_name: string;
  id_type: string;
  id_number: string;
  front_document?: File;
  back_document?: File;
}