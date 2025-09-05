'use client'
import { useTranslation } from 'react-i18next'
import { useEffect, useState } from 'react'
import {
  RiCameraLine,
  RiCheckLine,
  RiCloseLine,
  RiErrorWarningLine,
  RiFileUploadLine,
  RiIdCardLine,
  RiInformationLine,
  RiTimeLine,
  RiUserLine,
} from '@remixicon/react'
import Button from '../../base/button'
import Input from '../../base/input'
import Select from '../../base/select'
import Toast from '../../base/toast'
import { getRealNameVerificationStatus, submitRealNameVerification, resubmitRealNameVerification } from '@/service/common'
import type { RealNameVerificationStatus, IDType } from '@/models/common'

type VerificationStep = 'info' | 'documents' | 'review' | 'submit'

const IDTypeOptions = [
  { value: 'national_id', name: 'National ID Card' },
  { value: 'passport', name: 'Passport' },
  { value: 'drivers_license', name: 'Driver\'s License' },
  { value: 'other', name: 'Other' },
]

export default function RealNameVerification() {
  const { t } = useTranslation()
  const [currentStep, setCurrentStep] = useState<VerificationStep>('info')
  const [loading, setLoading] = useState(false)
  const [verificationStatus, setVerificationStatus] = useState<RealNameVerificationStatus | null>(null)
  
  // Form data
  const [formData, setFormData] = useState({
    realName: '',
    idType: 'national_id' as IDType,
    idNumber: '',
  })
  
  // Document files
  const [documentFront, setDocumentFront] = useState<File | null>(null)
  const [documentBack, setDocumentBack] = useState<File | null>(null)
  const [frontPreview, setFrontPreview] = useState<string | null>(null)
  const [backPreview, setBackPreview] = useState<string | null>(null)

  // Load current verification status
  useEffect(() => {
    loadVerificationStatus()
  }, [])

  const loadVerificationStatus = async () => {
    try {
      setLoading(true)
      const status = await getRealNameVerificationStatus()
      setVerificationStatus(status)
      
      if (status && status.status === 'pending') {
        setCurrentStep('submit')
      } else if (status && status.status === 'rejected') {
        setCurrentStep('info')
        // Pre-fill form with existing data for resubmission
        setFormData({
          realName: status.real_name || '',
          idType: status.id_type as IDType || 'national_id',
          idNumber: '', // Don't pre-fill sensitive data
        })
      }
    } catch (error) {
      console.error('Failed to load verification status:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: keyof typeof formData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleFileSelect = (type: 'front' | 'back', file: File) => {
    if (!file.type.startsWith('image/')) {
      Toast.notify({
        type: 'error',
        message: t('common.realNameVerification.invalidImageFormat'),
      })
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      Toast.notify({
        type: 'error',
        message: t('common.realNameVerification.fileTooLarge'),
      })
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const result = e.target?.result as string
      if (type === 'front') {
        setDocumentFront(file)
        setFrontPreview(result)
      } else {
        setDocumentBack(file)
        setBackPreview(result)
      }
    }
    reader.readAsDataURL(file)
  }

  const handleSubmit = async () => {
    try {
      setLoading(true)
      
      const submitData = new FormData()
      submitData.append('real_name', formData.realName)
      submitData.append('id_type', formData.idType)
      submitData.append('id_number', formData.idNumber)
      
      if (documentFront) {
        submitData.append('document_front', documentFront)
      }
      if (documentBack) {
        submitData.append('document_back', documentBack)
      }

      let response
      if (verificationStatus?.status === 'rejected' && verificationStatus.id) {
        // Resubmit existing verification
        response = await resubmitRealNameVerification(verificationStatus.id, submitData)
      } else {
        // Submit new verification
        response = await submitRealNameVerification(submitData)
      }

      Toast.notify({
        type: 'success',
        message: t('common.realNameVerification.submitSuccess'),
      })

      // Reload verification status
      await loadVerificationStatus()
    } catch (error: any) {
      Toast.notify({
        type: 'error',
        message: error.message || t('common.realNameVerification.submitFailed'),
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusDisplay = () => {
    if (!verificationStatus) return null

    const statusConfig = {
      pending: {
        icon: <RiTimeLine className="w-5 h-5 text-amber-600" />,
        text: t('common.realNameVerification.statusPending'),
        description: t('common.realNameVerification.statusPendingDesc'),
        bgColor: 'bg-amber-50',
        textColor: 'text-amber-800',
        borderColor: 'border-amber-200',
      },
      approved: {
        icon: <RiCheckLine className="w-5 h-5 text-green-600" />,
        text: t('common.realNameVerification.statusApproved'),
        description: t('common.realNameVerification.statusApprovedDesc'),
        bgColor: 'bg-green-50',
        textColor: 'text-green-800',
        borderColor: 'border-green-200',
      },
      rejected: {
        icon: <RiErrorWarningLine className="w-5 h-5 text-red-600" />,
        text: t('common.realNameVerification.statusRejected'),
        description: verificationStatus.rejection_reason || t('common.realNameVerification.statusRejectedDesc'),
        bgColor: 'bg-red-50',
        textColor: 'text-red-800',
        borderColor: 'border-red-200',
      },
      expired: {
        icon: <RiCloseLine className="w-5 h-5 text-gray-600" />,
        text: t('common.realNameVerification.statusExpired'),
        description: t('common.realNameVerification.statusExpiredDesc'),
        bgColor: 'bg-gray-50',
        textColor: 'text-gray-800',
        borderColor: 'border-gray-200',
      },
    }

    const config = statusConfig[verificationStatus.status as keyof typeof statusConfig]
    if (!config) return null

    return (
      <div className={`rounded-lg border p-4 ${config.bgColor} ${config.borderColor}`}>
        <div className="flex items-start space-x-3">
          {config.icon}
          <div className="flex-1">
            <h3 className={`text-sm font-medium ${config.textColor}`}>
              {config.text}
            </h3>
            <p className={`mt-1 text-sm ${config.textColor} opacity-80`}>
              {config.description}
            </p>
            {verificationStatus.created_at && (
              <p className={`mt-1 text-xs ${config.textColor} opacity-60`}>
                {t('common.realNameVerification.submittedAt')}: {new Date(verificationStatus.created_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 'info':
        return (
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('common.realNameVerification.realName')} *
              </label>
              <Input
                value={formData.realName}
                onChange={(e) => handleInputChange('realName', e.target.value)}
                placeholder={t('common.realNameVerification.realNamePlaceholder')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('common.realNameVerification.idType')} *
              </label>
              <Select
                value={formData.idType}
                onSelect={(value) => handleInputChange('idType', value)}
                items={IDTypeOptions}
                placeholder={t('common.realNameVerification.selectIdType')}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('common.realNameVerification.idNumber')} *
              </label>
              <Input
                value={formData.idNumber}
                onChange={(e) => handleInputChange('idNumber', e.target.value)}
                placeholder={t('common.realNameVerification.idNumberPlaceholder')}
                type="password"
              />
            </div>
          </div>
        )

      case 'documents':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <RiIdCardLine className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {t('common.realNameVerification.uploadDocuments')}
              </h3>
              <p className="text-sm text-gray-600">
                {t('common.realNameVerification.uploadDocumentsDesc')}
              </p>
            </div>

            {/* Front Document */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('common.realNameVerification.documentFront')} *
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                {frontPreview ? (
                  <div className="relative">
                    <img src={frontPreview} alt="Document front" className="w-full h-48 object-cover rounded" />
                    <button
                      onClick={() => {
                        setDocumentFront(null)
                        setFrontPreview(null)
                      }}
                      className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                    >
                      <RiCloseLine className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center cursor-pointer hover:bg-gray-50 rounded p-4">
                    <RiCameraLine className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">{t('common.realNameVerification.clickToUpload')}</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleFileSelect('front', file)
                      }}
                    />
                  </label>
                )}
              </div>
            </div>

            {/* Back Document */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('common.realNameVerification.documentBack')}
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
                {backPreview ? (
                  <div className="relative">
                    <img src={backPreview} alt="Document back" className="w-full h-48 object-cover rounded" />
                    <button
                      onClick={() => {
                        setDocumentBack(null)
                        setBackPreview(null)
                      }}
                      className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                    >
                      <RiCloseLine className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <label className="flex flex-col items-center cursor-pointer hover:bg-gray-50 rounded p-4">
                    <RiCameraLine className="w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-sm text-gray-600">{t('common.realNameVerification.clickToUpload')}</span>
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleFileSelect('back', file)
                      }}
                    />
                  </label>
                )}
              </div>
            </div>
          </div>
        )

      case 'review':
        return (
          <div className="space-y-6">
            <div className="text-center">
              <RiInformationLine className="w-12 h-12 text-blue-500 mx-auto mb-3" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {t('common.realNameVerification.reviewInformation')}
              </h3>
              <p className="text-sm text-gray-600">
                {t('common.realNameVerification.reviewInformationDesc')}
              </p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600">{t('common.realNameVerification.realName')}:</span>
                <span className="text-sm text-gray-900">{formData.realName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600">{t('common.realNameVerification.idType')}:</span>
                <span className="text-sm text-gray-900">
                  {IDTypeOptions.find(opt => opt.value === formData.idType)?.name}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600">{t('common.realNameVerification.idNumber')}:</span>
                <span className="text-sm text-gray-900">{'*'.repeat(formData.idNumber.length - 4) + formData.idNumber.slice(-4)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm font-medium text-gray-600">{t('common.realNameVerification.documents')}:</span>
                <span className="text-sm text-gray-900">
                  {documentFront ? '✓' : '✗'} {t('common.realNameVerification.front')} / 
                  {documentBack ? '✓' : '✗'} {t('common.realNameVerification.back')}
                </span>
              </div>
            </div>
          </div>
        )

      case 'submit':
        return (
          <div className="space-y-6">
            {getStatusDisplay()}
            
            {!verificationStatus && (
              <div className="text-center">
                <RiCheckLine className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {t('common.realNameVerification.submissionComplete')}
                </h3>
                <p className="text-sm text-gray-600">
                  {t('common.realNameVerification.submissionCompleteDesc')}
                </p>
              </div>
            )}
          </div>
        )

      default:
        return null
    }
  }

  const canProceedToNextStep = () => {
    switch (currentStep) {
      case 'info':
        return formData.realName && formData.idType && formData.idNumber
      case 'documents':
        return documentFront !== null
      case 'review':
        return true
      default:
        return false
    }
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 'info':
        return t('common.realNameVerification.stepInfo')
      case 'documents':
        return t('common.realNameVerification.stepDocuments')
      case 'review':
        return t('common.realNameVerification.stepReview')
      case 'submit':
        return t('common.realNameVerification.stepSubmit')
      default:
        return ''
    }
  }

  if (loading && !verificationStatus) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center space-x-2 mb-4">
          <RiUserLine className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">
            {t('common.realNameVerification.title')}
          </h1>
        </div>
        <p className="text-gray-600">
          {t('common.realNameVerification.description')}
        </p>
      </div>

      {/* Progress Steps */}
      {currentStep !== 'submit' && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {['info', 'documents', 'review'].map((step, index) => (
              <div key={step} className="flex items-center">
                <div className={`flex items-center justify-center w-8 h-8 rounded-full border-2 ${
                  currentStep === step ? 'bg-blue-600 border-blue-600 text-white' :
                  ['info', 'documents'].indexOf(currentStep) > index ? 'bg-green-600 border-green-600 text-white' :
                  'border-gray-300 text-gray-400'
                }`}>
                  {['info', 'documents'].indexOf(currentStep) > index ? (
                    <RiCheckLine className="w-4 h-4" />
                  ) : (
                    <span className="text-sm">{index + 1}</span>
                  )}
                </div>
                {index < 2 && (
                  <div className={`w-16 h-1 mx-2 ${
                    ['info', 'documents'].indexOf(currentStep) > index ? 'bg-green-600' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-6">{getStepTitle()}</h2>
        </div>
      )}

      {/* Step Content */}
      <div className="mb-8">
        {renderStepContent()}
      </div>

      {/* Actions */}
      {currentStep !== 'submit' && (
        <div className="flex justify-between">
          <div>
            {currentStep !== 'info' && (
              <Button
                variant="ghost"
                onClick={() => {
                  const steps: VerificationStep[] = ['info', 'documents', 'review']
                  const currentIndex = steps.indexOf(currentStep)
                  if (currentIndex > 0) {
                    setCurrentStep(steps[currentIndex - 1])
                  }
                }}
              >
                {t('common.realNameVerification.previous')}
              </Button>
            )}
          </div>
          
          <div className="space-x-3">
            {currentStep === 'review' ? (
              <Button
                variant="primary"
                onClick={handleSubmit}
                loading={loading}
                disabled={loading || !canProceedToNextStep()}
              >
                {verificationStatus?.status === 'rejected' 
                  ? t('common.realNameVerification.resubmit')
                  : t('common.realNameVerification.submit')
                }
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={() => {
                  const steps: VerificationStep[] = ['info', 'documents', 'review']
                  const currentIndex = steps.indexOf(currentStep)
                  if (currentIndex < steps.length - 1) {
                    setCurrentStep(steps[currentIndex + 1])
                  }
                }}
                disabled={!canProceedToNextStep()}
              >
                {t('common.realNameVerification.next')}
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Resubmit option for rejected verifications */}
      {verificationStatus?.status === 'rejected' && currentStep === 'submit' && (
        <div className="mt-6">
          <Button
            variant="primary"
            onClick={() => setCurrentStep('info')}
          >
            {t('common.realNameVerification.updateAndResubmit')}
          </Button>
        </div>
      )}
    </div>
  )
}