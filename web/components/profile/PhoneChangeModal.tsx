import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { X, Phone, Shield, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { profileAPI } from '@/lib/api/profile';
import { smsAPI } from '@/lib/api/sms';

interface PhoneChangeModalProps {
  currentPhone?: string | null;
  onChanged: (newPhone: string) => void;
  onClose: () => void;
}

interface PhoneChangeForm {
  newPhone: string;
  oldPhoneCode?: string;
  newPhoneCode: string;
}

enum Step {
  VERIFY_CURRENT = 'verify_current',
  SET_NEW = 'set_new',
  VERIFY_NEW = 'verify_new',
  CONFIRM = 'confirm'
}

export default function PhoneChangeModal({ currentPhone, onChanged, onClose }: PhoneChangeModalProps) {
  const [step, setStep] = useState<Step>(currentPhone ? Step.VERIFY_CURRENT : Step.SET_NEW);
  const [isLoading, setIsLoading] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [oldCodeSent, setOldCodeSent] = useState(false);
  const [newCodeSent, setNewCodeSent] = useState(false);
  const [countdown, setCountdown] = useState(0);

  const { register, handleSubmit, formState: { errors }, watch } = useForm<PhoneChangeForm>();

  // Countdown timer for SMS resend
  React.useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const startCountdown = () => {
    setCountdown(60);
  };

  const sendOldPhoneVerification = async () => {
    if (!currentPhone) return;
    
    try {
      setIsLoading(true);
      await smsAPI.sendVerification(currentPhone, 'phone_change');
      setOldCodeSent(true);
      startCountdown();
      toast.success('Verification code sent to your current phone');
    } catch (error: any) {
      toast.error(error.message || 'Failed to send verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const sendNewPhoneVerification = async (phone: string) => {
    try {
      setIsLoading(true);
      await smsAPI.sendVerification(phone, 'phone_change');
      setNewCodeSent(true);
      startCountdown();
      toast.success('Verification code sent to your new phone');
    } catch (error: any) {
      toast.error(error.message || 'Failed to send verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const verifyCurrentPhone = async (code: string) => {
    if (!currentPhone) return;
    
    try {
      setIsLoading(true);
      await smsAPI.verifyCode(currentPhone, code, 'phone_change');
      setStep(Step.SET_NEW);
      toast.success('Current phone verified successfully');
    } catch (error: any) {
      toast.error(error.message || 'Invalid verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const verifyNewPhone = async (phone: string, code: string) => {
    try {
      setIsLoading(true);
      await smsAPI.verifyCode(phone, code, 'phone_change');
      setStep(Step.CONFIRM);
      toast.success('New phone verified successfully');
    } catch (error: any) {
      toast.error(error.message || 'Invalid verification code');
    } finally {
      setIsLoading(false);
    }
  };

  const confirmPhoneChange = async () => {
    try {
      setIsLoading(true);
      const response = await profileAPI.changePhoneNumber(newPhone);
      onChanged(newPhone);
      onClose();
      toast.success('Phone number updated successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to update phone number');
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (data: PhoneChangeForm) => {
    switch (step) {
      case Step.VERIFY_CURRENT:
        if (data.oldPhoneCode) {
          await verifyCurrentPhone(data.oldPhoneCode);
        }
        break;
      case Step.SET_NEW:
        setNewPhone(data.newPhone);
        await sendNewPhoneVerification(data.newPhone);
        setStep(Step.VERIFY_NEW);
        break;
      case Step.VERIFY_NEW:
        await verifyNewPhone(newPhone, data.newPhoneCode);
        break;
      case Step.CONFIRM:
        await confirmPhoneChange();
        break;
    }
  };

  const formatPhoneNumber = (phone: string) => {
    return phone.replace(/(\d{3})(\d{4})(\d{4})/, '$1-****-$3');
  };

  const getStepTitle = () => {
    switch (step) {
      case Step.VERIFY_CURRENT:
        return 'Verify Current Phone';
      case Step.SET_NEW:
        return 'Set New Phone Number';
      case Step.VERIFY_NEW:
        return 'Verify New Phone';
      case Step.CONFIRM:
        return 'Confirm Changes';
      default:
        return 'Change Phone Number';
    }
  };

  const getStepDescription = () => {
    switch (step) {
      case Step.VERIFY_CURRENT:
        return `We'll send a verification code to ${formatPhoneNumber(currentPhone!)} to verify your identity.`;
      case Step.SET_NEW:
        return 'Enter your new phone number. We\'ll send a verification code to confirm it.';
      case Step.VERIFY_NEW:
        return `Please enter the verification code sent to ${formatPhoneNumber(newPhone)}.`;
      case Step.CONFIRM:
        return 'Please review the changes before confirming.';
      default:
        return '';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">{getStepTitle()}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6">
          {/* Step Description */}
          <div className="text-sm text-gray-600">
            {getStepDescription()}
          </div>

          {/* Step Content */}
          {step === Step.VERIFY_CURRENT && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <Phone size={16} className="text-blue-600" />
                  <span className="text-blue-800">Current: {formatPhoneNumber(currentPhone!)}</span>
                </div>
              </div>

              {!oldCodeSent ? (
                <button
                  type="button"
                  onClick={sendOldPhoneVerification}
                  disabled={isLoading}
                  className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 transition-colors"
                >
                  {isLoading ? 'Sending...' : 'Send Verification Code'}
                </button>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Verification Code
                    </label>
                    <input
                      {...register('oldPhoneCode', {
                        required: 'Verification code is required',
                        pattern: {
                          value: /^\d{6}$/,
                          message: 'Code must be 6 digits'
                        }
                      })}
                      type="text"
                      placeholder="Enter 6-digit code"
                      maxLength={6}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-center text-lg tracking-wider"
                    />
                    {errors.oldPhoneCode && (
                      <p className="text-sm text-red-600 mt-1">{errors.oldPhoneCode.message}</p>
                    )}
                  </div>

                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={sendOldPhoneVerification}
                      disabled={countdown > 0 || isLoading}
                      className="text-sm text-primary hover:underline disabled:text-gray-400"
                    >
                      {countdown > 0 ? `Resend in ${countdown}s` : 'Resend Code'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {step === Step.SET_NEW && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  New Phone Number
                </label>
                <input
                  {...register('newPhone', {
                    required: 'Phone number is required',
                    pattern: {
                      value: /^1[3-9]\d{9}$/,
                      message: 'Please enter a valid Chinese phone number'
                    }
                  })}
                  type="tel"
                  placeholder="13800138000"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                />
                {errors.newPhone && (
                  <p className="text-sm text-red-600 mt-1">{errors.newPhone.message}</p>
                )}
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start space-x-2">
                  <AlertTriangle size={16} className="text-yellow-600 mt-0.5" />
                  <div className="text-sm text-yellow-800">
                    <strong>Important:</strong> Make sure you have access to this phone number. 
                    You'll need to verify it before the change takes effect.
                  </div>
                </div>
              </div>
            </div>
          )}

          {step === Step.VERIFY_NEW && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <Phone size={16} className="text-blue-600" />
                  <span className="text-blue-800">New: {formatPhoneNumber(newPhone)}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Verification Code
                </label>
                <input
                  {...register('newPhoneCode', {
                    required: 'Verification code is required',
                    pattern: {
                      value: /^\d{6}$/,
                      message: 'Code must be 6 digits'
                    }
                  })}
                  type="text"
                  placeholder="Enter 6-digit code"
                  maxLength={6}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-center text-lg tracking-wider"
                />
                {errors.newPhoneCode && (
                  <p className="text-sm text-red-600 mt-1">{errors.newPhoneCode.message}</p>
                )}
              </div>

              <div className="flex justify-between items-center">
                <button
                  type="button"
                  onClick={() => sendNewPhoneVerification(newPhone)}
                  disabled={countdown > 0 || isLoading}
                  className="text-sm text-primary hover:underline disabled:text-gray-400"
                >
                  {countdown > 0 ? `Resend in ${countdown}s` : 'Resend Code'}
                </button>
              </div>
            </div>
          )}

          {step === Step.CONFIRM && (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <Shield size={16} className="text-green-600" />
                  <span className="text-green-800 font-medium">Verification Complete</span>
                </div>
                <div className="text-sm text-green-700">
                  Both phone numbers have been verified successfully.
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Current Phone:</span>
                  <span className="font-medium">{formatPhoneNumber(currentPhone || '')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">New Phone:</span>
                  <span className="font-medium text-primary">{formatPhoneNumber(newPhone)}</span>
                </div>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="text-sm text-yellow-800">
                  <strong>Note:</strong> This change will affect your login method and account security. 
                  Please keep your new phone number secure.
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            
            {((step === Step.VERIFY_CURRENT && oldCodeSent) || 
              step === Step.SET_NEW || 
              step === Step.VERIFY_NEW || 
              step === Step.CONFIRM) && (
              <button
                type="submit"
                disabled={isLoading}
                className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Processing...' : 
                 step === Step.SET_NEW ? 'Continue' :
                 step === Step.CONFIRM ? 'Confirm Change' : 'Verify'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}