/**
 * Phone authentication hook for registration and login
 */
import { useState, useCallback } from 'react'

export interface PhoneRegistrationData {
  phone_number: string
  verification_code: string
  password?: string
  agreements: {
    privacy_policy: { version: string; agreed: boolean }
    terms_of_service: { version: string; agreed: boolean }
  }
  user_info?: {
    nickname?: string
    preferred_language?: string
  }
}

export interface PhoneLoginData {
  phone_number: string
  verification_code: string
  remember_me?: boolean
}

export interface Agreement {
  version: string
  content: string
  last_updated: string
}

export interface PhoneAuthResponse {
  success: boolean
  message?: string
  error?: string
  user?: {
    id: string
    phone_number: string
    phone_verified: boolean
    nickname?: string
    created_at?: string
    status: string
  }
}

export interface AgreementsResponse {
  success: boolean
  agreements?: {
    privacy_policy: Agreement
    terms_of_service: Agreement
  }
}

interface UsePhoneAuthReturn {
  // State
  loading: boolean
  error: string | null
  
  // Registration
  registerWithPhone: (data: PhoneRegistrationData) => Promise<PhoneAuthResponse>
  
  // Login
  loginWithPhone: (data: PhoneLoginData) => Promise<PhoneAuthResponse>
  
  // Agreements
  fetchAgreements: () => Promise<AgreementsResponse>
  
  // Utilities
  checkPhoneAvailability: (phoneNumber: string) => Promise<{ available: boolean; registered: boolean }>
  sendSMSCode: (phoneNumber: string, purpose: 'registration' | 'login') => Promise<{ success: boolean; message?: string }>
  clearError: () => void
}

export const usePhoneAuth = (): UsePhoneAuthReturn => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const handleError = useCallback((err: any) => {
    console.error('Phone auth error:', err)
    if (err.response?.data?.message) {
      setError(err.response.data.message)
    } else if (err.message) {
      setError(err.message)
    } else {
      setError('An unexpected error occurred')
    }
  }, [])

  const sendSMSCode = useCallback(async (phoneNumber: string, purpose: 'registration' | 'login') => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/auth/send-sms', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number: phoneNumber,
          purpose,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to send SMS code')
      }

      return data
    } catch (err) {
      handleError(err)
      return { success: false, message: error || 'Failed to send SMS code' }
    } finally {
      setLoading(false)
    }
  }, [error, handleError])

  const checkPhoneAvailability = useCallback(async (phoneNumber: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/auth/phone/check-phone', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone_number: phoneNumber,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to check phone availability')
      }

      return {
        available: data.available,
        registered: data.registered,
      }
    } catch (err) {
      handleError(err)
      return { available: false, registered: false }
    } finally {
      setLoading(false)
    }
  }, [handleError])

  const registerWithPhone = useCallback(async (data: PhoneRegistrationData): Promise<PhoneAuthResponse> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/auth/phone/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.message || 'Registration failed')
      }

      return result
    } catch (err) {
      handleError(err)
      return {
        success: false,
        error: error || 'Registration failed',
      }
    } finally {
      setLoading(false)
    }
  }, [error, handleError])

  const loginWithPhone = useCallback(async (data: PhoneLoginData): Promise<PhoneAuthResponse> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/auth/phone/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })

      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.message || 'Login failed')
      }

      return result
    } catch (err) {
      handleError(err)
      return {
        success: false,
        error: error || 'Login failed',
      }
    } finally {
      setLoading(false)
    }
  }, [error, handleError])

  const fetchAgreements = useCallback(async (): Promise<AgreementsResponse> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/auth/phone/agreements', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.message || 'Failed to fetch agreements')
      }

      return result
    } catch (err) {
      handleError(err)
      return {
        success: false,
      }
    } finally {
      setLoading(false)
    }
  }, [handleError])

  return {
    loading,
    error,
    registerWithPhone,
    loginWithPhone,
    fetchAgreements,
    checkPhoneAvailability,
    sendSMSCode,
    clearError,
  }
}