/**
 * AI Content Detection Utilities
 */

export interface MessageData {
  id?: string
  content?: string
  answer?: string
  model_provider?: string
  model_id?: string
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

export interface AIDetectionResult {
  isAIGenerated: boolean
  confidence: number
  factors: {
    hasModelProvider: boolean
    hasAIKeywords: boolean
    hasAIPatterns: boolean
    contentLength: number
  }
}

/**
 * Known AI providers and models
 */
export const AI_PROVIDERS = new Set([
  'openai', 'anthropic', 'google', 'cohere', 'mistral',
  'claude', 'gpt', 'palm', 'bard', 'llama', 'vicuna',
  'huggingface', 'together', 'replicate', 'stability',
  'midjourney', 'dalle', 'stable-diffusion'
])

export const AI_MODEL_KEYWORDS = new Set([
  'gpt', 'claude', 'palm', 'bard', 'llama', 'vicuna',
  'alpaca', 'chatglm', 'baichuan', 'qwen', 'chatgpt',
  'dall-e', 'dalle', 'midjourney', 'stable-diffusion',
  'whisper', 'codex', 'davinci', 'curie', 'babbage'
])

/**
 * AI-generated text patterns
 */
export const AI_TEXT_PATTERNS = {
  en: [
    /as an ai/i,
    /i am an ai/i,
    /as a language model/i,
    /i do not have personal/i,
    /i cannot provide personal/i,
    /as artificial intelligence/i,
    /i'm an ai assistant/i,
    /as an ai assistant/i,
    /i don't have the ability to/i,
    /i cannot browse the internet/i,
    /as a machine learning model/i,
    /i was created by/i,
    /my training data/i
  ],
  zh: [
    /作为ai/i,
    /作为人工智能/i,
    /我是一个ai/i,
    /我是人工智能/i,
    /作为语言模型/i,
    /我无法提供个人/i,
    /我不能提供个人/i,
    /我是由.*训练的/i,
    /作为.*助手/i,
    /我不具备.*能力/i
  ],
  ja: [
    /私はai/i,
    /人工知能として/i,
    /言語モデルとして/i,
    /私にはできません/i,
    /私は.*によって作られました/i
  ]
}

/**
 * Detect if message content appears to be AI-generated
 */
export function detectAIContent(message: MessageData): AIDetectionResult {
  const content = message.answer || message.content || ''
  const modelProvider = message.model_provider || message.ai_model_info?.provider
  const modelId = message.model_id || message.ai_model_info?.model_id
  
  let confidence = 0
  const factors = {
    hasModelProvider: false,
    hasAIKeywords: false,
    hasAIPatterns: false,
    contentLength: content.length
  }

  // Check if explicitly marked as AI-generated
  if (message.ai_generated === true) {
    return {
      isAIGenerated: true,
      confidence: 1.0,
      factors: { ...factors, hasModelProvider: true }
    }
  }

  // Check for AI model provider
  if (modelProvider) {
    const provider = modelProvider.toLowerCase()
    factors.hasModelProvider = true
    
    if (AI_PROVIDERS.has(provider) || 
        Array.from(AI_PROVIDERS).some(p => provider.includes(p))) {
      confidence += 0.4
    }
  }

  // Check for AI model keywords in model ID
  if (modelId) {
    const model = modelId.toLowerCase()
    factors.hasAIKeywords = true
    
    if (AI_MODEL_KEYWORDS.has(model) || 
        Array.from(AI_MODEL_KEYWORDS).some(k => model.includes(k))) {
      confidence += 0.3
    }
  }

  // Check for AI-generated text patterns
  if (content) {
    const contentLower = content.toLowerCase()
    
    // Check English patterns
    for (const pattern of AI_TEXT_PATTERNS.en) {
      if (pattern.test(contentLower)) {
        factors.hasAIPatterns = true
        confidence += 0.2
        break
      }
    }
    
    // Check Chinese patterns
    if (!factors.hasAIPatterns) {
      for (const pattern of AI_TEXT_PATTERNS.zh) {
        if (pattern.test(content)) {
          factors.hasAIPatterns = true
          confidence += 0.2
          break
        }
      }
    }
    
    // Check Japanese patterns
    if (!factors.hasAIPatterns) {
      for (const pattern of AI_TEXT_PATTERNS.ja) {
        if (pattern.test(content)) {
          factors.hasAIPatterns = true
          confidence += 0.2
          break
        }
      }
    }
  }

  // Additional heuristics
  if (content && content.length > 0) {
    // Very long responses might indicate AI generation
    if (content.length > 2000) {
      confidence += 0.1
    }
    
    // Check for formal, structured responses
    const sentences = content.split(/[.!?]+/).filter(s => s.trim().length > 0)
    if (sentences.length > 3) {
      const avgSentenceLength = content.length / sentences.length
      if (avgSentenceLength > 50) {
        confidence += 0.05
      }
    }
  }

  // Normalize confidence to 0-1 range
  confidence = Math.min(confidence, 1.0)
  
  return {
    isAIGenerated: confidence > 0.3, // Threshold for AI detection
    confidence,
    factors
  }
}

/**
 * Extract AI model information from message
 */
export function extractAIModelInfo(message: MessageData) {
  const modelInfo = message.ai_model_info || {}
  
  return {
    provider: modelInfo.provider || message.model_provider || null,
    model_id: modelInfo.model_id || message.model_id || null,
    version: modelInfo.version || null
  }
}

/**
 * Check if content type requires watermarking
 */
export function shouldWatermarkContent(contentType: string, fileExtension?: string): boolean {
  const watermarkTypes = ['image', 'video']
  
  if (watermarkTypes.includes(contentType.toLowerCase())) {
    return true
  }
  
  if (fileExtension) {
    const imageExtensions = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'])
    const videoExtensions = new Set(['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv'])
    
    const ext = fileExtension.toLowerCase().replace('.', '')
    return imageExtensions.has(ext) || videoExtensions.has(ext)
  }
  
  return false
}

/**
 * Generate AI content labels based on detection results
 */
export function generateContentLabels(
  detection: AIDetectionResult,
  language: string = 'en',
  contentType: string = 'text'
): any {
  if (!detection.isAIGenerated) {
    return null
  }

  const labels: Record<string, any> = {
    en: {
      text_notice: 'Content generated by AI, for reference only',
      media_notice: 'Content generated by AI',
      watermark_text: 'AI Generated',
      warning: 'AI-generated content may contain errors'
    },
    zh: {
      text_notice: '内容由AI生成，仅供参考',
      media_notice: '内容由AI生成',
      watermark_text: 'AI生成',
      warning: 'AI生成内容可能包含错误'
    },
    'zh-CN': {
      text_notice: '内容由AI生成，仅供参考',
      media_notice: '内容由AI生成',
      watermark_text: 'AI生成',
      warning: 'AI生成内容可能包含错误'
    }
  }

  const baseLanguage = language.split('-')[0]
  const selectedLabels = labels[language] || labels[baseLanguage] || labels.en

  return {
    generated_content_notice: contentType === 'text' ? selectedLabels.text_notice : selectedLabels.media_notice,
    media_notice: selectedLabels.media_notice,
    watermark_text: selectedLabels.watermark_text,
    inappropriate: false,
    language,
    content_type: contentType,
    created_at: new Date().toISOString(),
    detection_confidence: detection.confidence,
    detection_factors: detection.factors
  }
}

/**
 * Validate AI labeling data
 */
export function validateAILabelData(labelData: any): boolean {
  if (!labelData || typeof labelData !== 'object') {
    return false
  }

  // Check required fields
  const requiredFields = ['generated_content_notice', 'language', 'content_type']
  for (const field of requiredFields) {
    if (!(field in labelData)) {
      return false
    }
  }

  // Validate language format
  if (typeof labelData.language !== 'string' || labelData.language.length < 2) {
    return false
  }

  // Validate content type
  const validContentTypes = ['text', 'image', 'video', 'audio']
  if (!validContentTypes.includes(labelData.content_type)) {
    return false
  }

  return true
}

/**
 * Batch process messages for AI detection
 */
export function batchDetectAIContent(messages: MessageData[]): Map<string, AIDetectionResult> {
  const results = new Map<string, AIDetectionResult>()
  
  for (const message of messages) {
    if (message.id) {
      const detection = detectAIContent(message)
      results.set(message.id, detection)
    }
  }
  
  return results
}

/**
 * Get AI content statistics for a set of messages
 */
export function getAIContentStats(messages: MessageData[]) {
  const total = messages.length
  let aiGenerated = 0
  let highConfidence = 0
  let hasModelInfo = 0
  
  for (const message of messages) {
    const detection = detectAIContent(message)
    
    if (detection.isAIGenerated) {
      aiGenerated++
    }
    
    if (detection.confidence > 0.7) {
      highConfidence++
    }
    
    if (detection.factors.hasModelProvider) {
      hasModelInfo++
    }
  }
  
  return {
    total,
    aiGenerated,
    humanGenerated: total - aiGenerated,
    highConfidence,
    hasModelInfo,
    aiPercentage: total > 0 ? (aiGenerated / total * 100).toFixed(1) : '0'
  }
}