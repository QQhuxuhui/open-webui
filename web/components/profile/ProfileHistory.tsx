import React, { useState, useEffect } from 'react';
import { X, User, Phone, Mail, Image, Calendar, MapPin, Shield } from 'lucide-react';
import { toast } from 'sonner';
import { profileAPI } from '@/lib/api/profile';
import type { ProfileChangeLog } from '@/types/profile';

interface ProfileHistoryProps {
  onClose: () => void;
}

const getChangeIcon = (changeType: string) => {
  switch (changeType) {
    case 'nickname':
    case 'real_name':
      return <User size={16} className="text-blue-600" />;
    case 'phone_number':
      return <Phone size={16} className="text-green-600" />;
    case 'email':
      return <Mail size={16} className="text-purple-600" />;
    case 'avatar':
      return <Image size={16} className="text-orange-600" />;
    case 'verification':
      return <Shield size={16} className="text-red-600" />;
    default:
      return <Calendar size={16} className="text-gray-600" />;
  }
};

const getChangeLabel = (changeType: string) => {
  const labels: Record<string, string> = {
    'nickname': 'Nickname',
    'real_name': 'Real Name',
    'phone_number': 'Phone Number',
    'email': 'Email',
    'avatar': 'Avatar',
    'verification': 'Verification Status',
    'password': 'Password',
    'profile_settings': 'Profile Settings'
  };
  return labels[changeType] || changeType;
};

const formatChangeValue = (changeType: string, value: any) => {
  if (!value) return 'Not set';
  
  switch (changeType) {
    case 'phone_number':
      return value.replace(/(\d{3})(\d{4})(\d{4})/, '$1****$3');
    case 'email':
      const [local, domain] = value.split('@');
      return `${local.slice(0, 2)}****@${domain}`;
    case 'avatar':
      return 'Profile picture updated';
    case 'verification':
      return value ? 'Verified' : 'Not verified';
    default:
      return value;
  }
};

export default function ProfileHistory({ onClose }: ProfileHistoryProps) {
  const [changes, setChanges] = useState<ProfileChangeLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadChangeHistory();
  }, []);

  const loadChangeHistory = async () => {
    try {
      setIsLoading(true);
      const data = await profileAPI.getChangeHistory();
      setChanges(data);
    } catch (error: any) {
      toast.error(error.message || 'Failed to load change history');
    } finally {
      setIsLoading(false);
    }
  };

  const filteredChanges = changes.filter(change => 
    filter === 'all' || change.change_type === filter
  );

  const uniqueChangeTypes = [...new Set(changes.map(change => change.change_type))];

  const groupChangesByDate = (changes: ProfileChangeLog[]) => {
    const groups: Record<string, ProfileChangeLog[]> = {};
    
    changes.forEach(change => {
      const date = new Date(change.created_at).toDateString();
      if (!groups[date]) {
        groups[date] = [];
      }
      groups[date].push(change);
    });
    
    return groups;
  };

  const changeGroups = groupChangesByDate(filteredChanges);

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <div className="bg-white rounded-lg p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3">Loading history...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Profile Change History</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1 rounded-full text-sm transition-colors ${
                filter === 'all' 
                  ? 'bg-primary text-white' 
                  : 'bg-white text-gray-600 hover:bg-gray-100'
              }`}
            >
              All Changes ({changes.length})
            </button>
            {uniqueChangeTypes.map(type => {
              const count = changes.filter(c => c.change_type === type).length;
              return (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    filter === type 
                      ? 'bg-primary text-white' 
                      : 'bg-white text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {getChangeLabel(type)} ({count})
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {Object.keys(changeGroups).length === 0 ? (
            <div className="text-center py-12">
              <Calendar size={48} className="text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No profile changes found</p>
              <p className="text-sm text-gray-400 mt-2">
                Your profile changes will appear here for security audit purposes
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {Object.entries(changeGroups)
                .sort(([a], [b]) => new Date(b).getTime() - new Date(a).getTime())
                .map(([date, dateChanges]) => (
                <div key={date} className="space-y-4">
                  <div className="flex items-center space-x-2">
                    <Calendar size={16} className="text-gray-400" />
                    <h3 className="text-lg font-semibold text-gray-800">
                      {new Date(date).toLocaleDateString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </h3>
                  </div>
                  
                  <div className="space-y-3 pl-6 border-l-2 border-gray-200">
                    {dateChanges
                      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                      .map((change) => (
                      <div key={change.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-start space-x-3">
                          <div className="flex-shrink-0 mt-0.5">
                            {getChangeIcon(change.change_type)}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium text-gray-900">
                                {getChangeLabel(change.change_type)} Changed
                              </h4>
                              <span className="text-xs text-gray-500">
                                {new Date(change.created_at).toLocaleTimeString()}
                              </span>
                            </div>
                            
                            {change.old_value && (
                              <div className="text-sm text-gray-600 mb-1">
                                <span className="text-gray-500">From:</span>{' '}
                                <span className="line-through">
                                  {formatChangeValue(change.change_type, change.old_value)}
                                </span>
                              </div>
                            )}
                            
                            <div className="text-sm text-gray-900">
                              <span className="text-gray-500">To:</span>{' '}
                              <span className="font-medium">
                                {formatChangeValue(change.change_type, change.new_value)}
                              </span>
                            </div>
                            
                            <div className="flex items-center justify-between mt-2">
                              <div className="flex items-center space-x-2 text-xs text-gray-500">
                                <MapPin size={12} />
                                <span>IP: {change.ip_address}</span>
                              </div>
                              
                              {change.user_agent && (
                                <div className="text-xs text-gray-400 truncate max-w-xs">
                                  {change.user_agent.split(' ')[0]}
                                </div>
                              )}
                            </div>
                            
                            {change.reason && (
                              <div className="mt-2 text-sm text-blue-600 bg-blue-50 rounded p-2">
                                <strong>Reason:</strong> {change.reason}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <div className="text-sm text-gray-600 text-center">
            <Shield size={16} className="inline mr-2" />
            Change history is kept for security and audit purposes
          </div>
        </div>
      </div>
    </div>
  );
}