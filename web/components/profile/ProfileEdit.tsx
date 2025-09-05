import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { Camera, Upload, Phone, User, Mail, Save, History } from 'lucide-react';
import AvatarCropper from './AvatarCropper';
import PhoneChangeModal from './PhoneChangeModal';
import ProfileHistory from './ProfileHistory';
import { profileAPI } from '@/lib/api/profile';
import type { ProfileData, ProfileUpdateRequest } from '@/types/profile';

interface ProfileEditProps {
  initialData?: ProfileData;
  onUpdate?: (data: ProfileData) => void;
}

export default function ProfileEdit({ initialData, onUpdate }: ProfileEditProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [showAvatarCropper, setShowAvatarCropper] = useState(false);
  const [showPhoneChange, setShowPhoneChange] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [profileData, setProfileData] = useState<ProfileData | null>(initialData || null);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isDirty }
  } = useForm<ProfileUpdateRequest>({
    defaultValues: {
      nickname: initialData?.nickname || '',
      real_name: initialData?.real_name || '',
      email: initialData?.email || '',
    }
  });

  // Load profile data if not provided
  useEffect(() => {
    if (!initialData) {
      loadProfileData();
    }
  }, [initialData]);

  const loadProfileData = async () => {
    try {
      const data = await profileAPI.getProfile();
      setProfileData(data);
      setValue('nickname', data.nickname || '');
      setValue('real_name', data.real_name || '');
      setValue('email', data.email || '');
    } catch (error) {
      toast.error('Failed to load profile data');
    }
  };

  const handleAvatarSelect = (file: File) => {
    setAvatarFile(file);
    setShowAvatarCropper(true);
  };

  const handleAvatarCropped = async (croppedFile: File) => {
    try {
      setIsLoading(true);
      const response = await profileAPI.uploadAvatar(croppedFile);
      setProfileData(prev => prev ? { ...prev, avatar_url: response.avatar_url } : null);
      toast.success('Avatar updated successfully');
      onUpdate?.(response);
    } catch (error) {
      toast.error('Failed to update avatar');
    } finally {
      setIsLoading(false);
      setShowAvatarCropper(false);
    }
  };

  const handlePhoneChanged = (newPhoneNumber: string) => {
    setProfileData(prev => prev ? { ...prev, phone_number: newPhoneNumber } : null);
    toast.success('Phone number updated successfully');
  };

  const onSubmit = async (data: ProfileUpdateRequest) => {
    try {
      setIsLoading(true);
      const response = await profileAPI.updateProfile(data);
      setProfileData(response);
      toast.success('Profile updated successfully');
      onUpdate?.(response);
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setIsLoading(false);
    }
  };

  if (!profileData) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Edit Profile</h1>
        <button
          onClick={() => setShowHistory(true)}
          className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <History size={16} />
          View History
        </button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Avatar Section */}
        <div className="flex flex-col items-center space-y-4">
          <div className="relative">
            <img
              src={profileData.avatar_url || '/default-avatar.png'}
              alt="Profile Avatar"
              className="w-24 h-24 rounded-full object-cover border-4 border-gray-200"
            />
            <button
              type="button"
              onClick={() => document.getElementById('avatar-input')?.click()}
              className="absolute bottom-0 right-0 p-2 bg-primary text-white rounded-full hover:bg-primary-dark transition-colors"
            >
              <Camera size={16} />
            </button>
          </div>
          <input
            id="avatar-input"
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleAvatarSelect(file);
            }}
            className="hidden"
          />
          <p className="text-sm text-gray-500">Click the camera icon to change your avatar</p>
        </div>

        {/* Basic Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Nickname */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              <User size={16} className="inline mr-2" />
              Nickname
            </label>
            <input
              {...register('nickname', {
                required: 'Nickname is required',
                minLength: { value: 2, message: 'Nickname must be at least 2 characters' },
                maxLength: { value: 50, message: 'Nickname must be less than 50 characters' }
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Enter your nickname"
            />
            {errors.nickname && (
              <p className="text-sm text-red-600">{errors.nickname.message}</p>
            )}
          </div>

          {/* Real Name */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Real Name
            </label>
            <input
              {...register('real_name', {
                maxLength: { value: 100, message: 'Real name must be less than 100 characters' }
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Enter your real name"
            />
            {errors.real_name && (
              <p className="text-sm text-red-600">{errors.real_name.message}</p>
            )}
          </div>

          {/* Email */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              <Mail size={16} className="inline mr-2" />
              Email
            </label>
            <input
              {...register('email', {
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: 'Invalid email address'
                }
              })}
              type="email"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              placeholder="Enter your email"
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          {/* Phone Number */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              <Phone size={16} className="inline mr-2" />
              Phone Number
            </label>
            <div className="flex items-center space-x-2">
              <input
                value={profileData.phone_number || 'Not set'}
                readOnly
                className="flex-1 px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-600"
              />
              <button
                type="button"
                onClick={() => setShowPhoneChange(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Change
              </button>
            </div>
            {profileData.phone_verified && (
              <p className="text-sm text-green-600">✓ Phone number verified</p>
            )}
          </div>
        </div>

        {/* Account Status Information */}
        <div className="bg-gray-50 p-4 rounded-lg space-y-2">
          <h3 className="font-medium text-gray-800">Account Status</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Real Name Verified: </span>
              <span className={profileData.real_name_verified ? "text-green-600" : "text-gray-500"}>
                {profileData.real_name_verified ? "✓ Verified" : "Not verified"}
              </span>
            </div>
            <div>
              <span className="text-gray-600">Member Since: </span>
              <span className="text-gray-800">
                {new Date(profileData.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-end space-x-4">
          <button
            type="button"
            onClick={loadProfileData}
            className="px-6 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!isDirty || isLoading}
            className="flex items-center gap-2 px-6 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save size={16} />
            {isLoading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>

      {/* Modals */}
      {showAvatarCropper && (
        <AvatarCropper
          file={avatarFile!}
          onCropped={handleAvatarCropped}
          onClose={() => setShowAvatarCropper(false)}
        />
      )}

      {showPhoneChange && (
        <PhoneChangeModal
          currentPhone={profileData.phone_number}
          onChanged={handlePhoneChanged}
          onClose={() => setShowPhoneChange(false)}
        />
      )}

      {showHistory && (
        <ProfileHistory onClose={() => setShowHistory(false)} />
      )}
    </div>
  );
}