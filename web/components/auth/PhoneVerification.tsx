'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

export interface PhoneVerificationProps {
  phone: string
  onCodeChange: (code: string) => void
  onResendCode: () => void
  loading?: boolean
  error?: string
  maxLength?: number
  autoFocus?: boolean
}

const PhoneVerification: React.FC<PhoneVerificationProps> = ({
  phone,
  onCodeChange,
  onResendCode,
  loading = false,
  error,
  maxLength = 6,
  autoFocus = true,
}) => {
  const { t } = useTranslation()
  const [code, setCode] = useState('')
  const [countdown, setCountdown] = useState(0)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])

  // Initialize input refs array
  useEffect(() => {
    inputRefs.current = Array(maxLength).fill(null)
  }, [maxLength])

  // Start countdown on mount
  useEffect(() => {
    const savedCountdown = localStorage.getItem('sms_countdown')
    if (savedCountdown) {
      const timeLeft = Math.max(0, parseInt(savedCountdown) - Date.now())
      if (timeLeft > 0) {
        setCountdown(Math.ceil(timeLeft / 1000))
      }
    }
  }, [])

  // Countdown timer
  useEffect(() => {
    let timer: NodeJS.Timeout
    if (countdown > 0) {
      timer = setTimeout(() => {
        setCountdown(countdown - 1)
      }, 1000)
    } else {
      localStorage.removeItem('sms_countdown')
    }
    return () => clearTimeout(timer)
  }, [countdown])

  // Auto focus first input
  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      inputRefs.current[0].focus()
    }
  }, [autoFocus])

  // Notify parent component when code changes
  useEffect(() => {
    onCodeChange(code)
  }, [code, onCodeChange])

  const handleInputChange = (index: number, value: string) => {
    // Only allow digits
    const sanitizedValue = value.replace(/\D/g, '')
    
    if (sanitizedValue.length <= 1) {
      const newCode = code.split('')
      newCode[index] = sanitizedValue
      setCode(newCode.join(''))

      // Auto focus next input
      if (sanitizedValue && index < maxLength - 1) {
        inputRefs.current[index + 1]?.focus()
      }
    }
  }

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Handle backspace
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus()
    }
    
    // Handle paste
    if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      navigator.clipboard.readText().then((text) => {
        const digits = text.replace(/\D/g, '').slice(0, maxLength)
        setCode(digits.padEnd(maxLength, ''))
        
        // Focus last filled input or first empty input
        const nextIndex = Math.min(digits.length, maxLength - 1)
        inputRefs.current[nextIndex]?.focus()
      })
    }
  }

  const handleResendCode = async () => {
    if (countdown > 0 || loading) return
    
    try {
      await onResendCode()
      
      // Start 60 second countdown
      const endTime = Date.now() + 60000
      localStorage.setItem('sms_countdown', endTime.toString())
      setCountdown(60)
    } catch (error) {
      console.error('Failed to resend code:', error)
    }
  }

  const formatPhone = (phone: string) => {
    // Format phone number for display
    if (phone.startsWith('+86')) {
      const number = phone.slice(3)
      return `${number.slice(0, 3)} ${number.slice(3, 7)} ${number.slice(7)}`
    }
    return phone
  }

  return (
    <div className="space-y-4">
      {/* Title */}
      <div className="text-center">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {t('auth.phone.verification.title')}
        </h3>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {t('auth.phone.verification.description', { phone: formatPhone(phone) })}
        </p>
      </div>

      {/* Verification Code Input */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('auth.phone.verification.codeLabel')}
        </label>
        
        <div className="flex justify-center space-x-2">
          {Array.from({ length: maxLength }).map((_, index) => (
            <input
              key={index}
              ref={(el) => (inputRefs.current[index] = el)}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={code[index] || ''}
              onChange={(e) => handleInputChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className={`w-12 h-12 text-center text-lg font-semibold border rounded-lg transition-colors ${
                error
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
              } dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 dark:focus:border-blue-400 dark:focus:ring-blue-400`}
              disabled={loading}
              aria-label={`${t('auth.phone.verification.digitLabel')} ${index + 1}`}
            />
          ))}
        </div>

        {/* Error message */}
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400 text-center">
            {error}
          </p>
        )}

        {/* Code length indicator */}
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          {code.length}/{maxLength} {t('auth.phone.verification.digitsEntered')}
        </p>
      </div>

      {/* Resend Code */}
      <div className="text-center">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {t('auth.phone.verification.didNotReceive')}{' '}
          {countdown > 0 ? (
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {countdown}s
            </span>
          ) : (
            <button
              type="button"
              onClick={handleResendCode}
              disabled={loading}
              className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('auth.phone.verification.resendCode')}
            </button>
          )}
        </p>
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      )}
    </div>
  )
}

export default PhoneVerification