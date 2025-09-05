/**
 * Chat Export Utilities with AI Labeling Integration
 * Demonstrates how AI content labels are preserved during chat export
 */

export interface ChatMessage {
  id: string
  query: string
  answer: string
  created_at: string
  conversation_id?: string
  ai_generated?: boolean
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

export interface ChatExportData {
  conversation_id: string
  messages: ChatMessage[]
  export_date: string
  total_messages: number
  ai_generated_count: number
  human_generated_count: number
  ai_labeling_stats?: {
    total_labeled: number
    labeling_rate: number
    languages_detected: string[]
  }
}

/**
 * Export chat conversation with AI labeling information preserved
 */
export async function exportChatWithAILabels(
  conversationId: string,
  format: 'json' | 'markdown' | 'html' = 'json'
): Promise<ChatExportData | string> {
  try {
    // Fetch conversation messages (this would be replaced with actual API call)
    const messages = await fetchConversationMessages(conversationId)
    
    // Enrich messages with AI labeling information
    const enrichedMessages = await enrichMessagesWithAILabels(messages)
    
    // Generate export statistics
    const stats = generateExportStatistics(enrichedMessages)
    
    const exportData: ChatExportData = {
      conversation_id: conversationId,
      messages: enrichedMessages,
      export_date: new Date().toISOString(),
      total_messages: enrichedMessages.length,
      ai_generated_count: stats.ai_generated_count,
      human_generated_count: stats.human_generated_count,
      ai_labeling_stats: stats.labeling_stats
    }
    
    // Format export based on requested format
    switch (format) {
      case 'json':
        return exportData
      case 'markdown':
        return formatAsMarkdown(exportData)
      case 'html':
        return formatAsHTML(exportData)
      default:
        return exportData
    }
  } catch (error) {
    console.error('Failed to export chat with AI labels:', error)
    throw error
  }
}

/**
 * Fetch conversation messages (placeholder - would integrate with actual API)
 */
async function fetchConversationMessages(conversationId: string): Promise<ChatMessage[]> {
  // This would be replaced with actual API call
  const response = await fetch(`/api/conversations/${conversationId}/messages`)
  if (!response.ok) {
    throw new Error('Failed to fetch conversation messages')
  }
  return response.json()
}

/**
 * Enrich messages with AI labeling information
 */
async function enrichMessagesWithAILabels(messages: ChatMessage[]): Promise<ChatMessage[]> {
  const enrichedMessages: ChatMessage[] = []
  
  for (const message of messages) {
    let enrichedMessage = { ...message }
    
    // Fetch AI labels if message is AI-generated
    if (message.ai_generated) {
      try {
        const response = await fetch(`/api/config/ai-labels/message/${message.id}`)
        if (response.ok) {
          const labelData = await response.json()
          if (labelData.success && labelData.label_info) {
            enrichedMessage = {
              ...enrichedMessage,
              ai_model_info: labelData.label_info.ai_model_info,
              content_labels: labelData.label_info.content_labels
            }
          }
        }
      } catch (error) {
        console.warn(`Failed to fetch AI labels for message ${message.id}:`, error)
        // Continue without labels if fetch fails
      }
    }
    
    enrichedMessages.push(enrichedMessage)
  }
  
  return enrichedMessages
}

/**
 * Generate export statistics including AI labeling information
 */
function generateExportStatistics(messages: ChatMessage[]) {
  const aiMessages = messages.filter(msg => msg.ai_generated)
  const humanMessages = messages.filter(msg => !msg.ai_generated)
  
  const labeledMessages = messages.filter(msg => msg.content_labels)
  const languagesDetected = new Set<string>()
  
  messages.forEach(msg => {
    if (msg.content_labels?.language) {
      languagesDetected.add(msg.content_labels.language)
    }
  })
  
  return {
    ai_generated_count: aiMessages.length,
    human_generated_count: humanMessages.length,
    labeling_stats: {
      total_labeled: labeledMessages.length,
      labeling_rate: messages.length > 0 ? (labeledMessages.length / messages.length) * 100 : 0,
      languages_detected: Array.from(languagesDetected)
    }
  }
}

/**
 * Format export data as Markdown
 */
function formatAsMarkdown(exportData: ChatExportData): string {
  let markdown = `# Chat Export: ${exportData.conversation_id}\n\n`
  markdown += `**Export Date:** ${exportData.export_date}\n`
  markdown += `**Total Messages:** ${exportData.total_messages}\n`
  markdown += `**AI Generated:** ${exportData.ai_generated_count}\n`
  markdown += `**Human Generated:** ${exportData.human_generated_count}\n`
  
  if (exportData.ai_labeling_stats) {
    markdown += `**AI Labeling Rate:** ${exportData.ai_labeling_stats.labeling_rate.toFixed(1)}%\n`
    markdown += `**Languages Detected:** ${exportData.ai_labeling_stats.languages_detected.join(', ')}\n`
  }
  
  markdown += '\n---\n\n'
  
  exportData.messages.forEach((message, index) => {
    markdown += `## Message ${index + 1}\n\n`
    markdown += `**Query:** ${message.query}\n\n`
    markdown += `**Answer:** ${message.answer}\n\n`
    
    if (message.ai_generated && message.ai_model_info) {
      markdown += `**AI Model:** ${message.ai_model_info.provider} ${message.ai_model_info.model_id}\n`
      if (message.ai_model_info.version) {
        markdown += `**Model Version:** ${message.ai_model_info.version}\n`
      }
    }
    
    if (message.content_labels) {
      markdown += `**AI Content Notice:** ${message.content_labels.generated_content_notice}\n`
      markdown += `**Language:** ${message.content_labels.language}\n`
    }
    
    markdown += `**Created:** ${message.created_at}\n\n`
    markdown += '---\n\n'
  })
  
  return markdown
}

/**
 * Format export data as HTML
 */
function formatAsHTML(exportData: ChatExportData): string {
  let html = `
<!DOCTYPE html>
<html>
<head>
    <title>Chat Export: ${exportData.conversation_id}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .message { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }
        .ai-message { background-color: #f0f8ff; border-left: 4px solid #4285f4; }
        .human-message { background-color: #f9f9f9; border-left: 4px solid #34a853; }
        .ai-label { background: #fff3cd; padding: 8px; border-radius: 4px; margin-top: 10px; font-size: 0.9em; }
        .meta-info { color: #666; font-size: 0.9em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Chat Export: ${exportData.conversation_id}</h1>
        <p><strong>Export Date:</strong> ${exportData.export_date}</p>
        <p><strong>Total Messages:</strong> ${exportData.total_messages}</p>
        <p><strong>AI Generated:</strong> ${exportData.ai_generated_count}</p>
        <p><strong>Human Generated:</strong> ${exportData.human_generated_count}</p>`
  
  if (exportData.ai_labeling_stats) {
    html += `
        <p><strong>AI Labeling Rate:</strong> ${exportData.ai_labeling_stats.labeling_rate.toFixed(1)}%</p>
        <p><strong>Languages Detected:</strong> ${exportData.ai_labeling_stats.languages_detected.join(', ')}</p>`
  }
  
  html += `
    </div>`
  
  exportData.messages.forEach((message, index) => {
    const messageClass = message.ai_generated ? 'ai-message' : 'human-message'
    const messageType = message.ai_generated ? 'AI Generated' : 'Human'
    
    html += `
    <div class="message ${messageClass}">
        <h3>Message ${index + 1} (${messageType})</h3>
        <p><strong>Query:</strong> ${escapeHtml(message.query)}</p>
        <p><strong>Answer:</strong> ${escapeHtml(message.answer)}</p>`
    
    if (message.ai_generated && message.ai_model_info) {
      html += `
        <p><strong>AI Model:</strong> ${escapeHtml(message.ai_model_info.provider || '')} ${escapeHtml(message.ai_model_info.model_id || '')}</p>`
      
      if (message.ai_model_info.version) {
        html += `<p><strong>Model Version:</strong> ${escapeHtml(message.ai_model_info.version)}</p>`
      }
    }
    
    if (message.content_labels) {
      html += `
        <div class="ai-label">
            <p><strong>⚠️ AI Content Notice:</strong> ${escapeHtml(message.content_labels.generated_content_notice || '')}</p>
            <p><strong>Language:</strong> ${escapeHtml(message.content_labels.language || '')}</p>
        </div>`
    }
    
    html += `
        <div class="meta-info">
            <p><strong>Created:</strong> ${message.created_at}</p>
        </div>
    </div>`
  })
  
  html += `
</body>
</html>`
  
  return html
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Export multiple conversations as a batch with AI labeling
 */
export async function exportMultipleChatsWithAILabels(
  conversationIds: string[],
  format: 'json' | 'markdown' | 'html' = 'json'
): Promise<ChatExportData[] | string> {
  try {
    const exports = await Promise.all(
      conversationIds.map(id => exportChatWithAILabels(id, 'json'))
    )
    
    if (format === 'json') {
      return exports as ChatExportData[]
    }
    
    // Combine exports for markdown/html format
    const combinedExport = {
      conversations: exports as ChatExportData[],
      export_date: new Date().toISOString(),
      total_conversations: conversationIds.length,
      total_messages: (exports as ChatExportData[]).reduce((sum, exp) => sum + exp.total_messages, 0),
      total_ai_messages: (exports as ChatExportData[]).reduce((sum, exp) => sum + exp.ai_generated_count, 0),
      total_human_messages: (exports as ChatExportData[]).reduce((sum, exp) => sum + exp.human_generated_count, 0)
    }
    
    if (format === 'markdown') {
      return formatBatchAsMarkdown(combinedExport)
    } else if (format === 'html') {
      return formatBatchAsHTML(combinedExport)
    }
    
    return exports as ChatExportData[]
  } catch (error) {
    console.error('Failed to export multiple chats:', error)
    throw error
  }
}

/**
 * Format batch export as Markdown
 */
function formatBatchAsMarkdown(batchExport: any): string {
  let markdown = `# Batch Chat Export\n\n`
  markdown += `**Export Date:** ${batchExport.export_date}\n`
  markdown += `**Total Conversations:** ${batchExport.total_conversations}\n`
  markdown += `**Total Messages:** ${batchExport.total_messages}\n`
  markdown += `**Total AI Messages:** ${batchExport.total_ai_messages}\n`
  markdown += `**Total Human Messages:** ${batchExport.total_human_messages}\n\n`
  
  batchExport.conversations.forEach((conv: ChatExportData, index: number) => {
    markdown += formatAsMarkdown(conv)
    if (index < batchExport.conversations.length - 1) {
      markdown += '\n\n==============================\n\n'
    }
  })
  
  return markdown
}

/**
 * Format batch export as HTML
 */
function formatBatchAsHTML(batchExport: any): string {
  let html = `
<!DOCTYPE html>
<html>
<head>
    <title>Batch Chat Export</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .batch-header { background: #e8f4fd; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
        .conversation-separator { border-top: 3px solid #ddd; margin: 30px 0; padding-top: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .message { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 8px; }
        .ai-message { background-color: #f0f8ff; border-left: 4px solid #4285f4; }
        .human-message { background-color: #f9f9f9; border-left: 4px solid #34a853; }
        .ai-label { background: #fff3cd; padding: 8px; border-radius: 4px; margin-top: 10px; font-size: 0.9em; }
        .meta-info { color: #666; font-size: 0.9em; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="batch-header">
        <h1>Batch Chat Export</h1>
        <p><strong>Export Date:</strong> ${batchExport.export_date}</p>
        <p><strong>Total Conversations:</strong> ${batchExport.total_conversations}</p>
        <p><strong>Total Messages:</strong> ${batchExport.total_messages}</p>
        <p><strong>Total AI Messages:</strong> ${batchExport.total_ai_messages}</p>
        <p><strong>Total Human Messages:</strong> ${batchExport.total_human_messages}</p>
    </div>`
  
  batchExport.conversations.forEach((conv: ChatExportData, index: number) => {
    if (index > 0) {
      html += '<div class="conversation-separator"></div>'
    }
    html += formatAsHTML(conv)
  })
  
  html += '</body></html>'
  return html
}

/**
 * Download chat export as file
 */
export function downloadChatExport(
  data: ChatExportData | ChatExportData[] | string,
  filename: string,
  format: 'json' | 'markdown' | 'html'
) {
  let content: string
  let mimeType: string
  
  switch (format) {
    case 'json':
      content = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
      mimeType = 'application/json'
      break
    case 'markdown':
      content = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
      mimeType = 'text/markdown'
      break
    case 'html':
      content = typeof data === 'string' ? data : JSON.stringify(data, null, 2)
      mimeType = 'text/html'
      break
    default:
      throw new Error(`Unsupported format: ${format}`)
  }
  
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}.${format}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}