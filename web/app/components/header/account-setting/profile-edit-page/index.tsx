'use client'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RiEditLine, RiEyeLine, RiEyeOffLine, RiPhoneLine, RiShieldLine, RiHistoryLine, RiUpload2Line, RiCropLine } from '@remixicon/react'
import Modal from '@/app/components/base/modal'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { useAppContext } from '@/context/app-context'
import { useContext } from 'use-context-selector'
import { ToastContext } from '@/app/components/base/toast'
import AvatarCropModal from './avatar-crop-modal'
import PhoneChangeModal from './phone-change-modal'
import ProfileHistoryModal from './profile-history-modal'
import { updateUserProfile } from '@/service/common'

const titleClassName = `
  system-sm-semibold text-text-secondary
`
const descriptionClassName = `
  mt-1 body-xs-regular text-text-tertiary
`

export default function ProfileEditPage() {
  const { t } = useTranslation()
  const { mutateUserProfile, userProfile } = useAppContext()
  const { notify } = useContext(ToastContext)
  
  // Form state
  const [editNicknameModalVisible, setEditNicknameModalVisible] = useState(false)
  const [nickname, setNickname] = useState('')
  const [editing, setEditing] = useState(false)
  
  // Modal states
  const [showAvatarCrop, setShowAvatarCrop] = useState(false)
  const [showPhoneChange, setShowPhoneChange] = useState(false)
  const [showProfileHistory, setShowProfileHistory] = useState(false)
  
  const handleEditNickname = () => {
    setEditNicknameModalVisible(true)
    setNickname(userProfile.nickname || userProfile.name || '')
  }

  const handleSaveNickname = async () => {
    if (!nickname.trim()) {
      notify({ type: 'error', message: t('common.account.nicknameEmpty') })
      return
    }
    
    try {
      setEditing(true)
      await updateUserProfile({ url: 'account/nickname', body: { nickname } })
      notify({ type: 'success', message: t('common.actionMsg.modifiedSuccessfully') })
      mutateUserProfile()
      setEditNicknameModalVisible(false)
    }
    catch (e) {
      notify({ type: 'error', message: (e as Error).message })
    }
    finally {
      setEditing(false)
    }
  }

  const handleAvatarChange = (newAvatarUrl: string) => {
    mutateUserProfile()
    notify({ type: 'success', message: t('common.actionMsg.modifiedSuccessfully') })
  }

  const handlePhoneChange = () => {
    mutateUserProfile()
    notify({ type: 'success', message: t('common.actionMsg.modifiedSuccessfully') })
  }

  return (
    <>
      <div className='pb-3 pt-2'>
        <h4 className='title-2xl-semi-bold text-text-primary'>{t('common.account.profileEdit')}</h4>
        <p className='system-sm-regular mt-1 text-text-tertiary'>{t('common.account.profileEditDescription')}</p>
      </div>

      {/* Avatar Section */}
      <div className='mb-8'>
        <div className={titleClassName}>{t('common.account.avatar')}</div>
        <div className={descriptionClassName}>{t('common.account.avatarTip')}</div>
        <div className='mt-3 flex items-center gap-4'>
          <div className='h-16 w-16 rounded-full bg-components-avatar-bg overflow-hidden'>
            {userProfile.avatar_url ? (
              <img src={userProfile.avatar_url} alt={userProfile.name} className='h-full w-full object-cover' />
            ) : (
              <div className='flex h-full w-full items-center justify-center text-components-avatar-text text-xl font-semibold'>
                {(userProfile.nickname || userProfile.name)?.charAt(0)?.toUpperCase()}
              </div>
            )}
          </div>
          <div className='flex gap-2'>
            <Button
              variant='secondary'
              size='small'
              onClick={() => setShowAvatarCrop(true)}
            >
              <RiUpload2Line className='mr-1 h-4 w-4' />
              {t('common.account.uploadAvatar')}
            </Button>
            {userProfile.avatar_url && (
              <Button
                variant='tertiary'
                size='small'
                onClick={() => setShowAvatarCrop(true)}
              >
                <RiCropLine className='mr-1 h-4 w-4' />
                {t('common.account.editAvatar')}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Nickname Section */}
      <div className='mb-8'>
        <div className={titleClassName}>{t('common.account.nickname')}</div>
        <div className={descriptionClassName}>{t('common.account.nicknameTip')}</div>
        <div className='mt-2 flex w-full items-center justify-between gap-2'>
          <div className='system-sm-regular flex-1 rounded-lg bg-components-input-bg-normal p-2 text-components-input-text-filled'>
            <span className='pl-1'>{userProfile.nickname || userProfile.name}</span>
          </div>
          <Button
            variant='tertiary'
            size='small'
            onClick={handleEditNickname}
          >
            <RiEditLine className='mr-1 h-4 w-4' />
            {t('common.operation.edit')}
          </Button>
        </div>
      </div>

      {/* Phone Number Section */}
      <div className='mb-8'>
        <div className={titleClassName}>{t('common.account.phoneNumber')}</div>
        <div className={descriptionClassName}>{t('common.account.phoneNumberTip')}</div>
        <div className='mt-2 flex w-full items-center justify-between gap-2'>
          <div className='system-sm-regular flex-1 rounded-lg bg-components-input-bg-normal p-2 text-components-input-text-filled'>
            <span className='pl-1'>
              {userProfile.phone_number ? 
                `${userProfile.phone_number.slice(0, 3)}****${userProfile.phone_number.slice(-4)}` : 
                t('common.account.phoneNumberNotSet')
              }
            </span>
            {userProfile.phone_verified && (
              <span className='ml-2 text-components-badge-text-success text-xs'>
                <RiShieldLine className='inline h-3 w-3 mr-1' />
                {t('common.account.verified')}
              </span>
            )}
          </div>
          <Button
            variant='tertiary'
            size='small'
            onClick={() => setShowPhoneChange(true)}
          >
            <RiPhoneLine className='mr-1 h-4 w-4' />
            {userProfile.phone_number ? t('common.account.changePhone') : t('common.account.bindPhone')}
          </Button>
        </div>
      </div>

      {/* Real Name Section */}
      <div className='mb-8'>
        <div className={titleClassName}>{t('common.account.realName')}</div>
        <div className={descriptionClassName}>{t('common.account.realNameTip')}</div>
        <div className='mt-2 flex w-full items-center justify-between gap-2'>
          <div className='system-sm-regular flex-1 rounded-lg bg-components-input-bg-normal p-2 text-components-input-text-filled'>
            <span className='pl-1'>
              {userProfile.real_name ? 
                `${userProfile.real_name.charAt(0)}**${userProfile.real_name.slice(-1)}` : 
                t('common.account.realNameNotSet')
              }
            </span>
            {userProfile.real_name_verified && (
              <span className='ml-2 text-components-badge-text-success text-xs'>
                <RiShieldLine className='inline h-3 w-3 mr-1' />
                {t('common.account.verified')}
              </span>
            )}
          </div>
          {!userProfile.real_name_verified && (
            <Button
              variant='tertiary'
              size='small'
              disabled
            >
              <RiShieldLine className='mr-1 h-4 w-4' />
              {userProfile.real_name ? t('common.account.verifyRealName') : t('common.account.setRealName')}
            </Button>
          )}
        </div>
      </div>

      <div className='mb-6 border-[1px] border-divider-subtle' />

      {/* Security & History Section */}
      <div className='mb-8'>
        <div className={titleClassName}>{t('common.account.securityAudit')}</div>
        <div className={descriptionClassName}>{t('common.account.securityAuditTip')}</div>
        <div className='mt-3'>
          <Button
            variant='tertiary'
            size='small'
            onClick={() => setShowProfileHistory(true)}
          >
            <RiHistoryLine className='mr-1 h-4 w-4' />
            {t('common.account.viewProfileHistory')}
          </Button>
        </div>
      </div>

      {/* Nickname Edit Modal */}
      {editNicknameModalVisible && (
        <Modal
          isShow
          onClose={() => setEditNicknameModalVisible(false)}
          className='!w-[420px] !p-6'
        >
          <div className='title-2xl-semi-bold mb-6 text-text-primary'>{t('common.account.editNickname')}</div>
          <div className={titleClassName}>{t('common.account.nickname')}</div>
          <Input 
            className='mt-2'
            value={nickname}
            onChange={e => setNickname(e.target.value)}
            placeholder={t('common.account.nicknamePlaceholder')}
          />
          <div className='mt-10 flex justify-end'>
            <Button 
              className='mr-2' 
              onClick={() => setEditNicknameModalVisible(false)}
            >
              {t('common.operation.cancel')}
            </Button>
            <Button
              disabled={editing || !nickname.trim()}
              variant='primary'
              onClick={handleSaveNickname}
            >
              {t('common.operation.save')}
            </Button>
          </div>
        </Modal>
      )}

      {/* Avatar Crop Modal */}
      {showAvatarCrop && (
        <AvatarCropModal
          show={showAvatarCrop}
          onClose={() => setShowAvatarCrop(false)}
          onSave={handleAvatarChange}
        />
      )}

      {/* Phone Change Modal */}
      {showPhoneChange && (
        <PhoneChangeModal
          show={showPhoneChange}
          onClose={() => setShowPhoneChange(false)}
          onSave={handlePhoneChange}
          currentPhone={userProfile.phone_number}
        />
      )}

      {/* Profile History Modal */}
      {showProfileHistory && (
        <ProfileHistoryModal
          show={showProfileHistory}
          onClose={() => setShowProfileHistory(false)}
        />
      )}
    </>
  )
}