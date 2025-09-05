'use client'

import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export interface AdminReportEntry {
  id: string
  content_id: string
  content_type: 'text' | 'image' | 'video' | 'audio'
  report_category: string
  report_reason: string
  status: 'pending' | 'reviewing' | 'resolved' | 'dismissed'
  created_at: string
  resolved_at?: string
}

export interface AdminReportPanelProps {
  className?: string
}

const STATUSES = ['pending', 'reviewing', 'resolved', 'dismissed'] as const
const CATEGORIES = [
  'inappropriate_content',
  'misinformation', 
  'technical_issue',
  'spam',
  'harassment',
  'other'
] as const

const AdminReportPanel: React.FC<AdminReportPanelProps> = ({ className = '' }) => {
  const { t } = useTranslation()
  const [reports, setReports] = useState<AdminReportEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(20)
  
  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  
  // Action states
  const [processingReports, setProcessingReports] = useState<Set<string>>(new Set())
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set())

  const fetchReports = async (
    pageNum: number = 1,
    status?: string,
    category?: string
  ) => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: pageNum.toString(),
        page_size: pageSize.toString()
      })

      if (status) params.append('status', status)
      if (category) params.append('category', category)

      const response = await fetch(`/api/reports/admin/reports?${params}`, {
        credentials: 'include'
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || t('admin.reports.fetchError', 'Failed to fetch reports'))
      }

      if (result.success) {
        setReports(result.reports || [])
        setTotal(result.total || 0)
        setPage(pageNum)
      } else {
        throw new Error(result.message || t('admin.reports.fetchError', 'Failed to fetch reports'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.reports.fetchError', 'Failed to fetch reports'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReports(1, statusFilter, categoryFilter)
  }, [statusFilter, categoryFilter])

  const updateReportStatus = async (reportId: string, newStatus: string, notes?: string) => {
    setProcessingReports(prev => new Set(prev).add(reportId))

    try {
      const response = await fetch(`/api/reports/admin/reports/${reportId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ status: newStatus, notes })
      })

      const result = await response.json()

      if (!response.ok) {
        throw new Error(result.message || t('admin.reports.updateError', 'Failed to update report'))
      }

      if (result.success) {
        // Refresh the reports list
        await fetchReports(page, statusFilter, categoryFilter)
      } else {
        throw new Error(result.message || t('admin.reports.updateError', 'Failed to update report'))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.reports.updateError', 'Failed to update report'))
    } finally {
      setProcessingReports(prev => {
        const newSet = new Set(prev)
        newSet.delete(reportId)
        return newSet
      })
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
      case 'reviewing':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800'
      case 'resolved':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
      case 'dismissed':
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-600'
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-600'
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

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className={`admin-report-panel bg-white dark:bg-gray-800 rounded-lg shadow-sm ${className}`}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {t('admin.reports.title', 'Content Reports')}
          </h2>
          <button
            onClick={() => fetchReports(page, statusFilter, categoryFilter)}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? t('common.loading', 'Loading...') : t('common.refresh', 'Refresh')}
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('admin.reports.filterByStatus', 'Filter by Status')}
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="">{t('admin.reports.allStatuses', 'All Statuses')}</option>
              {STATUSES.map(status => (
                <option key={status} value={status}>
                  {t(`report.status.${status}`, status)}
                </option>
              ))}
            </select>
          </div>
          
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('admin.reports.filterByCategory', 'Filter by Category')}
            </label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-gray-100"
            >
              <option value="">{t('admin.reports.allCategories', 'All Categories')}</option>
              {CATEGORIES.map(category => (
                <option key={category} value={category}>
                  {getCategoryLabel(category)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 mb-6">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
                <button
                  onClick={() => fetchReports(page, statusFilter, categoryFilter)}
                  className="ml-2 text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline"
                >
                  {t('common.retry', 'Retry')}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Reports Table */}
        <div className="overflow-x-auto">
          <table className="w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {t('admin.reports.table.content', 'Content')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {t('admin.reports.table.category', 'Category')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {t('admin.reports.table.status', 'Status')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {t('admin.reports.table.date', 'Date')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                  {t('admin.reports.table.actions', 'Actions')}
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {loading && reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2"></div>
                      <span className="text-gray-500 dark:text-gray-400">
                        {t('common.loading', 'Loading...')}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : reports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                    {t('admin.reports.noReports', 'No reports found')}
                  </td>
                </tr>
              ) : (
                reports.map((report) => (
                  <tr key={report.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <div className="flex items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs uppercase text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                              {report.content_type}
                            </span>
                            <span className="text-xs text-gray-400 dark:text-gray-500">
                              ID: {report.content_id.slice(0, 8)}...
                            </span>
                          </div>
                          <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                            {report.report_reason}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {getCategoryLabel(report.report_category)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${getStatusColor(report.status)}`}>
                        {t(`report.status.${report.status}`, report.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {formatDate(report.created_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        {report.status === 'pending' && (
                          <>
                            <button
                              onClick={() => updateReportStatus(report.id, 'reviewing')}
                              disabled={processingReports.has(report.id)}
                              className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {processingReports.has(report.id) ? '...' : t('admin.reports.actions.review', 'Review')}
                            </button>
                            <button
                              onClick={() => updateReportStatus(report.id, 'dismissed')}
                              disabled={processingReports.has(report.id)}
                              className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {processingReports.has(report.id) ? '...' : t('admin.reports.actions.dismiss', 'Dismiss')}
                            </button>
                          </>
                        )}
                        {report.status === 'reviewing' && (
                          <>
                            <button
                              onClick={() => updateReportStatus(report.id, 'resolved')}
                              disabled={processingReports.has(report.id)}
                              className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {processingReports.has(report.id) ? '...' : t('admin.reports.actions.resolve', 'Resolve')}
                            </button>
                            <button
                              onClick={() => updateReportStatus(report.id, 'dismissed')}
                              disabled={processingReports.has(report.id)}
                              className="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                              {processingReports.has(report.id) ? '...' : t('admin.reports.actions.dismiss', 'Dismiss')}
                            </button>
                          </>
                        )}
                        {(report.status === 'resolved' || report.status === 'dismissed') && (
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {t('admin.reports.completed', 'Completed')}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {t('admin.reports.pagination.showing', 'Showing {{start}} to {{end}} of {{total}} reports', {
                start: (page - 1) * pageSize + 1,
                end: Math.min(page * pageSize, total),
                total
              })}
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => fetchReports(page - 1, statusFilter, categoryFilter)}
                disabled={page <= 1 || loading}
                className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {t('common.previous', 'Previous')}
              </button>
              
              <span className="px-3 py-1 text-sm text-gray-700 dark:text-gray-300">
                {page} / {totalPages}
              </span>
              
              <button
                onClick={() => fetchReports(page + 1, statusFilter, categoryFilter)}
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
  )
}

export default AdminReportPanel