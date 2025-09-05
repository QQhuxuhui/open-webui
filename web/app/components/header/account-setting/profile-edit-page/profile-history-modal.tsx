'use client'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { RiHistoryLine, RiUserLine, RiPhoneLine, RiImageLine, RiTimeLine } from '@remixicon/react'
import Modal from '@/app/components/base/modal'
import Button from '@/app/components/base/button'
import { useContext } from 'use-context-selector'
import { ToastContext } from '@/app/components/base/toast'
import { formatDistanceToNow } from 'date-fns'
import { zhCN, enUS } from 'date-fns/locale'
import { getProfileHistory } from '@/service/common'

interface ProfileHistoryModalProps {
  show: boolean
  onClose: () => void
}

interface ProfileHistoryItem {
  id: string
  field_name: string
  field_label: string
  old_value: string | null
  new_value: string
  ip_address: string
  user_agent: string
  created_at: string
  verification_required: boolean
}

export default function ProfileHistoryModal({ show, onClose }: ProfileHistoryModalProps) {
  const { t, i18n } = useTranslation()
  const { notify } = useContext(ToastContext)
  
  const [historyItems, setHistoryItems] = useState<ProfileHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  useEffect(() => {
    if (show) {
      loadHistory(1)
    }
  }, [show])

  const loadHistory = async (pageNum: number) => {
    try {
      setLoading(true)
      const response = await getProfileHistory({ page: pageNum, limit: 20 })
      
      if (pageNum === 1) {
        setHistoryItems(response.data)
      } else {
        setHistoryItems(prev => [...prev, ...response.data])
      }
      
      setHasMore(response.has_next)
      setPage(pageNum)
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  const getFieldIcon = (fieldName: string) => {
    switch (fieldName) {
      case 'nickname':
      case 'name':
        return <RiUserLine className='h-4 w-4' />
      case 'phone_number':
        return <RiPhoneLine className='h-4 w-4' />
      case 'avatar_url':
        return <RiImageLine className='h-4 w-4' />
      default:
        return <RiHistoryLine className='h-4 w-4' />
    }
  }

  const getFieldLabel = (fieldName: string, fieldLabel?: string) => {
    if (fieldLabel) return fieldLabel
    
    switch (fieldName) {
      case 'nickname':
        return t('common.account.nickname')
      case 'name':
        return t('common.account.name')
      case 'phone_number':
        return t('common.account.phoneNumber')
      case 'avatar_url':
        return t('common.account.avatar')
      default:
        return fieldName
    }
  }

  const formatValue = (fieldName: string, value: string | null) => {
    if (!value) return t('common.account.notSet')
    
    switch (fieldName) {
      case 'phone_number':
        return `${value.slice(0, 3)}****${value.slice(-4)}`
      case 'avatar_url':
        return t('common.account.avatarUpdated')
      default:
        return value
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const locale = i18n.language === 'zh-Hans' ? zhCN : enUS
    return formatDistanceToNow(date, { addSuffix: true, locale })
  }

  const getLocationInfo = (ipAddress: string, userAgent: string) => {
    // Extract browser info from user agent
    let browser = 'Unknown'
    if (userAgent.includes('Chrome')) browser = 'Chrome'
    else if (userAgent.includes('Firefox')) browser = 'Firefox'
    else if (userAgent.includes('Safari')) browser = 'Safari'
    else if (userAgent.includes('Edge')) browser = 'Edge'
    
    return `${browser} • ${ipAddress}`
  }

  return (
    <Modal
      isShow={show}
      onClose={onClose}
      className='!w-[640px] !max-h-[80vh] !p-6'
    >
      <div className='title-2xl-semi-bold mb-6 text-text-primary'>
        {t('common.account.profileHistory')}
      </div>
      
      <div className='mb-4'>
        <p className='system-sm-regular text-text-tertiary'>
          {t('common.account.profileHistoryDesc')}
        </p>
      </div>

      <div className='max-h-[400px] overflow-y-auto'>
        {loading && historyItems.length === 0 ? (
          <div className='flex items-center justify-center py-8'>
            <div className='text-text-tertiary'>{t('common.operation.loading')}</div>
          </div>
        ) : historyItems.length === 0 ? (
          <div className='flex flex-col items-center justify-center py-8'>
            <RiHistoryLine className='h-12 w-12 text-text-quaternary mb-3' />
            <p className='system-sm-medium text-text-tertiary'>{t('common.account.noProfileHistory')}</p>
          </div>
        ) : (
          <div className='space-y-4'>
            {historyItems.map((item) => (
              <div
                key={item.id}
                className='border border-divider-subtle rounded-lg p-4'
              >
                <div className='flex items-start justify-between mb-3'>
                  <div className='flex items-center gap-2'>
                    <div className='p-2 rounded-lg bg-components-badge-bg-primary'>
                      {getFieldIcon(item.field_name)}
                    </div>
                    <div>
                      <h4 className='system-sm-semibold text-text-primary'>
                        {getFieldLabel(item.field_name, item.field_label)}
                      </h4>
                      <div className='flex items-center gap-1 text-text-tertiary system-xs-regular mt-1'>
                        <RiTimeLine className='h-3 w-3' />
                        {formatDate(item.created_at)}
                      </div>
                    </div>
                  </div>
                  
                  {item.verification_required && (
                    <span className='px-2 py-1 rounded-full bg-components-badge-bg-warning text-components-badge-text-warning system-2xs-medium'>
                      {t('common.account.verificationRequired')}
                    </span>
                  )}
                </div>

                <div className='space-y-2'>
                  {item.old_value && (
                    <div>
                      <span className='system-xs-medium text-text-tertiary mr-2'>
                        {t('common.account.oldValue')}:
                      </span>
                      <span className='system-xs-regular text-text-secondary'>
                        {formatValue(item.field_name, item.old_value)}
                      </span>
                    </div>
                  )}
                  
                  <div>
                    <span className='system-xs-medium text-text-tertiary mr-2'>
                      {t('common.account.newValue')}:
                    </span>
                    <span className='system-xs-regular text-text-primary font-medium'>
                      {formatValue(item.field_name, item.new_value)}
                    </span>
                  </div>

                  <div>
                    <span className='system-xs-medium text-text-tertiary mr-2'>
                      {t('common.account.location')}:
                    </span>
                    <span className='system-xs-regular text-text-tertiary'>
                      {getLocationInfo(item.ip_address, item.user_agent)}
                    </span>
                  </div>
                </div>
              </div>
            ))}

            {hasMore && (
              <div className='text-center pt-4'>
                <Button
                  variant='tertiary'
                  onClick={() => loadHistory(page + 1)}
                  disabled={loading}
                >
                  {loading ? t('common.operation.loading') : t('common.operation.loadMore')}
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className='mt-6 flex justify-end'>
        <Button onClick={onClose}>{t('common.operation.close')}</Button>
      </div>
    </Modal>
  )
}