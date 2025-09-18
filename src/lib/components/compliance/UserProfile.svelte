<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let loading = false;

	let profileData = {
		real_name: '',
		id_card_masked: '',
		verified: false,
		verification_status: 'not_started',
		has_id_card_photos: false
	};

	let formData = {
		real_name: '',
		id_card: ''
	};

	let idCardFrontFile: File | null = null;
	let idCardBackFile: File | null = null;
	let submitting = false;
	let uploading = false;

	// 状态映射
	const statusMessages = {
		'not_started': { 
			zh: '尚未开始实名认证', 
			en: 'Real-name verification not started',
			color: 'text-gray-500'
		},
		'pending': { 
			zh: '实名认证审核中', 
			en: 'Real-name verification pending',
			color: 'text-yellow-500'
		},
		'approved': { 
			zh: '实名认证已通过', 
			en: 'Real-name verification approved',
			color: 'text-green-500'
		},
		'rejected': { 
			zh: '实名认证被拒绝', 
			en: 'Real-name verification rejected',
			color: 'text-red-500'
		}
	};

	// 页面加载时获取用户资料
	async function loadProfile() {
		try {
			const res = await fetch('/api/v1/profile', {
				headers: {
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (res.ok) {
				profileData = await res.json();
				// 如果有已保存的信息，填充表单（仅姓名，身份证号不回填）
				if (profileData.real_name) {
					formData.real_name = profileData.real_name;
				}
			}
		} catch (err) {
			console.error('加载用户资料失败:', err);
		}
	}

	// 提交实名认证信息
	async function submitProfile() {
		if (!formData.real_name || !formData.id_card) {
			toast.error('请填写完整的实名认证信息');
			return;
		}

		// 验证姓名格式（2-20位中文）
		if (!/^[\u4e00-\u9fa5·]{2,20}$/.test(formData.real_name)) {
			toast.error('请输入正确的中文姓名（2-20位）');
			return;
		}

		// 验证身份证格式
		if (!/^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$/.test(formData.id_card)) {
			toast.error('请输入正确的身份证号码');
			return;
		}

		submitting = true;

		try {
			const endpoint = profileData.verification_status === 'not_started' 
				? '/api/v1/profile' 
				: '/api/v1/profile';
			
			const method = profileData.verification_status === 'not_started' ? 'POST' : 'PUT';

			const res = await fetch(endpoint, {
				method: method,
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				},
				body: JSON.stringify(formData)
			});

			if (res.ok) {
				toast.success('实名认证信息提交成功');
				await loadProfile();
				dispatch('success');
			} else {
				const error = await res.json();
				toast.error(error.detail || '提交失败');
			}
		} catch (err) {
			toast.error('网络错误，请稍后再试');
		} finally {
			submitting = false;
		}
	}

	// 上传身份证照片
	async function uploadIdCardPhoto(file: File, type: 'front' | 'back') {
		if (!file) return;

		// 验证文件
		if (file.size > 5 * 1024 * 1024) {
			toast.error('图片大小不能超过5MB');
			return;
		}

		if (!file.type.startsWith('image/')) {
			toast.error('只能上传图片文件');
			return;
		}

		uploading = true;

		try {
			const formData = new FormData();
			formData.append('file', file);
			formData.append('file_type', type);

			const res = await fetch('/api/v1/profile/upload-id-card?file_type=' + type, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${localStorage.getItem('token')}`
				},
				body: formData
			});

			if (res.ok) {
				toast.success(`身份证${type === 'front' ? '正面' : '背面'}照片上传成功`);
				await loadProfile();
			} else {
				const error = await res.json();
				toast.error(error.detail || '上传失败');
			}
		} catch (err) {
			toast.error('网络错误，请稍后再试');
		} finally {
			uploading = false;
		}
	}

	// 处理文件选择
	function handleFileSelect(event: Event, type: 'front' | 'back') {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		
		if (file) {
			if (type === 'front') {
				idCardFrontFile = file;
			} else {
				idCardBackFile = file;
			}
			uploadIdCardPhoto(file, type);
		}
	}

	// 获取状态显示信息
	$: statusInfo = statusMessages[profileData.verification_status] || statusMessages['not_started'];
	$: statusText = $i18n.language.startsWith('zh') ? statusInfo.zh : statusInfo.en;

	// 组件挂载时加载数据
	loadProfile();
</script>

<div class="max-w-2xl mx-auto p-6">
	<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
		<!-- 头部 -->
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
				{$i18n.language.startsWith('zh') ? '实名认证' : 'Real-name Verification'}
			</h2>
			<div class="mt-2 flex items-center gap-2">
				<span class="text-sm {statusInfo.color}">● {statusText}</span>
				{#if profileData.verified}
					<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
						{$i18n.language.startsWith('zh') ? '已认证' : 'Verified'}
					</span>
				{/if}
			</div>
		</div>

		<!-- 内容 -->
		<div class="p-6 space-y-6">
			<!-- 认证信息表单 -->
			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.language.startsWith('zh') ? '真实姓名' : 'Real Name'} *
					</label>
					<input
						bind:value={formData.real_name}
						type="text"
						placeholder={$i18n.language.startsWith('zh') ? '请输入您的真实姓名' : 'Enter your real name'}
						class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						disabled={submitting || uploading || profileData.verified}
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{$i18n.language.startsWith('zh') ? '身份证号码' : 'ID Card Number'} *
					</label>
					<input
						bind:value={formData.id_card}
						type="text"
						maxlength="18"
						placeholder={$i18n.language.startsWith('zh') ? 
							(profileData.id_card_masked || '请输入18位身份证号码') : 
							(profileData.id_card_masked || 'Enter 18-digit ID card number')
						}
						class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						disabled={submitting || uploading || profileData.verified}
					/>
					{#if profileData.id_card_masked}
						<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
							{$i18n.language.startsWith('zh') ? '当前: ' : 'Current: '}{profileData.id_card_masked}
						</p>
					{/if}
				</div>

				{#if !profileData.verified}
					<button
						type="button"
						on:click={submitProfile}
						disabled={submitting || uploading || !formData.real_name || !formData.id_card}
						class="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
					>
						{submitting ? 
							($i18n.language.startsWith('zh') ? '提交中...' : 'Submitting...') : 
							($i18n.language.startsWith('zh') ? '提交认证信息' : 'Submit for Verification')
						}
					</button>
				{/if}
			</div>

			<!-- 身份证照片上传 -->
			<div class="border-t border-gray-200 dark:border-gray-700 pt-6">
				<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
					{$i18n.language.startsWith('zh') ? '身份证照片' : 'ID Card Photos'}
					<span class="text-sm font-normal text-gray-500 dark:text-gray-400 ml-2">
						({$i18n.language.startsWith('zh') ? '可选，有助于加快审核' : 'Optional, helps speed up verification'})
					</span>
				</h3>

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<!-- 身份证正面 -->
					<div class="space-y-2">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.language.startsWith('zh') ? '身份证正面' : 'ID Card Front'}
						</label>
						<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4 text-center">
							<input
								type="file"
								accept="image/*"
								on:change={(e) => handleFileSelect(e, 'front')}
								class="hidden"
								id="id-card-front"
								disabled={uploading || profileData.verified}
							/>
							<label 
								for="id-card-front" 
								class="cursor-pointer flex flex-col items-center"
								class:cursor-not-allowed={uploading || profileData.verified}
							>
								<svg class="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
								</svg>
								<span class="text-sm text-gray-500 dark:text-gray-400">
									{$i18n.language.startsWith('zh') ? '点击上传' : 'Click to upload'}
								</span>
							</label>
						</div>
					</div>

					<!-- 身份证背面 -->
					<div class="space-y-2">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
							{$i18n.language.startsWith('zh') ? '身份证背面' : 'ID Card Back'}
						</label>
						<div class="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-4 text-center">
							<input
								type="file"
								accept="image/*"
								on:change={(e) => handleFileSelect(e, 'back')}
								class="hidden"
								id="id-card-back"
								disabled={uploading || profileData.verified}
							/>
							<label 
								for="id-card-back" 
								class="cursor-pointer flex flex-col items-center"
								class:cursor-not-allowed={uploading || profileData.verified}
							>
								<svg class="w-8 h-8 text-gray-400 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
								</svg>
								<span class="text-sm text-gray-500 dark:text-gray-400">
									{$i18n.language.startsWith('zh') ? '点击上传' : 'Click to upload'}
								</span>
							</label>
						</div>
					</div>
				</div>

				{#if profileData.has_id_card_photos}
					<div class="mt-2 text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
						</svg>
						{$i18n.language.startsWith('zh') ? '身份证照片已上传' : 'ID card photos uploaded'}
					</div>
				{/if}

				{#if uploading}
					<div class="mt-2 text-sm text-blue-600 dark:text-blue-400">
						{$i18n.language.startsWith('zh') ? '上传中...' : 'Uploading...'}
					</div>
				{/if}
			</div>

			<!-- 说明信息 -->
			<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
				<h4 class="text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
					{$i18n.language.startsWith('zh') ? '温馨提示' : 'Notice'}
				</h4>
				<ul class="text-xs text-blue-800 dark:text-blue-200 space-y-1">
					<li>• {$i18n.language.startsWith('zh') ? '实名认证信息仅用于法规合规，我们承诺严格保护您的隐私' : 'Real-name verification is only for regulatory compliance, we promise to protect your privacy'}</li>
					<li>• {$i18n.language.startsWith('zh') ? '认证信息将采用AES-256加密存储' : 'Verification information is encrypted with AES-256'}</li>
					<li>• {$i18n.language.startsWith('zh') ? '审核通常在1-3个工作日内完成' : 'Review usually completed within 1-3 business days'}</li>
					<li>• {$i18n.language.startsWith('zh') ? '如有问题请联系客服' : 'Contact support if you have any questions'}</li>
				</ul>
			</div>
		</div>
	</div>
</div>