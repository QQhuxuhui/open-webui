import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { X, Upload, AlertCircle, CheckCircle, Clock, FileText, Shield, Camera } from 'lucide-react';
import { toast } from 'sonner';
import { verificationAPI } from '@/lib/api/verification';
import type { 
  VerificationStatus, 
  VerificationSubmissionData, 
  IDTypeOption, 
  VerificationFormData,
  VerificationStep 
} from '@/types/verification';

interface RealNameVerificationProps {
  onClose: () => void;
  onVerificationUpdate?: (status: VerificationStatus) => void;
}

export default function RealNameVerification({ onClose, onVerificationUpdate }: RealNameVerificationProps) {
  const [currentStep, setCurrentStep] = useState<VerificationStep>('form');
  const [isLoading, setIsLoading] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatus | null>(null);
  const [idTypes, setIdTypes] = useState<IDTypeOption[]>([]);
  const [frontDocumentPreview, setFrontDocumentPreview] = useState<string | null>(null);
  const [backDocumentPreview, setBackDocumentPreview] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, watch, setValue } = useForm<VerificationFormData>();

  const frontDocumentFile = watch('front_document');
  const backDocumentFile = watch('back_document');

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (frontDocumentFile && frontDocumentFile[0]) {
      const file = frontDocumentFile[0];
      const reader = new FileReader();
      reader.onload = (e) => setFrontDocumentPreview(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      setFrontDocumentPreview(null);
    }
  }, [frontDocumentFile]);

  useEffect(() => {
    if (backDocumentFile && backDocumentFile[0]) {
      const file = backDocumentFile[0];
      const reader = new FileReader();
      reader.onload = (e) => setBackDocumentPreview(e.target?.result as string);
      reader.readAsDataURL(file);
    } else {
      setBackDocumentPreview(null);
    }
  }, [backDocumentFile]);

  const loadInitialData = async () => {
    try {
      setIsLoading(true);
      const [status, types] = await Promise.all([
        verificationAPI.getVerificationStatus(),
        verificationAPI.getIDTypes()
      ]);
      
      setVerificationStatus(status);
      setIdTypes(types);

      // If user already has a verification, show status instead of form
      if (!status.can_submit) {
        setCurrentStep('review');
      }
    } catch (error: any) {
      toast.error(error.message || 'Failed to load verification data');
    } finally {
      setIsLoading(false);
    }
  };

  const onSubmit = async (data: VerificationFormData) => {
    if (currentStep !== 'submit') return;

    try {
      setIsLoading(true);

      const submissionData: VerificationSubmissionData = {
        real_name: data.real_name,
        id_type: data.id_type,
        id_number: data.id_number,
        front_document: data.front_document[0],
        back_document: data.back_document?.[0]
      };

      const result = await verificationAPI.submitVerification(submissionData);
      
      // Refresh status
      const updatedStatus = await verificationAPI.getVerificationStatus();
      setVerificationStatus(updatedStatus);
      
      if (onVerificationUpdate) {
        onVerificationUpdate(updatedStatus);
      }

      toast.success('Verification submitted successfully!');
      setCurrentStep('review');

    } catch (error: any) {
      toast.error(error.message || 'Failed to submit verification');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = () => {
    if (!verificationStatus) return <Clock size={20} className="text-gray-500" />;
    
    switch (verificationStatus.status) {
      case 'approved':
        return <CheckCircle size={20} className="text-green-600" />;
      case 'rejected':
        return <AlertCircle size={20} className="text-red-600" />;
      case 'pending':
        return <Clock size={20} className="text-yellow-600" />;
      default:
        return <FileText size={20} className="text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    if (!verificationStatus) return 'text-gray-600';
    
    switch (verificationStatus.status) {
      case 'approved':
        return 'text-green-600';
      case 'rejected':
        return 'text-red-600';
      case 'pending':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const canProceedToUpload = () => {
    const data = watch();
    return data.real_name && data.id_type && data.id_number;
  };

  const canProceedToReview = () => {
    const data = watch();
    return canProceedToUpload() && data.front_document && data.front_document[0];
  };

  if (isLoading && !verificationStatus) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3">Loading...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <Shield size={24} className="text-primary" />
            <h2 className="text-xl font-semibold">Real Name Verification</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Status Display */}
          {verificationStatus && !verificationStatus.can_submit && (
            <div className="p-6">
              <div className="bg-gray-50 rounded-lg p-6">
                <div className="flex items-center space-x-3 mb-4">
                  {getStatusIcon()}
                  <div>
                    <h3 className={`text-lg font-semibold ${getStatusColor()}`}>
                      Verification Status
                    </h3>
                    <p className="text-gray-600 text-sm mt-1">
                      {verificationStatus.message}
                    </p>
                  </div>
                </div>

                {verificationStatus.status === 'rejected' && verificationStatus.rejection_reason && (
                  <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                    <h4 className="font-medium text-red-800 mb-2">Rejection Reason:</h4>
                    <p className="text-red-700 text-sm">{verificationStatus.rejection_reason}</p>
                  </div>
                )}

                {verificationStatus.submitted_at && (
                  <div className="mt-4 text-sm text-gray-600">
                    <p>Submitted: {new Date(verificationStatus.submitted_at).toLocaleDateString()}</p>
                    {verificationStatus.verified_at && (
                      <p>Verified: {new Date(verificationStatus.verified_at).toLocaleDateString()}</p>
                    )}
                  </div>
                )}
              </div>

              {verificationStatus.can_submit && (
                <div className="mt-6">
                  <button
                    onClick={() => {
                      setCurrentStep('form');
                      setVerificationStatus(null);
                    }}
                    className="w-full py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
                  >
                    Submit New Verification
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Verification Form */}
          {(verificationStatus?.can_submit !== false) && (
            <form onSubmit={handleSubmit(onSubmit)} className="p-6">
              {/* Step 1: Basic Information */}
              {currentStep === 'form' && (
                <div className="space-y-6">
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="flex items-start space-x-3">
                      <AlertCircle size={20} className="text-blue-600 mt-0.5" />
                      <div className="text-sm text-blue-800">
                        <p className="font-medium mb-2">Important Information:</p>
                        <ul className="space-y-1">
                          <li>• Please ensure all information matches your official ID document exactly</li>
                          <li>• Verification typically takes 1-3 business days</li>
                          <li>• Your personal information is encrypted and securely stored</li>
                        </ul>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Real Name *
                    </label>
                    <input
                      {...register('real_name', {
                        required: 'Real name is required',
                        minLength: {
                          value: 2,
                          message: 'Name must be at least 2 characters'
                        },
                        maxLength: {
                          value: 50,
                          message: 'Name must be less than 50 characters'
                        }
                      })}
                      type="text"
                      placeholder="Enter your full legal name"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                    {errors.real_name && (
                      <p className="text-sm text-red-600 mt-1">{errors.real_name.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      ID Type *
                    </label>
                    <select
                      {...register('id_type', { required: 'ID type is required' })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    >
                      <option value="">Select ID type</option>
                      {idTypes.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                    {errors.id_type && (
                      <p className="text-sm text-red-600 mt-1">{errors.id_type.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      ID Number *
                    </label>
                    <input
                      {...register('id_number', {
                        required: 'ID number is required',
                        minLength: {
                          value: 8,
                          message: 'ID number must be at least 8 characters'
                        },
                        maxLength: {
                          value: 20,
                          message: 'ID number must be less than 20 characters'
                        }
                      })}
                      type="text"
                      placeholder="Enter your ID number"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    />
                    {errors.id_number && (
                      <p className="text-sm text-red-600 mt-1">{errors.id_number.message}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Step 2: Document Upload */}
              {currentStep === 'upload' && (
                <div className="space-y-6">
                  <div className="text-center mb-6">
                    <Camera size={48} className="text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold">Upload ID Documents</h3>
                    <p className="text-gray-600 text-sm mt-2">
                      Please upload clear photos of your ID document
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Front Side of ID Document *
                    </label>
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-primary transition-colors">
                      <input
                        {...register('front_document', { required: 'Front document is required' })}
                        type="file"
                        accept="image/*,.pdf"
                        className="hidden"
                        id="front-document"
                      />
                      <label 
                        htmlFor="front-document" 
                        className="cursor-pointer flex flex-col items-center"
                      >
                        {frontDocumentPreview ? (
                          <img 
                            src={frontDocumentPreview} 
                            alt="Front document preview" 
                            className="max-w-full max-h-48 object-contain mb-4 rounded-lg"
                          />
                        ) : (
                          <>
                            <Upload size={32} className="text-gray-400 mb-2" />
                            <p className="text-gray-600 text-center">
                              Click to upload front side of ID
                            </p>
                          </>
                        )}
                      </label>
                    </div>
                    {errors.front_document && (
                      <p className="text-sm text-red-600 mt-1">{errors.front_document.message}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Back Side of ID Document (Optional)
                    </label>
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-primary transition-colors">
                      <input
                        {...register('back_document')}
                        type="file"
                        accept="image/*,.pdf"
                        className="hidden"
                        id="back-document"
                      />
                      <label 
                        htmlFor="back-document" 
                        className="cursor-pointer flex flex-col items-center"
                      >
                        {backDocumentPreview ? (
                          <img 
                            src={backDocumentPreview} 
                            alt="Back document preview" 
                            className="max-w-full max-h-48 object-contain mb-4 rounded-lg"
                          />
                        ) : (
                          <>
                            <Upload size={32} className="text-gray-400 mb-2" />
                            <p className="text-gray-600 text-center">
                              Click to upload back side of ID (if applicable)
                            </p>
                          </>
                        )}
                      </label>
                    </div>
                  </div>

                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="text-sm text-yellow-800">
                      <p className="font-medium mb-2">Photo Requirements:</p>
                      <ul className="space-y-1">
                        <li>• Clear, high-resolution images</li>
                        <li>• All text must be clearly readable</li>
                        <li>• No glare or shadows covering important information</li>
                        <li>• Maximum file size: 10MB</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: Review */}
              {currentStep === 'review' && (
                <div className="space-y-6">
                  <div className="text-center mb-6">
                    <FileText size={48} className="text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold">Review Your Information</h3>
                    <p className="text-gray-600 text-sm mt-2">
                      Please review all information before submitting
                    </p>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-6 space-y-4">
                    <div>
                      <label className="text-sm font-medium text-gray-600">Real Name</label>
                      <p className="text-lg">{watch('real_name')}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-600">ID Type</label>
                      <p className="text-lg">
                        {idTypes.find(t => t.value === watch('id_type'))?.label || watch('id_type')}
                      </p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-600">ID Number</label>
                      <p className="text-lg">{watch('id_number')}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-600">Documents</label>
                      <div className="flex space-x-4 mt-2">
                        {frontDocumentPreview && (
                          <img 
                            src={frontDocumentPreview} 
                            alt="Front document" 
                            className="w-24 h-16 object-cover rounded border"
                          />
                        )}
                        {backDocumentPreview && (
                          <img 
                            src={backDocumentPreview} 
                            alt="Back document" 
                            className="w-24 h-16 object-cover rounded border"
                          />
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div className="text-sm text-blue-800">
                      <p className="font-medium mb-2">Before submitting:</p>
                      <ul className="space-y-1">
                        <li>• Double-check that all information is accurate</li>
                        <li>• Verification process typically takes 1-3 business days</li>
                        <li>• You will be notified via email when review is complete</li>
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex justify-between items-center pt-6 mt-6 border-t">
                <div>
                  {currentStep !== 'form' && currentStep !== 'review' && (
                    <button
                      type="button"
                      onClick={() => {
                        if (currentStep === 'upload') setCurrentStep('form');
                        if (currentStep === 'submit') setCurrentStep('review');
                      }}
                      className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                    >
                      Back
                    </button>
                  )}
                </div>

                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                  
                  {currentStep === 'form' && (
                    <button
                      type="button"
                      onClick={() => canProceedToUpload() && setCurrentStep('upload')}
                      disabled={!canProceedToUpload()}
                      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Continue
                    </button>
                  )}

                  {currentStep === 'upload' && (
                    <button
                      type="button"
                      onClick={() => canProceedToReview() && setCurrentStep('review')}
                      disabled={!canProceedToReview()}
                      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      Review
                    </button>
                  )}

                  {currentStep === 'review' && (
                    <button
                      type="button"
                      onClick={() => setCurrentStep('submit')}
                      className="px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
                    >
                      Submit
                    </button>
                  )}

                  {currentStep === 'submit' && (
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {isLoading ? 'Submitting...' : 'Submit Verification'}
                    </button>
                  )}
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}