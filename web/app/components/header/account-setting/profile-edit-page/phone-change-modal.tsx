'use client'
import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { RiPhoneLine, RiShieldLine, RiTimeLine } from '@remixicon/react'
import Modal from '@/app/components/base/modal'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { useContext } from 'use-context-selector'
import { ToastContext } from '@/app/components/base/toast'
import { sendSMSCode, verifySMSCode, changePhoneNumber } from '@/service/common'

interface PhoneChangeModalProps {
  show: boolean
  onClose: () => void
  onSave: () => void
  currentPhone: string | null
}

type Step = 'verify_old' | 'set_new' | 'verify_new' | 'complete'

export default function PhoneChangeModal({ show, onClose, onSave, currentPhone }: PhoneChangeModalProps) {
  const { t } = useTranslation()
  const { notify } = useContext(ToastContext)
  
  const [step, setStep] = useState<Step>(currentPhone ? 'verify_old' : 'set_new')
  const [oldPhoneCode, setOldPhoneCode] = useState('')
  const [newPhone, setNewPhone] = useState('')
  const [newPhoneCode, setNewPhoneCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [countdown, setCountdown] = useState(0)

  // Countdown timer
  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    }
  }, [countdown])

  const validatePhoneNumber = (phone: string) => {
    const phoneRegex = /^1[3-9]\d{9}$/
    return phoneRegex.test(phone)
  }

  const handleSendOldPhoneCode = async () => {
    if (!currentPhone) return

    try {
      setLoading(true)
      await sendSMSCode({ 
        phone_number: currentPhone, 
        purpose: 'phone_change_old' 
      })
      
      setCountdown(60)
      notify({ type: 'success', message: t('auth.sms.codeSent') })
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyOldPhone = async () => {
    if (!currentPhone || !oldPhoneCode) return

    try {
      setLoading(true)
      await verifySMSCode({
        phone_number: currentPhone,
        verification_code: oldPhoneCode,
        purpose: 'phone_change_old'
      })
      
      setStep('set_new')
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  const handleSendNewPhoneCode = async () => {
    if (!validatePhoneNumber(newPhone)) {
      notify({ type: 'error', message: t('auth.phone.invalidFormat') })
      return
    }

    try {
      setLoading(true)
      await sendSMSCode({ 
        phone_number: newPhone, 
        purpose: 'phone_change_new' 
      })
      
      setCountdown(60)
      setStep('verify_new')
      notify({ type: 'success', message: t('auth.sms.codeSent') })
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  const handleVerifyNewPhone = async () => {
    if (!newPhone || !newPhoneCode) return

    try {
      setLoading(true)
      await verifySMSCode({
        phone_number: newPhone,
        verification_code: newPhoneCode,
        purpose: 'phone_change_new'
      })
      
      await changePhoneNumber({
        old_phone: currentPhone,
        new_phone: newPhone,
        old_phone_code: oldPhoneCode,
        new_phone_code: newPhoneCode
      })
      
      setStep('complete')
    } catch (error) {
      notify({ type: 'error', message: (error as Error).message })
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = () => {
    onSave()
    onClose()
  }

  const getStepContent = () => {
    switch (step) {
      case 'verify_old':
        return (
          <div>
            <div className='mb-6 text-center'>
              <RiShieldLine className='h-12 w-12 mx-auto text-components-badge-text-warning mb-3' />
              <h3 className='title-lg-semi-bold text-text-primary mb-2'>
                {t('common.account.verifyCurrentPhone')}
              </h3>
              <p className='system-sm-regular text-text-tertiary'>
                {t('common.account.verifyCurrentPhoneDesc', { phone: currentPhone })}
              </p>
            </div>

            <div className='space-y-4'>
              <div>
                <label className='system-sm-semibold text-text-secondary block mb-2'>
                  {t('auth.sms.verificationCode')}
                </label>
                <div className='flex gap-2'>
                  <Input
                    value={oldPhoneCode}
                    onChange={(e) => setOldPhoneCode(e.target.value)}
                    placeholder={t('auth.sms.codeInputPlaceholder')}
                    maxLength={6}
                  />
                  <Button
                    variant='secondary'
                    onClick={handleSendOldPhoneCode}
                    disabled={countdown > 0 || loading}
                    className='whitespace-nowrap'
                  >
                    {countdown > 0 ? (
                      <>
                        <RiTimeLine className='mr-1 h-4 w-4' />
                        {countdown}s
                      </>
                    ) : t('auth.sms.sendCode')}
                  </Button>
                </div>
              </div>
            </div>

            <div className='mt-8 flex justify-end gap-2'>
              <Button onClick={onClose}>{t('common.operation.cancel')}</Button>
              <Button
                variant='primary'
                onClick={handleVerifyOldPhone}
                disabled={loading || !oldPhoneCode}
              >
                {t('common.operation.verify')}
              </Button>
            </div>
          </div>
        )

      case 'set_new':
        return (
          <div>
            <div className='mb-6 text-center'>
              <RiPhoneLine className='h-12 w-12 mx-auto text-components-badge-text-info mb-3' />
              <h3 className='title-lg-semi-bold text-text-primary mb-2'>
                {currentPhone ? t('common.account.setNewPhone') : t('common.account.bindPhone')}
              </h3>
              <p className='system-sm-regular text-text-tertiary'>
                {t('common.account.setNewPhoneDesc')}
              </p>
            </div>

            <div className='space-y-4'>
              <div>
                <label className='system-sm-semibold text-text-secondary block mb-2'>
                  {t('common.account.newPhoneNumber')}
                </label>
                <Input
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  placeholder={t('auth.phone.phonePlaceholder')}
                  maxLength={11}
                />
              </div>
            </div>

            <div className='mt-8 flex justify-end gap-2'>
              <Button onClick={onClose}>{t('common.operation.cancel')}</Button>
              <Button
                variant='primary'
                onClick={handleSendNewPhoneCode}
                disabled={loading || !validatePhoneNumber(newPhone)}
              >
                {t('auth.sms.sendCode')}
              </Button>
            </div>
          </div>
        )

      case 'verify_new':
        return (
          <div>
            <div className='mb-6 text-center'>
              <RiShieldLine className='h-12 w-12 mx-auto text-components-badge-text-success mb-3' />
              <h3 className='title-lg-semi-bold text-text-primary mb-2'>
                {t('common.account.verifyNewPhone')}
              </h3>
              <p className='system-sm-regular text-text-tertiary'>
                {t('common.account.verifyNewPhoneDesc', { phone: newPhone })}
              </p>
            </div>

            <div className='space-y-4'>
              <div>
                <label className='system-sm-semibold text-text-secondary block mb-2'>
                  {t('auth.sms.verificationCode')}
                </label>
                <div className='flex gap-2'>
                  <Input
                    value={newPhoneCode}
                    onChange={(e) => setNewPhoneCode(e.target.value)}
                    placeholder={t('auth.sms.codeInputPlaceholder')}
                    maxLength={6}
                  />
                  <Button
                    variant='secondary'
                    onClick={handleSendNewPhoneCode}
                    disabled={countdown > 0 || loading}
                    className='whitespace-nowrap'
                  >
                    {countdown > 0 ? (
                      <>
                        <RiTimeLine className='mr-1 h-4 w-4' />
                        {countdown}s
                      </>
                    ) : t('auth.sms.resendCode')}
                  </Button>
                </div>
              </div>
            </div>

            <div className='mt-8 flex justify-end gap-2'>
              <Button onClick={onClose}>{t('common.operation.cancel')}</Button>
              <Button
                variant='primary'
                onClick={handleVerifyNewPhone}
                disabled={loading || !newPhoneCode}
              >
                {currentPhone ? t('common.account.changePhone') : t('common.account.bindPhone')}
              </Button>
            </div>
          </div>
        )

      case 'complete':
        return (
          <div>
            <div className='mb-6 text-center'>
              <div className='w-16 h-16 mx-auto rounded-full bg-components-badge-bg-success flex items-center justify-center mb-4'>
                <RiShieldLine className='h-8 w-8 text-components-badge-text-success' />
              </div>
              <h3 className='title-lg-semi-bold text-text-primary mb-2'>
                {currentPhone ? t('common.account.phoneChangeSuccess') : t('common.account.phoneBindSuccess')}
              </h3>
              <p className='system-sm-regular text-text-tertiary'>
                {t('common.account.phoneChangeSuccessDesc', { phone: newPhone })}
              </p>
            </div>

            <div className='mt-8 flex justify-end'>
              <Button variant='primary' onClick={handleComplete}>
                {t('common.operation.complete')}
              </Button>
            </div>
          </div>
        )
    }
  }

  return (
    <Modal
      isShow={show}
      onClose={onClose}
      className='!w-[480px] !p-6'
    >
      <div className='title-2xl-semi-bold mb-6 text-text-primary'>
        {currentPhone ? t('common.account.changePhone') : t('common.account.bindPhone')}
      </div>
      
      {getStepContent()}
    </Modal>
  )
}