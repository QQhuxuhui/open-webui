import React from 'react';
import { CheckCircle, AlertCircle, Clock, FileText, Shield, AlertTriangle } from 'lucide-react';
import type { VerificationStatus } from '@/types/verification';

interface VerificationStatusCardProps {
  status: VerificationStatus;
  onSubmitNew?: () => void;
  onViewDetails?: () => void;
  compact?: boolean;
}

export default function VerificationStatusCard({ 
  status, 
  onSubmitNew, 
  onViewDetails, 
  compact = false 
}: VerificationStatusCardProps) {
  
  const getStatusConfig = () => {
    switch (status.status) {
      case 'approved':
        return {
          icon: <CheckCircle size={compact ? 16 : 20} className="text-green-600" />,
          title: 'Verified',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          textColor: 'text-green-800'
        };
      case 'pending':
        return {
          icon: <Clock size={compact ? 16 : 20} className="text-yellow-600" />,
          title: 'Under Review',
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          textColor: 'text-yellow-800'
        };
      case 'rejected':
        return {
          icon: <AlertCircle size={compact ? 16 : 20} className="text-red-600" />,
          title: 'Verification Failed',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          textColor: 'text-red-800'
        };
      case 'expired':
        return {
          icon: <AlertTriangle size={compact ? 16 : 20} className="text-orange-600" />,
          title: 'Expired',
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          textColor: 'text-orange-800'
        };
      default:
        return {
          icon: <FileText size={compact ? 16 : 20} className="text-gray-600" />,
          title: 'Not Verified',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          textColor: 'text-gray-800'
        };
    }
  };

  const config = getStatusConfig();

  if (compact) {
    return (
      <div className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg border ${config.bgColor} ${config.borderColor}`}>
        {config.icon}
        <span className={`text-sm font-medium ${config.textColor}`}>
          {config.title}
        </span>
        {status.status === 'rejected' && onSubmitNew && (
          <button
            onClick={onSubmitNew}
            className="text-xs text-primary hover:underline ml-2"
          >
            Resubmit
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={`border rounded-lg p-6 ${config.bgColor} ${config.borderColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            {config.icon}
          </div>
          <div>
            <h3 className={`text-lg font-semibold ${config.textColor}`}>
              Real Name Verification
            </h3>
            <p className={`text-sm ${config.textColor} font-medium mt-1`}>
              {config.title}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Shield size={24} className="text-gray-400" />
        </div>
      </div>

      <div className="mt-4">
        <p className={`text-sm ${config.textColor.replace('800', '700')}`}>
          {status.message}
        </p>
      </div>

      {/* Status-specific content */}
      {status.status === 'approved' && status.verified_at && (
        <div className="mt-4 pt-4 border-t border-green-200">
          <p className="text-sm text-green-600">
            <span className="font-medium">Verified on:</span>{' '}
            {new Date(status.verified_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </p>
        </div>
      )}

      {status.status === 'pending' && status.submitted_at && (
        <div className="mt-4 pt-4 border-t border-yellow-200">
          <p className="text-sm text-yellow-600">
            <span className="font-medium">Submitted on:</span>{' '}
            {new Date(status.submitted_at).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'long',
              day: 'numeric'
            })}
          </p>
          <p className="text-xs text-yellow-600 mt-1">
            Review typically takes 1-3 business days
          </p>
        </div>
      )}

      {status.status === 'rejected' && status.rejection_reason && (
        <div className="mt-4 pt-4 border-t border-red-200">
          <p className="text-sm font-medium text-red-700 mb-2">
            Reason for rejection:
          </p>
          <p className="text-sm text-red-600 bg-red-100 rounded-lg p-3 border border-red-200">
            {status.rejection_reason}
          </p>
        </div>
      )}

      {/* Action buttons */}
      <div className="mt-6 flex flex-wrap gap-3">
        {status.can_submit && onSubmitNew && (
          <button
            onClick={onSubmitNew}
            className="flex items-center space-x-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors"
          >
            <FileText size={16} />
            <span>
              {status.status === 'not_submitted' ? 'Start Verification' : 'Submit New Request'}
            </span>
          </button>
        )}

        {status.verification_id && onViewDetails && (
          <button
            onClick={onViewDetails}
            className="flex items-center space-x-2 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <FileText size={16} />
            <span>View Details</span>
          </button>
        )}
      </div>

      {/* Help text */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-start space-x-2">
          <Shield size={14} className="text-gray-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-600">
            <p className="font-medium mb-1">Why verify your identity?</p>
            <ul className="space-y-0.5">
              <li>• Enhanced security for your account</li>
              <li>• Access to premium features</li>
              <li>• Increased trust and credibility</li>
              <li>• Compliance with platform policies</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Privacy notice */}
      <div className="mt-4 text-xs text-gray-500 bg-white rounded-lg p-3 border border-gray-200">
        <p>
          <span className="font-medium">Privacy Notice:</span> Your personal information is encrypted and securely stored. 
          We only use this information for identity verification purposes and will never share it with third parties.
        </p>
      </div>
    </div>
  );
}