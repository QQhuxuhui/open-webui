'use client'
import { useState, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { RiUploadLine, RiCropLine } from '@remixicon/react'
import Modal from '@/app/components/base/modal'
import Button from '@/app/components/base/button'
import { useContext } from 'use-context-selector'
import { ToastContext } from '@/app/components/base/toast'
import { updateUserProfile } from '@/service/common'

interface AvatarCropModalProps {
  show: boolean
  onClose: () => void
  onSave: (avatarUrl: string) => void
}

export default function AvatarCropModal({ show, onClose, onSave }: AvatarCropModalProps) {
  const { t } = useTranslation()
  const { notify } = useContext(ToastContext)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  
  const [selectedImage, setSelectedImage] = useState<string | null>(null)
  const [croppedImage, setCroppedImage] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [step, setStep] = useState<'select' | 'crop' | 'preview'>('select')

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      notify({ type: 'error', message: t('common.account.invalidImageFormat') })
      return
    }

    // Validate file size (5MB limit)
    if (file.size > 5 * 1024 * 1024) {
      notify({ type: 'error', message: t('common.account.imageTooLarge') })
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      setSelectedImage(e.target?.result as string)
      setStep('crop')
    }
    reader.readAsDataURL(file)
  }, [t, notify])

  const handleCrop = useCallback(() => {
    if (!selectedImage || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const img = new Image()
    img.onload = () => {
      // Set canvas size to 200x200 for avatar
      canvas.width = 200
      canvas.height = 200

      // Calculate crop dimensions to maintain aspect ratio
      const size = Math.min(img.width, img.height)
      const startX = (img.width - size) / 2
      const startY = (img.height - size) / 2

      // Draw cropped image
      ctx.drawImage(img, startX, startY, size, size, 0, 0, 200, 200)

      // Convert to blob
      canvas.toBlob((blob) => {
        if (blob) {
          const croppedUrl = URL.createObjectURL(blob)
          setCroppedImage(croppedUrl)
          setStep('preview')
        }
      }, 'image/jpeg', 0.9)
    }
    img.src = selectedImage
  }, [selectedImage])

  const handleSave = async () => {
    if (!croppedImage) return

    try {
      setUploading(true)

      // Convert blob URL to blob
      const response = await fetch(croppedImage)
      const blob = await response.blob()

      // Create form data
      const formData = new FormData()
      formData.append('avatar', blob, 'avatar.jpg')

      // Upload avatar
      await updateUserProfile({ url: 'account/avatar/upload', body: formData })
      
      onSave(croppedImage)
      onClose()
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setUploading(false)
    }
  }

  const handleReset = () => {
    setSelectedImage(null)
    setCroppedImage(null)
    setStep('select')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <Modal
      isShow={show}
      onClose={onClose}
      className='!w-[520px] !p-6'
    >
      <div className='title-2xl-semi-bold mb-6 text-text-primary'>{t('common.account.editAvatar')}</div>

      {step === 'select' && (
        <div className='text-center'>
          <div 
            className='mx-auto w-32 h-32 border-2 border-dashed border-components-button-secondary-border rounded-lg flex flex-col items-center justify-center cursor-pointer hover:bg-components-button-secondary-bg-hover transition-colors'
            onClick={() => fileInputRef.current?.click()}
          >
            <RiUploadLine className='h-8 w-8 text-text-tertiary mb-2' />
            <p className='system-sm-medium text-text-secondary mb-1'>{t('common.account.selectImage')}</p>
            <p className='system-xs-regular text-text-tertiary'>{t('common.account.imageFormat')}</p>
          </div>
          <input
            ref={fileInputRef}
            type='file'
            accept='image/*'
            onChange={handleFileSelect}
            className='hidden'
          />
        </div>
      )}

      {step === 'crop' && selectedImage && (
        <div className='text-center'>
          <div className='mb-4'>
            <img 
              src={selectedImage} 
              alt='Preview' 
              className='max-w-full max-h-64 mx-auto rounded-lg'
            />
          </div>
          <p className='system-sm-regular text-text-tertiary mb-4'>
            {t('common.account.cropInstruction')}
          </p>
          <canvas ref={canvasRef} className='hidden' />
        </div>
      )}

      {step === 'preview' && croppedImage && (
        <div className='text-center'>
          <div className='mb-4'>
            <div className='w-32 h-32 mx-auto rounded-full overflow-hidden'>
              <img 
                src={croppedImage} 
                alt='Cropped avatar' 
                className='w-full h-full object-cover'
              />
            </div>
          </div>
          <p className='system-sm-regular text-text-tertiary mb-4'>
            {t('common.account.avatarPreview')}
          </p>
        </div>
      )}

      <div className='mt-8 flex justify-between'>
        <Button onClick={step === 'select' ? onClose : handleReset}>
          {step === 'select' ? t('common.operation.cancel') : t('common.operation.reselect')}
        </Button>
        
        <div className='flex gap-2'>
          {step === 'crop' && (
            <Button variant='primary' onClick={handleCrop}>
              <RiCropLine className='mr-1 h-4 w-4' />
              {t('common.account.cropImage')}
            </Button>
          )}
          
          {step === 'preview' && (
            <Button 
              variant='primary' 
              onClick={handleSave}
              disabled={uploading}
            >
              {uploading ? t('common.operation.uploading') : t('common.operation.save')}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}