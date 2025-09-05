'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useRouter } from 'next/navigation'
import PhoneVerification from './PhoneVerification'
import AgreementModal from '../common/AgreementModal'
import { usePhoneAuth, PhoneRegistrationData } from '../../hooks/usePhoneAuth'

interface RegistrationStep {
  id: 'phone' | 'verification' | 'agreements' | 'info'
  title: string
  description: string
}

const PhoneRegistration: React.FC = () => {
  const { t } = useTranslation()
  const router = useRouter()
  const phoneInputRef = useRef<HTMLInputElement>(null)
  
  // Phone auth hook
  const {
    loading,
    error,
    registerWithPhone,
    sendSMSCode,
    checkPhoneAvailability,
    fetchAgreements,
    clearError,
  } = usePhoneAuth()

  // Form state
  const [currentStep, setCurrentStep] = useState<RegistrationStep['id']>('phone')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [verificationCode, setVerificationCode] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [language, setLanguage] = useState('zh-CN')
  
  // Agreement state
  const [agreements, setAgreements] = useState<any>({})
  const [consents, setConsents] = useState({
    privacy_policy: false,
    terms_of_service: false,
  })
  const [showAgreementModal, setShowAgreementModal] = useState(false)
  const [currentAgreementType, setCurrentAgreementType] = useState<'privacy_policy' | 'terms_of_service'>('privacy_policy')

  // Form validation
  const [phoneError, setPhoneError] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const steps: RegistrationStep[] = [
    { id: 'phone', title: t('auth.phone.steps.phone'), description: t('auth.phone.steps.phoneDesc') },
    { id: 'verification', title: t('auth.phone.steps.verification'), description: t('auth.phone.steps.verificationDesc') },
    { id: 'agreements', title: t('auth.phone.steps.agreements'), description: t('auth.phone.steps.agreementsDesc') },
    { id: 'info', title: t('auth.phone.steps.info'), description: t('auth.phone.steps.infoDesc') },
  ]

  const currentStepIndex = steps.findIndex(step => step.id === currentStep)
  const currentStepInfo = steps[currentStepIndex]

  // Load agreements on mount
  useEffect(() => {
    const loadAgreements = async () => {
      const result = await fetchAgreements()
      if (result.success && result.agreements) {
        setAgreements(result.agreements)
      }
    }
    loadAgreements()
  }, [fetchAgreements])

  // Auto-focus phone input
  useEffect(() => {
    if (currentStep === 'phone' && phoneInputRef.current) {
      phoneInputRef.current.focus()
    }
  }, [currentStep])

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

  const handlePhoneSubmit = async () => {
    clearError()
    setPhoneError('')

    const normalizedPhone = normalizePhoneNumber(phoneNumber)
    
    if (!validatePhoneNumber(phoneNumber)) {
      setPhoneError(t('auth.phone.errors.invalidPhone'))
      return
    }

    // Check phone availability
    const availability = await checkPhoneAvailability(normalizedPhone)
    if (availability.registered) {
      setPhoneError(t('auth.phone.errors.phoneRegistered'))
      return
    }

    // Send SMS verification code
    const result = await sendSMSCode(normalizedPhone, 'registration')
    if (result.success) {
      setPhoneNumber(normalizedPhone)
      setCurrentStep('verification')
    }
  }

  const handleVerificationSubmit = () => {
    if (verificationCode.length < 4) {
      return
    }
    setCurrentStep('agreements')
  }

  const handleAgreementToggle = (type: 'privacy_policy' | 'terms_of_service') => {
    setConsents(prev => ({
      ...prev,
      [type]: !prev[type]
    }))
  }

  const handleViewAgreement = (type: 'privacy_policy' | 'terms_of_service') => {
    setCurrentAgreementType(type)
    setShowAgreementModal(true)
  }

  const handleAgreementAccept = () => {
    setConsents(prev => ({
      ...prev,
      [currentAgreementType]: true
    }))
  }

  const handleAgreementsSubmit = () => {
    if (consents.privacy_policy && consents.terms_of_service) {
      setCurrentStep('info')
    }
  }

  const handleRegistration = async () => {
    clearError()
    setPasswordError('')

    // Validate password if provided
    if (password && password.length < 8) {
      setPasswordError(t('auth.phone.errors.passwordTooShort'))
      return
    }

    // Prepare registration data
    const registrationData: PhoneRegistrationData = {
      phone_number: phoneNumber,
      verification_code: verificationCode,
      password: password || undefined,
      agreements: {
        privacy_policy: {
          version: agreements.privacy_policy?.version || '1.0',
          agreed: true
        },
        terms_of_service: {
          version: agreements.terms_of_service?.version || '1.0',
          agreed: true
        }
      },
      user_info: {
        nickname: nickname || undefined,
        preferred_language: language
      }
    }

    const result = await registerWithPhone(registrationData)
    
    if (result.success) {
      // Registration successful - redirect to dashboard or welcome page
      router.push('/dashboard')
    }
  }

  const handleBack = () => {
    const steps = ['phone', 'verification', 'agreements', 'info']
    const currentIndex = steps.indexOf(currentStep)
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1] as RegistrationStep['id'])
    }
  }

  const renderPhoneStep = () => (
    <div className="space-y-4">
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
          className={`w-full px-3 py-2 border rounded-lg transition-colors ${
            phoneError
              ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
          } dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100`}
          disabled={loading}
        />
        {phoneError && (
          <p className="mt-1 text-sm text-red-600 dark:text-red-400">{phoneError}</p>
        )}
      </div>
      
      <button
        onClick={handlePhoneSubmit}
        disabled={loading || !phoneNumber}
        className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
      >
        {loading ? t('common.loading') : t('auth.phone.sendCode')}
      </button>
    </div>
  )

  const renderVerificationStep = () => (
    <div className="space-y-6">
      <PhoneVerification
        phone={phoneNumber}
        onCodeChange={setVerificationCode}
        onResendCode={() => sendSMSCode(phoneNumber, 'registration')}
        loading={loading}
        error={error}
      />
      
      <div className="flex space-x-3">
        <button
          onClick={handleBack}
          className="flex-1 py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors"
        >
          {t('common.back')}
        </button>
        <button
          onClick={handleVerificationSubmit}
          disabled={verificationCode.length < 4}
          className="flex-1 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
        >
          {t('common.continue')}
        </button>
      </div>
    </div>
  )

  const renderAgreementsStep = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        {/* Privacy Policy */}
        <div className="flex items-start space-x-3">
          <input
            id="privacy_policy"
            type="checkbox"
            checked={consents.privacy_policy}
            onChange={() => handleAgreementToggle('privacy_policy')}
            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <div className="flex-1">
            <label htmlFor="privacy_policy" className="text-sm text-gray-700 dark:text-gray-300">
              {t('auth.phone.agreeToPrivacy')}
              <button
                type="button"
                onClick={() => handleViewAgreement('privacy_policy')}
                className="ml-1 text-blue-600 hover:text-blue-500 dark:text-blue-400 underline"
              >
                {t('auth.agreements.privacyPolicy')}
              </button>
            </label>
          </div>
        </div>

        {/* Terms of Service */}
        <div className="flex items-start space-x-3">
          <input
            id="terms_of_service"
            type="checkbox"
            checked={consents.terms_of_service}
            onChange={() => handleAgreementToggle('terms_of_service')}
            className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <div className="flex-1">
            <label htmlFor="terms_of_service" className="text-sm text-gray-700 dark:text-gray-300">
              {t('auth.phone.agreeToTerms')}
              <button
                type="button"
                onClick={() => handleViewAgreement('terms_of_service')}
                className="ml-1 text-blue-600 hover:text-blue-500 dark:text-blue-400 underline"
              >
                {t('auth.agreements.termsOfService')}
              </button>
            </label>
          </div>
        </div>
      </div>

      <div className="flex space-x-3">
        <button
          onClick={handleBack}
          className="flex-1 py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors"
        >
          {t('common.back')}
        </button>
        <button
          onClick={handleAgreementsSubmit}
          disabled={!consents.privacy_policy || !consents.terms_of_service}
          className="flex-1 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
        >
          {t('common.continue')}
        </button>
      </div>
    </div>
  )

  const renderInfoStep = () => (
    <div className="space-y-6">
      <div className="space-y-4">
        {/* Nickname */}
        <div>
          <label htmlFor="nickname" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('auth.phone.nickname')} ({t('common.optional')})
          </label>
          <input
            id="nickname"
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder={t('auth.phone.nicknamePlaceholder')}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:border-blue-500 focus:ring-blue-500 transition-colors"
            maxLength={50}
          />
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('auth.phone.password')} ({t('common.optional')})
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('auth.phone.passwordPlaceholder')}
            className={`w-full px-3 py-2 border rounded-lg transition-colors ${
              passwordError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
            } dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100`}
          />
          {passwordError && (
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">{passwordError}</p>
          )}
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            {t('auth.phone.passwordHint')}
          </p>
        </div>

        {/* Language */}
        <div>
          <label htmlFor="language" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            {t('auth.phone.preferredLanguage')}
          </label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100 rounded-lg focus:border-blue-500 focus:ring-blue-500 transition-colors"
          >
            <option value="zh-CN">{t('languages.zhCN')}</option>
            <option value="en-US">{t('languages.enUS')}</option>
          </select>
        </div>
      </div>

      <div className="flex space-x-3">
        <button
          onClick={handleBack}
          className="flex-1 py-2 px-4 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-colors"
        >
          {t('common.back')}
        </button>
        <button
          onClick={handleRegistration}
          disabled={loading}
          className="flex-1 py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium rounded-lg transition-colors disabled:cursor-not-allowed"
        >
          {loading ? t('common.loading') : t('auth.phone.completeRegistration')}
        </button>
      </div>
    </div>
  )

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 'phone':
        return renderPhoneStep()
      case 'verification':
        return renderVerificationStep()
      case 'agreements':
        return renderAgreementsStep()
      case 'info':
        return renderInfoStep()
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <h2 className="mt-6 text-3xl font-bold text-gray-900 dark:text-gray-100">
            {t('auth.phone.registration.title')}
          </h2>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            {t('auth.phone.registration.subtitle')}
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex justify-between">
          {steps.map((step, index) => (
            <div key={step.id} className="flex items-center">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                index <= currentStepIndex
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-600 dark:text-gray-400'
              }`}>
                {index < currentStepIndex ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <span className="text-sm font-medium">{index + 1}</span>
                )}
              </div>
              {index < steps.length - 1 && (
                <div className={`w-12 h-0.5 ${
                  index < currentStepIndex
                    ? 'bg-blue-600'
                    : 'bg-gray-300 dark:bg-gray-600'
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* Step Info */}
        <div className="text-center">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {currentStepInfo.title}
          </h3>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            {currentStepInfo.description}
          </p>
        </div>

        {/* Form */}
        <div className="bg-white dark:bg-gray-800 py-8 px-6 shadow rounded-lg">
          {/* Error Message */}
          {error && (
            <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 text-red-700 dark:text-red-300 rounded-lg">
              {error}
            </div>
          )}

          {renderCurrentStep()}
        </div>

        {/* Switch to Login */}
        <div className="text-center">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {t('auth.phone.alreadyHaveAccount')}{' '}
            <button
              onClick={() => router.push('/auth/phone/login')}
              className="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
            >
              {t('auth.phone.login')}
            </button>
          </p>
        </div>
      </div>

      {/* Agreement Modal */}
      <AgreementModal
        isOpen={showAgreementModal}
        onClose={() => setShowAgreementModal(false)}
        agreementType={currentAgreementType}
        agreement={agreements[currentAgreementType]}
        onAgree={handleAgreementAccept}
        showActions={true}
      />
    </div>
  )
}

export default PhoneRegistration