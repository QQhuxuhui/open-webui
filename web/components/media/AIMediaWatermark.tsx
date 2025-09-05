'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'

export interface AIMediaWatermarkProps {
  src: string
  alt?: string
  watermarkText?: string
  watermarkPosition?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right'
  showWatermark?: boolean
  className?: string
  style?: React.CSSProperties
  onLoad?: () => void
  onError?: () => void
}

const AIMediaWatermark: React.FC<AIMediaWatermarkProps> = ({
  src,
  alt,
  watermarkText,
  watermarkPosition = 'bottom-right',
  showWatermark = true,
  className = '',
  style,
  onLoad,
  onError
}) => {
  const { t, i18n } = useTranslation()
  const containerRef = useRef<HTMLDivElement>(null)
  const [isImageLoaded, setIsImageLoaded] = useState(false)
  const [watermarkDisplay, setWatermarkDisplay] = useState('')

  // Update watermark text based on language
  useEffect(() => {
    if (!showWatermark) {
      setWatermarkDisplay('')
      return
    }

    const currentLang = i18n.language
    const defaultTexts = {
      'en': 'AI Generated',
      'zh': 'AI生成',
      'zh-CN': 'AI生成',
      'ja': 'AI生成',
      'ko': 'AI 생성',
      'fr': 'Généré par IA',
      'de': 'KI-generiert',
      'es': 'Generado por IA',
      'pt': 'Gerado por IA',
      'ru': 'Создано ИИ'
    }

    const text = watermarkText || 
                 defaultTexts[currentLang as keyof typeof defaultTexts] || 
                 defaultTexts['en'] ||
                 t('ai.watermark.defaultText', 'AI Generated')

    setWatermarkDisplay(text)
  }, [watermarkText, showWatermark, i18n.language, t])

  const handleImageLoad = () => {
    setIsImageLoaded(true)
    onLoad?.()
  }

  const handleImageError = () => {
    setIsImageLoaded(false)
    onError?.()
  }

  const getWatermarkPositionStyles = () => {
    const baseStyles = "absolute text-white text-xs font-medium px-2 py-1 rounded-md pointer-events-none select-none"
    const backgroundStyles = "bg-black/50 backdrop-blur-sm"
    
    const positions = {
      'top-left': 'top-2 left-2',
      'top-right': 'top-2 right-2',
      'bottom-left': 'bottom-2 left-2',
      'bottom-right': 'bottom-2 right-2'
    }

    return `${baseStyles} ${backgroundStyles} ${positions[watermarkPosition]}`
  }

  // Determine if the source is an image or video
  const isImage = /\.(jpg|jpeg|png|gif|webp|bmp|svg)$/i.test(src)
  const isVideo = /\.(mp4|webm|ogg|mov|avi|mkv)$/i.test(src)

  if (isVideo) {
    return (
      <div 
        ref={containerRef}
        className={`relative inline-block ${className}`}
        style={style}
      >
        <video
          src={src}
          controls
          className="max-w-full h-auto"
          onLoadedData={handleImageLoad}
          onError={handleImageError}
          aria-label={alt}
        >
          {t('media.videoNotSupported', 'Your browser does not support the video tag.')}
        </video>
        
        {showWatermark && watermarkDisplay && isImageLoaded && (
          <div className={getWatermarkPositionStyles()}>
            <div className="flex items-center gap-1">
              <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
              {watermarkDisplay}
            </div>
          </div>
        )}
      </div>
    )
  }

  // Default to image handling
  return (
    <div 
      ref={containerRef}
      className={`relative inline-block ${className}`}
      style={style}
    >
      <img
        src={src}
        alt={alt}
        className="max-w-full h-auto"
        onLoad={handleImageLoad}
        onError={handleImageError}
      />
      
      {showWatermark && watermarkDisplay && isImageLoaded && (
        <div className={getWatermarkPositionStyles()}>
          <div className="flex items-center gap-1">
            <svg className="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
            {watermarkDisplay}
          </div>
        </div>
      )}
      
      {/* Loading placeholder */}
      {!isImageLoaded && (
        <div className="absolute inset-0 bg-gray-200 dark:bg-gray-700 animate-pulse flex items-center justify-center">
          <div className="text-gray-400 dark:text-gray-500">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        </div>
      )}
    </div>
  )
}

// Enhanced version with overlay watermark
export const AIMediaWithOverlay: React.FC<AIMediaWatermarkProps & {
  overlayOpacity?: number
  overlayColor?: string
}> = ({ 
  overlayOpacity = 0.7,
  overlayColor = 'rgba(0, 0, 0, 0.5)',
  ...props 
}) => {
  return (
    <div className="relative group">
      <AIMediaWatermark {...props} />
      
      {/* Hover overlay with AI information */}
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center"
        style={{ backgroundColor: overlayColor }}
      >
        <div className="text-white text-center">
          <div className="flex items-center justify-center mb-2">
            <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
            <span className="font-medium">AI Generated Content</span>
          </div>
          <p className="text-sm opacity-90">
            This content was created using artificial intelligence
          </p>
        </div>
      </div>
    </div>
  )
}

export default AIMediaWatermark