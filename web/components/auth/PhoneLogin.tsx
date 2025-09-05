'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import PhoneVerification from './PhoneVerification'
import { usePhoneAuth, PhoneLoginData } from '../../hooks/usePhoneAuth'

const PhoneLogin: React.FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  const phoneInputRef = useRef<HTMLInputElement>(null)
  
  // Phone auth hook
  const {
    loading,
    error,
    loginWithPhone,
    sendSMSCode,
    clearError,
  } = usePhoneAuth()

  // Form state
  const [step, setStep] = useState<'phone' | 'verification'>('phone')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [rememberMe, setRememberMe] = useState(false)
  
  // Form validation
  const [phoneError, setPhoneError] = useState('')

  // Auto-focus phone input
  useEffect(() => {
    if (step === 'phone' && phoneInputRef.current) {
      phoneInputRef.current.focus()
    }
  }, [step])

  const formatPhoneNumber = (value: string) => {
    // Remove non-digits
    const digits = value.replace(/\D/g, '')
    
    // Handle Chinese phone numbers
    if (digits.length <= 11 && (digits.startsWith('1') || digits.length === 0)) {
      // Format as Chinese mobile number
      if (digits.length <= 3) return digits
      if (digits.length <= 7) return `${digits.slice(0, 3)} ${digits.slice(3)}`
      return `${digits.slice(0, 3)} ${digits.slice(3, 7)} ${digits.slice(7, 11)}`
    }
    
    return value
  }

  const validatePhoneNumber = (phone: string): boolean => {
    const digits = phone.replace(/\D/g, '')
    
    // Chinese mobile number validation
    if (digits.length === 11 && digits.startsWith('1')) {
      const validPrefixes = ['13', '14', '15', '16', '17', '18', '19']
      const prefix = digits.slice(0, 2)
      return validPrefixes.includes(prefix)
    }
    
    // International format validation
    if (phone.startsWith('+') && digits.length >= 10 && digits.length <= 15) {
      return true
    }
    
    return false
  }

  const normalizePhoneNumber = (phone: string): string => {
    const digits = phone.replace(/\D/g, '')
    
    // Add +86 prefix for Chinese numbers
    if (digits.length === 11 && digits.startsWith('1')) {
      return `+86${digits}`
    }
    
    // Return as-is if already in international format
    if (phone.startsWith('+')) {
      return phone.replace(/\s/g, '')
    }
    
    return phone
  }

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setPhoneError('')

    const normalizedPhone = normalizePhoneNumber(phoneNumber)
    
    if (!validatePhoneNumber(phoneNumber)) {
      setPhoneError(t('auth.phone.errors.invalidPhone'))
      return
    }

    // Send SMS verification code
    const result = await sendSMSCode(normalizedPhone, 'login')
    if (result.success) {
      setPhoneNumber(normalizedPhone)
      setStep('verification')
    }
  }

  const handleLogin = async () => {
    if (verificationCode.length < 4) {
      return
    }

    const loginData: PhoneLoginData = {
      phone_number: phoneNumber,
      verification_code: verificationCode,
      remember_me: rememberMe,
    }

    const result = await loginWithPhone(loginData)
    
    if (result.success) {
      // Login successful - redirect to dashboard
      router.push('/dashboard')
    }
  }

  const handleBack = () => {
    setStep('phone')
    setVerificationCode('')
    clearError()
  }

  const renderPhoneStep = () => (
    <form onSubmit={handlePhoneSubmit} className="space-y-6">
      <div>
        <label htmlFor="phone" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          {t('auth.phone.phoneNumber')}
        </label>
        <input
          ref={phoneInputRef}
          id="phone"
          type="tel"
          value={phoneNumber}
          onChange={(e) => setPhoneNumber(formatPhoneNumber(e.target.value))}
          placeholder={t('auth.phone.phonePlaceholder')}
          className={`w-full px-4 py-3 text-lg border rounded-lg transition-colors ${
            phoneError
              ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
          } dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-opacity-50`}
          disabled={loading}
          required
        />
        {phoneError && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{phoneError}</p>
        )}
      </div>

      {/* Remember Me */}
      <div className="flex items-center">
        <input
          id="remember_me"
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
        />
        <label htmlFor="remember_me" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
          {t('auth.phone.rememberMe')}
        </label>
      </div>
      
      <button
        type="submit"
        disabled={loading || !phoneNumber}
        className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium text-lg rounded-lg transition-colors disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
      >
        {loading ? t('common.loading') : t('auth.phone.sendCode')}
      </button>
    </form>
  )

  const renderVerificationStep = () => (
    <div className="space-y-6">
      <PhoneVerification
        phone={phoneNumber}
        onCodeChange={setVerificationCode}
        onResendCode={() => sendSMSCode(phoneNumber, 'login')}
        loading={loading}
        error={error}
      />
      
      <div className="flex space-x-3">
        <button
          onClick={handleBack}
          className="flex-1 py-3 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50"
        >
          {t('common.back')}
        </button>
        <button
          onClick={handleLogin}
          disabled={loading || verificationCode.length < 4}
          className="flex-1 py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50"
        >
          {loading ? t('common.loading') : t('auth.phone.login')}
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {t('auth.phone.login.title')}
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {step === 'phone' 
              ? t('auth.phone.login.subtitle')
              : t('auth.phone.login.verificationSubtitle')
            }
          </p>
        </div>

        {/* Form */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow-lg rounded-lg">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg">
              <div className="flex">
                <svg className="w-5 h-5 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <h3 className="text-sm font-medium">{t('common.error')}</h3>
                  <p className="mt-1 text-sm">{error}</p>
                </div>
              </div>
            </div>
          )}

          {step === 'phone' ? renderPhoneStep() : renderVerificationStep()}
        </div>

        {/* Alternative Login Options */}
        <div className="text-center space-y-4">
          {/* Divider */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">
                {t('auth.phone.or')}
              </span>
            </div>
          </div>

          {/* Other Login Methods */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => router.push('/auth/login')}
              className="flex-1 py-2 px-4 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50"
            >
              {t('auth.phone.emailLogin')}
            </button>
            <button
              onClick={() => router.push('/auth/phone/register')}
              className="flex-1 py-2 px-4 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-opacity-50"
            >
              {t('auth.phone.register')}
            </button>
          </div>
        </div>

        {/* Security Notice */}
        <div className="bg-blue-50 dark:bg-blue-900 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <div>
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300">
                {t('auth.phone.securityNotice.title')}
              </h3>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-400">
                {t('auth.phone.securityNotice.message')}
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-gray-500 dark:text-gray-400">
          <p>
            {t('auth.phone.footer.privacy')}{' '}
            <button className="underline hover:text-gray-700 dark:hover:text-gray-300">
              {t('auth.agreements.privacyPolicy')}
            </button>
            {' '}{t('common.and')}{' '}
            <button className="underline hover:text-gray-700 dark:hover:text-gray-300">
              {t('auth.agreements.termsOfService')}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}

export default PhoneLogin