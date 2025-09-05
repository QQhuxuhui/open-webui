'use client'

import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import ReportModal from './ReportModal'

export interface ReportButtonProps {
  contentId: string
  contentType: 'text' | 'image' | 'video' | 'audio'
  contentSnapshot?: any
  className?: string
  variant?: 'default' | 'icon-only' | 'minimal'
  position?: 'inline' | 'hover' | 'always-visible'
  disabled?: boolean
  onReportSubmitted?: (reportId: string) => void
}

const ReportButton: React.FC<ReportButtonProps> = ({
  contentId,
  contentType,
  contentSnapshot,
  className = '',
  variant = 'default',
  position = 'hover',
  disabled = false,
  onReportSubmitted
}) => {
  const { t } = useTranslation()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  const getButtonText = () => {
    if (variant === 'icon-only') return ''
    return t('report.button.text', 'Report')
  }

  const getButtonStyles = () => {
    const baseStyles = "inline-flex items-center gap-1.5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-opacity-50"
    
    switch (variant) {
      case 'icon-only':
        return `${baseStyles} p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400`
      case 'minimal':
        return `${baseStyles} px-2 py-1 text-xs text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-50 dark:hover:bg-gray-800 rounded`
      default:
        return `${baseStyles} px-3 py-1.5 text-sm bg-red-50 hover:bg-red-100 text-red-600 dark:bg-red-900/20 dark:hover:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-md`
    }
  }

  const getVisibilityStyles = () => {
    if (position === 'always-visible') return 'opacity-100'
    if (position === 'hover') return isHovered ? 'opacity-100' : 'opacity-0'
    return 'opacity-100'
  }

  const handleClick = () => {
    if (disabled) return
    setIsModalOpen(true)
  }

  const handleReportSubmitted = (reportId: string) => {
    setIsModalOpen(false)
    onReportSubmitted?.(reportId)
  }

  const FlagIcon = () => (
    <svg
      className="w-4 h-4 flex-shrink-0"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 2H21l-3 6 3 6h-8.5l-1-2H5a2 2 0 00-2 2zm9-13.5V9"
      />
    </svg>
  )

  return (
    <div 
      className={`report-button-container ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <button
        onClick={handleClick}
        disabled={disabled}
        className={`${getButtonStyles()} ${getVisibilityStyles()}`}
        title={t('report.button.tooltip', 'Report this content')}
        aria-label={t('report.button.ariaLabel', 'Report content')}
      >
        <FlagIcon />
        {getButtonText() && (
          <span className="select-none">{getButtonText()}</span>
        )}
      </button>

      {isModalOpen && (
        <ReportModal
          contentId={contentId}
          contentType={contentType}
          contentSnapshot={contentSnapshot}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onReportSubmitted={handleReportSubmitted}
        />
      )}
    </div>
  )
}

export default ReportButton