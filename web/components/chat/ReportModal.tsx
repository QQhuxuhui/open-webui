'use client'

import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'

export interface ReportModalProps {
  contentId: string
  contentType: 'text' | 'image' | 'video' | 'audio'
  contentSnapshot?: any
  isOpen: boolean
  onClose: () => void
  onReportSubmitted: (reportId: string) => void
}

export interface ReportFormData {
  category: string
  reason: string
  attachments: File[]
}

const REPORT_CATEGORIES = [
  { key: 'inappropriate_content', label: 'report.categories.inappropriate' },
  { key: 'misinformation', label: 'report.categories.misinformation' },
  { key: 'technical_issue', label: 'report.categories.technical' },
  { key: 'spam', label: 'report.categories.spam' },
  { key: 'harassment', label: 'report.categories.harassment' },
  { key: 'other', label: 'report.categories.other' }
] as const

const ReportModal: React.FC<ReportModalProps> = ({
  contentId,
  contentType,
  contentSnapshot,
  isOpen,
  onClose,
  onReportSubmitted
}) => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<ReportFormData>({
    category: '',
    reason: '',
    attachments: []
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleCategoryChange = (category: string) => {
    setFormData(prev => ({ ...prev, category }))
    setError(null)
  }

  const handleReasonChange = (reason: string) => {
    setFormData(prev => ({ ...prev, reason }))
    setError(null)
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    const validFiles = files.filter(file => {
      // Limit file size to 10MB and allow common image types and documents
      const maxSize = 10 * 1024 * 1024
      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf', 'text/plain']
      return file.size <= maxSize && allowedTypes.includes(file.type)
    })

    if (validFiles.length !== files.length) {
      setError(t('report.errors.invalidFiles', 'Some files were not added due to size or type restrictions'))
    }

    setFormData(prev => ({
      ...prev,
      attachments: [...prev.attachments, ...validFiles].slice(0, 5) // Max 5 files
    }))
  }

  const removeAttachment = (index: number) => {
    setFormData(prev => ({
      ...prev,
      attachments: prev.attachments.filter((_, i) => i !== index)
    }))
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    
    if (!formData.category) {
      setError(t('report.errors.categoryRequired', 'Please select a report category'))
      return
    }

    if (!formData.reason.trim()) {
      setError(t('report.errors.reasonRequired', 'Please provide a reason for reporting'))
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const submitFormData = new FormData()
      submitFormData.append('content_id', contentId)
      submitFormData.append('content_type', contentType)
      submitFormData.append('report_category', formData.category)
      submitFormData.append('report_reason', formData.reason)
      
      if (contentSnapshot) {
        submitFormData.append('content_snapshot', JSON.stringify(contentSnapshot))
      }

      formData.attachments.forEach((file, index) => {
        submitFormData.append(`attachment_${index}`, file)
      })

      const response = await fetch('/api/reports/submit', {
        method: 'POST',
        body: submitFormData,
        credentials: 'include'
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.error || t('report.errors.submitFailed', 'Failed to submit report'))
      }

      onReportSubmitted(result.report_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('report.errors.submitFailed', 'Failed to submit report'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget && !isSubmitting) {
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              {t('report.modal.title', 'Report Content')}
            </h2>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none"
              aria-label={t('common.close', 'Close')}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Content Info */}
            <div className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700 p-3 rounded">
              <div className="flex items-center gap-2">
                <span className="font-medium">{t('report.modal.contentType')}:</span>
                <span className="capitalize">{contentType}</span>
              </div>
              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {t('report.modal.contentId')}: {contentId.slice(0, 8)}...
              </div>
            </div>

            {/* Report Category */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('report.modal.categoryLabel', 'Report Category')} *
              </label>
              <div className="space-y-2">
                {REPORT_CATEGORIES.map((category) => (
                  <label key={category.key} className="flex items-center">
                    <input
                      type="radio"
                      name="category"
                      value={category.key}
                      checked={formData.category === category.key}
                      onChange={(e) => handleCategoryChange(e.target.value)}
                      disabled={isSubmitting}
                      className="mr-2 text-red-600 focus:ring-red-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {t(category.label, category.key.replace('_', ' '))}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Report Reason */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('report.modal.reasonLabel', 'Reason for Report')} *
              </label>
              <textarea
                value={formData.reason}
                onChange={(e) => handleReasonChange(e.target.value)}
                disabled={isSubmitting}
                rows={4}
                maxLength={1000}
                placeholder={t('report.modal.reasonPlaceholder', 'Please describe why you are reporting this content...')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 dark:bg-gray-700 dark:text-gray-100 resize-none"
              />
              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
                {formData.reason.length}/1000
              </div>
            </div>

            {/* File Attachments */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('report.modal.attachmentsLabel', 'Attachments (Optional)')}
              </label>
              <div className="space-y-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*,.pdf,.txt"
                  onChange={handleFileSelect}
                  disabled={isSubmitting}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isSubmitting || formData.attachments.length >= 5}
                  className="w-full px-3 py-2 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-md hover:border-gray-400 dark:hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 text-sm text-gray-600 dark:text-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('report.modal.selectFiles', 'Select Files')} (max 5, 10MB each)
                </button>
                
                {formData.attachments.length > 0 && (
                  <div className="space-y-1">
                    {formData.attachments.map((file, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 p-2 rounded">
                        <span className="text-sm text-gray-700 dark:text-gray-300 truncate flex-1">
                          {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                        </span>
                        <button
                          type="button"
                          onClick={() => removeAttachment(index)}
                          disabled={isSubmitting}
                          className="ml-2 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                          aria-label={t('common.remove', 'Remove')}
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3">
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('common.cancel', 'Cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !formData.category || !formData.reason.trim()}
                className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
              >
                {isSubmitting ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"></circle>
                      <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"></path>
                    </svg>
                    {t('report.modal.submitting', 'Submitting...')}
                  </>
                ) : (
                  t('report.modal.submit', 'Submit Report')
                )}
              </button>
            </div>
          </form>

          {/* Terms Notice */}
          <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">
            {t('report.modal.termsNotice', 'By submitting this report, you agree that the information provided is accurate and you understand that false reports may result in account restrictions.')}
          </div>
        </div>
      </div>
    </div>
  )
}

export default ReportModal