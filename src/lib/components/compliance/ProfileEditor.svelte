<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let user: any;
	export let loading = false;

	let formData = {
		name: user?.name || '',
		email: user?.email || '',
		phone: user?.phone || ''
	};

	let avatarFile: File | null = null;
	let avatarPreview: string | null = null;
	let submitting = false;

	// 处理头像文件选择
	function handleAvatarSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		
		if (!file) return;

		// 验证文件
		if (file.size > 2 * 1024 * 1024) { // 2MB限制
			toast.error($i18n.language.startsWith('zh') ? '头像大小不能超过2MB' : 'Avatar size cannot exceed 2MB');
			return;
		}

		if (!file.type.startsWith('image/')) {
			toast.error($i18n.language.startsWith('zh') ? '只能上传图片文件' : 'Only image files are allowed');
			return;
		}

		avatarFile = file;
		
		// 生成预览
		const reader = new FileReader();
		reader.onload = (e) => {
			avatarPreview = e.target?.result as string;
		};
		reader.readAsDataURL(file);
	}

	// 验证手机号格式
	function validatePhone(phone: string): boolean {
		if (!phone) return true; // 空值允许（不是必填）
		return /^1[3-9]\d{9}$/.test(phone);
	}

	// 验证邮箱格式
	function validateEmail(email: string): boolean {
		if (!email) return true; // 空值允许（不是必填）
		return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
	}

	// 提交表单
	async function submitProfile() {
		// 验证输入
		if (!formData.name.trim()) {
			toast.error($i18n.language.startsWith('zh') ? '请输入昵称' : 'Please enter nickname');
			return;
		}

		if (formData.phone && !validatePhone(formData.phone)) {
			toast.error($i18n.language.startsWith('zh') ? '请输入正确的手机号' : 'Please enter a valid phone number');
			return;
		}

		if (formData.email && !validateEmail(formData.email)) {
			toast.error($i18n.language.startsWith('zh') ? '请输入正确的邮箱地址' : 'Please enter a valid email address');
			return;
		}

		submitting = true;

		try {
			// 上传头像（如果有选择新头像）
			let avatarUrl = user?.profile_image_url;
			if (avatarFile) {
				const formData = new FormData();
				formData.append('file', avatarFile);

				const uploadRes = await fetch('/api/v1/users/upload-avatar', {
					method: 'POST',
					headers: {
						'Authorization': `Bearer ${localStorage.getItem('token')}`
					},
					body: formData
				});

				if (uploadRes.ok) {
					const result = await uploadRes.json();
					avatarUrl = result.url;
				} else {
					throw new Error('头像上传失败');
				}
			}

			// 更新用户信息
			const updateRes = await fetch('/api/v1/users/update', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify({
					name: formData.name.trim(),
					email: formData.email.trim() || null,
					phone: formData.phone.trim() || null,
					profile_image_url: avatarUrl
				})
			});

			if (updateRes.ok) {
				const updatedUser = await updateRes.json();
				toast.success($i18n.language.startsWith('zh') ? '个人信息更新成功' : 'Profile updated successfully');
				dispatch('success', updatedUser);
			} else {
				const error = await updateRes.json();
				toast.error(error.detail || ($i18n.language.startsWith('zh') ? '更新失败' : 'Update failed'));
			}
		} catch (err) {
			console.error('更新个人信息错误:', err);
			toast.error($i18n.language.startsWith('zh') ? '网络错误，请稍后再试' : 'Network error, please try again');
		} finally {
			submitting = false;
		}
	}

	// 重置表单
	function resetForm() {
		formData = {
			name: user?.name || '',
			email: user?.email || '',
			phone: user?.phone || ''
		};
		avatarFile = null;
		avatarPreview = null;
	}

	// 监听用户数据变化
	$: if (user) {
		formData = {
			name: user.name || '',
			email: user.email || '',
			phone: user.phone || ''
		};
	}
</script>

<div class="max-w-2xl mx-auto p-6">
	<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
		<!-- 头部 -->
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
				{$i18n.language.startsWith('zh') ? '编辑资料' : 'Edit Profile'}
			</h2>
		</div>

		<!-- 内容 -->
		<form on:submit|preventDefault={submitProfile} class="p-6 space-y-6">
			<!-- 头像上传 -->
			<div class="flex items-center space-x-6">
				<div class="relative">
					<div class="w-20 h-20 rounded-full bg-gray-200 dark:bg-gray-600 overflow-hidden">
						{#if avatarPreview}
							<img src={avatarPreview} alt="Avatar preview" class="w-full h-full object-cover" />
						{:else if user?.profile_image_url}
							<img src={user.profile_image_url} alt="Current avatar" class="w-full h-full object-cover" />
						{:else}
							<div class="w-full h-full flex items-center justify-center">
								<svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
								</svg>
							</div>
						{/if}
					</div>
				</div>
				<div>
					<input
						type="file"
						accept="image/*"
						on:change={handleAvatarSelect}
						class="hidden"
						id="avatar-upload"
						disabled={submitting}
					/>
					<label 
						for="avatar-upload" 
						class="inline-flex items-center px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer transition-colors"
						class:cursor-not-allowed={submitting}
					>
						<svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
						</svg>
						{$i18n.language.startsWith('zh') ? '上传头像' : 'Upload Avatar'}
					</label>
					<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						{$i18n.language.startsWith('zh') ? 'PNG, JPG, GIF 最大2MB' : 'PNG, JPG, GIF up to 2MB'}
					</p>
				</div>
			</div>

			<!-- 基本信息 -->
			<div class="space-y-4">
				<div>
					<label for="name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.language.startsWith('zh') ? '昵称' : 'Nickname'} *
					</label>
					<input
						id="name"
						bind:value={formData.name}
						type="text"
						required
						placeholder={$i18n.language.startsWith('zh') ? '请输入昵称' : 'Enter your nickname'}
						class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						disabled={submitting}
					/>
				</div>

				<div>
					<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.language.startsWith('zh') ? '邮箱地址' : 'Email Address'}
					</label>
					<input
						id="email"
						bind:value={formData.email}
						type="email"
						placeholder={$i18n.language.startsWith('zh') ? '请输入邮箱地址（可选）' : 'Enter email address (optional)'}
						class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						disabled={submitting}
					/>
				</div>

				<div>
					<label for="phone" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.language.startsWith('zh') ? '手机号码' : 'Phone Number'}
					</label>
					<input
						id="phone"
						bind:value={formData.phone}
						type="tel"
						placeholder={$i18n.language.startsWith('zh') ? '请输入手机号码（可选）' : 'Enter phone number (optional)'}
						class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						disabled={submitting}
					/>
				</div>
			</div>

			<!-- 操作按钮 -->
			<div class="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
				<button
					type="button"
					on:click={resetForm}
					disabled={submitting}
					class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
				>
					{$i18n.language.startsWith('zh') ? '重置' : 'Reset'}
				</button>
				<button
					type="submit"
					disabled={submitting || !formData.name.trim()}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
				>
					{submitting ? 
						($i18n.language.startsWith('zh') ? '保存中...' : 'Saving...') : 
						($i18n.language.startsWith('zh') ? '保存更改' : 'Save Changes')
					}
				</button>
			</div>
		</form>
	</div>
</div>