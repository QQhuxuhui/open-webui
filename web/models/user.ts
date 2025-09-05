export type User = {
  id: string
  firstName: string
  lastName: string
  name: string
  phone: string
  username: string
  email: string
  avatar: string
  // Compliance-related fields
  phone_number?: string | null
  phone_verified: boolean
  real_name?: string | null
  real_name_verified: boolean
  real_name_verified_at?: Date | null
  nickname?: string | null
  avatar_url?: string | null
  created_at: Date
  updated_at: Date
}

export type UserResponse = {
  users: User[]
}

export const fetchUsers = (url: string) =>
  fetch(url).then<UserResponse>(r => r.json())

// Compliance-related enums and types
export enum ConsentType {
  PRIVACY_POLICY = 'privacy_policy',
  TERMS_OF_SERVICE = 'terms_of_service', 
  MARKETING = 'marketing',
  ANALYTICS = 'analytics'
}

export enum SMSPurpose {
  REGISTRATION = 'registration',
  LOGIN = 'login',
  PHONE_CHANGE = 'phone_change',
  PASSWORD_RESET = 'password_reset'
}

export enum ContentType {
  TEXT = 'text',
  IMAGE = 'image', 
  VIDEO = 'video',
  AUDIO = 'audio'
}

export enum ReportCategory {
  INAPPROPRIATE_CONTENT = 'inappropriate_content',
  MISINFORMATION = 'misinformation',
  TECHNICAL_ISSUE = 'technical_issue',
  SPAM = 'spam',
  HARASSMENT = 'harassment',
  OTHER = 'other'
}

export enum ReportStatus {
  PENDING = 'pending',
  REVIEWING = 'reviewing',
  RESOLVED = 'resolved',
  DISMISSED = 'dismissed'
}

export enum VerificationStatus {
  PENDING = 'pending',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  EXPIRED = 'expired'
}

export enum IDType {
  NATIONAL_ID = 'national_id',
  PASSPORT = 'passport',
  DRIVERS_LICENSE = 'drivers_license',
  OTHER = 'other'
}

// User consent tracking interface
export interface UserConsent {
  id: string
  user_id: string
  consent_type: ConsentType
  consent_version: string
  consented_at: Date
  ip_address?: string | null
  user_agent?: string | null
  created_at: Date
  updated_at: Date
}

// SMS verification interface
export interface SmsVerification {
  id: string
  phone_number: string
  verification_code: string // This will be hashed on backend
  purpose: SMSPurpose
  expires_at: Date
  verified_at?: Date | null
  attempts: number
  max_attempts: number
  created_at: Date
  updated_at: Date
  // Computed properties
  is_expired?: boolean
  is_verified?: boolean
  attempts_remaining?: number
}

// Content reporting interface
export interface ContentReport {
  id: string
  reporter_id: string
  content_id: string
  content_type: ContentType
  report_category: ReportCategory
  report_reason?: string | null
  content_snapshot?: Record<string, any> | null
  status: ReportStatus
  moderator_notes?: string | null
  moderator_id?: string | null
  created_at: Date
  resolved_at?: Date | null
  updated_at: Date
  // Computed properties
  is_resolved?: boolean
  resolution_time_hours?: number | null
}

// Real name verification interface
export interface RealNameVerification {
  id: string
  user_id: string
  real_name: string
  id_type: IDType
  id_number_encrypted: string
  document_front_url?: string | null
  document_back_url?: string | null
  status: VerificationStatus
  rejection_reason?: string | null
  verified_at?: Date | null
  verified_by?: string | null
  created_at: Date
  updated_at: Date
  // Computed properties
  is_approved?: boolean
  is_pending?: boolean
  verification_time_days?: number | null
}

// Message interface extension for AI content identification
export interface MessageAIInfo {
  ai_generated: boolean
  ai_model_info?: {
    provider?: string
    model_id?: string
    version?: string
    temperature?: number
    [key: string]: any
  } | null
  content_labels?: {
    inappropriate?: boolean
    generated_content_notice?: string
    watermark_applied?: boolean
    [key: string]: any
  } | null
}

// API request/response types
export interface CreateUserConsentRequest {
  consent_type: ConsentType
  consent_version: string
  ip_address?: string
  user_agent?: string
}

export interface SendSMSVerificationRequest {
  phone_number: string
  purpose: SMSPurpose
}

export interface VerifySMSRequest {
  phone_number: string
  verification_code: string
  purpose: SMSPurpose
}

export interface CreateContentReportRequest {
  content_id: string
  content_type: ContentType
  report_category: ReportCategory
  report_reason?: string
  content_snapshot?: Record<string, any>
}

export interface CreateRealNameVerificationRequest {
  real_name: string
  id_type: IDType
  id_number: string // Will be encrypted on backend
  document_front_file?: File
  document_back_file?: File
}

// Response types
export interface UserConsentsResponse {
  consents: UserConsent[]
  total: number
}

export interface ContentReportsResponse {
  reports: ContentReport[]
  total: number
}

export interface RealNameVerificationsResponse {
  verifications: RealNameVerification[]
  total: number
}
