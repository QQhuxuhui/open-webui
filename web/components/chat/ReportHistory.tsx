'use client'

import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export interface ReportHistoryEntry {
  id: string
  content_id: string
  content_type: 'text' | 'image' | 'video' | 'audio'
  report_category: string
  report_reason: string
  status: 'pending' | 'reviewing' | 'resolved' | 'dismissed'
  created_at: string
  resolved_at?: string
}

export interface ReportHistoryProps {
  isOpen: boolean
  onClose: () => void
  className?: string
}

const ReportHistory: React.FC<ReportHistoryProps> = ({
  isOpen,
  onClose,
  className = ''
}) => {
  const { t } = useTranslation()
  const [reports, setReports] = useState<ReportHistoryEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(10)

  const fetchReports = async (pageNum: number = 1) => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`/api/reports/my-reports?page=${pageNum}&page_size=${pageSize}`, {
        credentials: 'include'
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || t('report.history.fetchError', 'Failed to fetch reports'))
      }

      if (result.success) {
        setReports(result.reports || [])
        setTotal(result.total || 0)
        setPage(pageNum)
      } else {
        throw new Error(result.message || t('report.history.fetchError', 'Failed to fetch reports'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('report.history.fetchError', 'Failed to fetch reports'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchReports(1)
    }
  }, [isOpen])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20'
      case 'reviewing':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20'
      case 'resolved':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
      case 'dismissed':
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20'
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20'
    }
  }

  const getCategoryLabel = (category: string) => {
    const categoryMap: Record<string, string> = {
      inappropriate_content: t('report.categories.inappropriate', 'Inappropriate Content'),
      misinformation: t('report.categories.misinformation', 'Misinformation'),
      technical_issue: t('report.categories.technical', 'Technical Issue'),
      spam: t('report.categories.spam', 'Spam'),
      harassment: t('report.categories.harassment', 'Harassment'),
      other: t('report.categories.other', 'Other')
    }
    return categoryMap[category] || category
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      onClose()
    }
  }

  if (!isOpen) return null

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {t('report.history.title', 'My Reports')}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 focus:outline-none"
              aria-label={t('common.close', 'Close')}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="overflow-y-auto max-h-[calc(90vh-200px)]">
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="ml-2 text-gray-600 dark:text-gray-400">
                  {t('common.loading', 'Loading...')}
                </span>
              </div>
            )}

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 mb-4">
                <div className="flex">
                  <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
                    <button
                      onClick={() => fetchReports(page)}
                      className="ml-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline"
                    >
                      {t('common.retry', 'Retry')}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {!loading && !error && reports.length === 0 && (
              <div className="text-center py-12">
                <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
                  <svg className="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 2H21l-3 6 3 6h-8.5l-1-2H5a2 2 0 00-2 2zm9-13.5V9" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  {t('report.history.empty.title', 'No Reports Yet')}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t('report.history.empty.description', 'You haven\'t submitted any reports yet.')}
                </p>
              </div>
            )}

            {!loading && !error && reports.length > 0 && (
              <div className="space-y-4">
                {reports.map((report) => (
                  <div key={report.id} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(report.status)}`}>
                            {t(`report.status.${report.status}`, report.status)}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {getCategoryLabel(report.report_category)}
                          </span>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {report.content_type.toUpperCase()}
                          </span>
                        </div>
                        
                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 line-clamp-2">
                          {report.report_reason}
                        </p>
                        
                        <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                          <span>
                            {t('report.history.submitted')}: {formatDate(report.created_at)}
                          </span>
                          {report.resolved_at && (
                            <span>
                              {t('report.history.resolved')}: {formatDate(report.resolved_at)}
                            </span>
                          )}
                        </div>
                      </div>
                      
                      <div className="text-xs text-gray-400 dark:text-gray-500 ml-4">
                        ID: {report.id.slice(0, 8)}...
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {t('report.history.pagination.showing', 'Showing {{start}} to {{end}} of {{total}} reports', {
                  start: (page - 1) * pageSize + 1,
                  end: Math.min(page * pageSize, total),
                  total
                })}
              </div>
              
              <div className="flex gap-2">
                <button
                  onClick={() => fetchReports(page - 1)}
                  disabled={page <= 1 || loading}
                  className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('common.previous', 'Previous')}
                </button>
                
                <span className="px-3 py-1 text-sm text-gray-700 dark:text-gray-300">
                  {page} / {totalPages}
                </span>
                
                <button
                  onClick={() => fetchReports(page + 1)}
                  disabled={page >= totalPages || loading}
                  className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {t('common.next', 'Next')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ReportHistory