/**
 * AI Labeling Hook for managing AI content labels and detection
 */
import { useState, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

export interface AILabelInfo {
  ai_generated: boolean
  ai_model_info?: {
    provider?: string
    model_id?: string
    version?: string
  }
  content_labels?: {
    generated_content_notice?: string
    media_notice?: string
    watermark_text?: string
    inappropriate?: boolean
    language?: string
    content_type?: string
    created_at?: string
  }
}

export interface AILabelsConfig {
  text_notice: string
  media_notice: string
  warning: string
  watermark_text: string
}

export interface LabelingStats {
  total_messages: number
  ai_generated_messages: number
  labeled_messages: number
  labeling_rate: number
  ai_detection_rate: number
}

interface UseAILabelingReturn {
  // State
  loading: boolean
  error: string | null
  labels: AILabelsConfig | null
  supportedLanguages: string[]
  
  // Label management
  fetchLabels: (language?: string) => Promise<AILabelsConfig | null>
  fetchAllLabels: () => Promise<Record<string, AILabelsConfig> | null>
  
  // Message labeling
  applyLabeling: (messageId: string, options?: {
    language?: string
    forceAIGenerated?: boolean
  }) => Promise<AILabelInfo | null>
  
  bulkApplyLabeling: (messageIds: string[], options?: {
    modelProvider?: string
    language?: string
    batchSize?: number
  }) => Promise<{
    total_processed: number
    total_labeled: number
    total_errors: number
  } | null>
  
  // Message label retrieval
  getMessageLabels: (messageId: string, language?: string) => Promise<AILabelInfo | null>
  
  // Content detection
  detectAIContent: (content: string, options?: {
    modelProvider?: string
    modelId?: string
  }) => Promise<boolean>
  
  // Statistics
  getLabelingStats: () => Promise<LabelingStats | null>
  
  // Utilities
  clearError: () => void
  isAIGenerated: (labelInfo?: AILabelInfo) => boolean
  formatModelInfo: (modelInfo?: AILabelInfo['ai_model_info']) => string
  getWatermarkText: (labelInfo?: AILabelInfo) => string
}

export const useAILabeling = (): UseAILabelingReturn => {
  const { i18n } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [labels, setLabels] = useState<AILabelsConfig | null>(null)
  const [supportedLanguages, setSupportedLanguages] = useState<string[]>([])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const handleError = useCallback((err: any) => {
    console.error('AI labeling error:', err)
    if (err.response?.data?.message) {
      setError(err.response.data.message)
    } else if (err.message) {
      setError(err.message)
    } else {
      setError('An unexpected error occurred')
    }
  }, [])

  const fetchLabels = useCallback(async (language?: string): Promise<AILabelsConfig | null> => {
    setLoading(true)
    setError(null)
    
    try {
      const lang = language || i18n.language
      const response = await fetch(`/api/config/ai-labels?language=${lang}`)
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch AI labels')
      }

      setLabels(data.labels)
      setSupportedLanguages(data.supported_languages || [])
      
      return data.labels
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [i18n.language, handleError])

  const fetchAllLabels = useCallback(async (): Promise<Record<string, AILabelsConfig> | null> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/config/ai-labels/all')
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to fetch all AI labels')
      }

      setSupportedLanguages(data.supported_languages || [])
      
      return data.labels
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [handleError])

  const applyLabeling = useCallback(async (
    messageId: string, 
    options: { language?: string; forceAIGenerated?: boolean } = {}
  ): Promise<AILabelInfo | null> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/config/ai-labels/apply', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message_id: messageId,
          language: options.language || i18n.language,
          force_ai_generated: options.forceAIGenerated,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to apply AI labeling')
      }

      return data.label_info
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [i18n.language, handleError])

  const bulkApplyLabeling = useCallback(async (
    messageIds: string[],
    options: { 
      modelProvider?: string
      language?: string
      batchSize?: number 
    } = {}
  ) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/config/ai-labels/bulk-apply', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message_ids: messageIds,
          model_provider: options.modelProvider,
          language: options.language || i18n.language,
          batch_size: options.batchSize || 100,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to apply bulk AI labeling')
      }

      return data.results
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [i18n.language, handleError])

  const getMessageLabels = useCallback(async (
    messageId: string, 
    language?: string
  ): Promise<AILabelInfo | null> => {
    setLoading(true)
    setError(null)
    
    try {
      const lang = language || i18n.language
      const response = await fetch(
        `/api/config/ai-labels/message/${messageId}${lang ? `?language=${lang}` : ''}`
      )

      if (response.status === 404) {
        return null // Message not found or not AI-generated
      }

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to get message labels')
      }

      return data.label_info
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [i18n.language, handleError])

  const detectAIContent = useCallback(async (
    content: string,
    options: { modelProvider?: string; modelId?: string } = {}
  ): Promise<boolean> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/config/ai-labels/detect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content,
          model_provider: options.modelProvider,
          model_id: options.modelId,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to detect AI content')
      }

      return data.is_ai_generated
    } catch (err) {
      handleError(err)
      return false
    } finally {
      setLoading(false)
    }
  }, [handleError])

  const getLabelingStats = useCallback(async (): Promise<LabelingStats | null> => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/config/ai-labels/stats')
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.message || 'Failed to get labeling stats')
      }

      return data.stats
    } catch (err) {
      handleError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [handleError])

  // Utility functions
  const isAIGenerated = useCallback((labelInfo?: AILabelInfo): boolean => {
    return labelInfo?.ai_generated === true
  }, [])

  const formatModelInfo = useCallback((modelInfo?: AILabelInfo['ai_model_info']): string => {
    if (!modelInfo) return ''
    
    const parts = []
    if (modelInfo.provider) parts.push(modelInfo.provider)
    if (modelInfo.model_id) parts.push(modelInfo.model_id)
    if (modelInfo.version) parts.push(`v${modelInfo.version}`)
    
    return parts.join(' ')
  }, [])

  const getWatermarkText = useCallback((labelInfo?: AILabelInfo): string => {
    return labelInfo?.content_labels?.watermark_text || labels?.watermark_text || 'AI Generated'
  }, [labels])

  // Load labels on mount and language change
  useEffect(() => {
    fetchLabels()
  }, [fetchLabels])

  return {
    // State
    loading,
    error,
    labels,
    supportedLanguages,
    
    // Label management
    fetchLabels,
    fetchAllLabels,
    
    // Message labeling
    applyLabeling,
    bulkApplyLabeling,
    
    // Message label retrieval
    getMessageLabels,
    
    // Content detection
    detectAIContent,
    
    // Statistics
    getLabelingStats,
    
    // Utilities
    clearError,
    isAIGenerated,
    formatModelInfo,
    getWatermarkText,
  }
}