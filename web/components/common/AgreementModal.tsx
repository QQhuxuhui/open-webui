'use client'

import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Agreement } from '../../hooks/usePhoneAuth'

export interface AgreementModalProps {
  isOpen: boolean
  onClose: () => void
  agreementType: 'privacy_policy' | 'terms_of_service'
  agreement?: Agreement
  onAgree?: () => void
  showActions?: boolean
}

const AgreementModal: React.FC<AgreementModalProps> = ({
  isOpen,
  onClose,
  agreementType,
  agreement,
  onAgree,
  showActions = false,
}) => {
  const { t } = useTranslation()
  const [isScrolledToBottom, setIsScrolledToBottom] = useState(false)

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement
    const threshold = 10 // pixels from bottom
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - threshold
    setIsScrolledToBottom(isAtBottom)
  }

  // Reset scroll state when modal opens
  useEffect(() => {
    if (isOpen) {
      setIsScrolledToBottom(false)
    }
  }, [isOpen])

  // Handle keyboard events
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'auto'
    }
  }, [isOpen, onClose])

  const getTitle = () => {
    return agreementType === 'privacy_policy'
      ? t('auth.agreements.privacyPolicy')
      : t('auth.agreements.termsOfService')
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateString
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-4xl bg-white dark:bg-gray-800 rounded-lg shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {getTitle()}
              </h3>
              {agreement && (
                <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                  <span>{t('auth.agreements.version')}: {agreement.version}</span>
                  <span>{t('auth.agreements.lastUpdated')}: {formatDate(agreement.last_updated)}</span>
                </div>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              aria-label={t('common.close')}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div
            className="max-h-96 overflow-y-auto p-6 prose prose-sm dark:prose-invert max-w-none"
            onScroll={handleScroll}
          >
            {agreement ? (
              <div className="whitespace-pre-wrap text-gray-700 dark:text-gray-300 leading-relaxed">
                {agreement.content}
              </div>
            ) : (
              <div className="flex justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
            )}
          </div>

          {/* Footer */}
          {showActions && (
            <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 rounded-b-lg">
              <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
                {!isScrolledToBottom && (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                    <span>{t('auth.agreements.scrollToBottom')}</span>
                  </>
                )}
              </div>
              
              <div className="flex space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-300 dark:hover:bg-gray-700 rounded-md transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  onClick={() => {
                    onAgree?.()
                    onClose()
                  }}
                  disabled={!isScrolledToBottom}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors"
                >
                  {t('auth.agreements.agree')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AgreementModal