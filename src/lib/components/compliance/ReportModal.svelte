<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Modal from '$lib/components/common/Modal.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let messageId: string = '';
	export let chatId: string = '';

	let loading = false;
	let category = '';
	let title = '';
	let description = '';
	let contactInfo = '';
	let screenshots: File[] = [];
	let isAnonymous = false;

	// 举报分类选项
	const categories = {
		'inappropriate': '不当内容',
		'technical': '技术问题',
		'copyright': '版权问题',
		'spam': '垃圾信息',
		'misinformation': '虚假信息',
		'other': '其他问题'
	};

	const categoriesEn = {
		'inappropriate': 'Inappropriate Content',
		'technical': 'Technical Issue',
		'copyright': 'Copyright Issue', 
		'spam': 'Spam',
		'misinformation': 'Misinformation',
		'other': 'Other Issue'
	};

	$: categoryOptions = $i18n.language.startsWith('zh') ? categories : categoriesEn;

	async function handleScreenshotUpload(event: Event) {
		const target = event.target as HTMLInputElement;
		const files = target.files;
		
		if (!files) return;
		
		// 限制最多3张截图
		if (screenshots.length + files.length > 3) {
			toast.error('最多只能上传3张截图');
			return;
		}
		
		// 验证文件大小和类型
		for (const file of Array.from(files)) {
			if (file.size > 5 * 1024 * 1024) {
				toast.error('图片大小不能超过5MB');
				return;
			}
			
			if (!file.type.startsWith('image/')) {
				toast.error('只能上传图片文件');
				return;
			}
		}
		
		screenshots = [...screenshots, ...Array.from(files)];
	}

	function removeScreenshot(index: number) {
		screenshots = screenshots.filter((_, i) => i !== index);
	}

	async function submitReport() {
		if (!category || !title) {
			toast.error('请填写必填项');
			return;
		}

		loading = true;

		try {
			// 上传截图
			const uploadedScreenshots = [];
			for (const file of screenshots) {
				const formData = new FormData();
				formData.append('file', file);

				const uploadResponse = await fetch('/api/v1/reports/upload-screenshot', {
					method: 'POST',
					headers: {
						'Authorization': `Bearer ${localStorage.getItem('token')}`
					},
					body: formData
				});

				if (uploadResponse.ok) {
					const result = await uploadResponse.json();
					uploadedScreenshots.push(result.filename);
				}
			}

			// 提交举报
			const endpoint = isAnonymous ? '/api/v1/reports/anonymous' : '/api/v1/reports';
			const headers: Record<string, string> = {
				'Content-Type': 'application/json'
			};
			
			if (!isAnonymous) {
				headers['Authorization'] = `Bearer ${localStorage.getItem('token')}`;
			}

			const response = await fetch(endpoint, {
				method: 'POST',
				headers,
				body: JSON.stringify({
					category,
					title,
					description: description || null,
					message_id: messageId || null,
					chat_id: chatId || null,
					contact_info: contactInfo || null,
					screenshot_files: uploadedScreenshots
				})
			});

			if (response.ok) {
				toast.success('举报提交成功');
				dispatch('success');
				closeModal();
			} else {
				const error = await response.json();
				toast.error(error.detail || '提交失败');
			}
		} catch (err) {
			toast.error('网络错误，请稍后再试');
		} finally {
			loading = false;
		}
	}

	function closeModal() {
		show = false;
		// 重置表单
		category = '';
		title = '';
		description = '';
		contactInfo = '';
		screenshots = [];
		isAnonymous = false;
	}
</script>

<Modal bind:show size="md">
	<div class="p-6">
		<div class="flex justify-between items-center mb-6">
			<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
				{$i18n.language.startsWith('zh') ? '举报反馈' : 'Report Feedback'}
			</h2>
			<button 
				on:click={closeModal}
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
				</svg>
			</button>
		</div>

		<form on:submit|preventDefault={submitReport} class="space-y-4">
			<!-- 举报类型 -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.language.startsWith('zh') ? '举报类型' : 'Report Category'} *
				</label>
				<select 
					bind:value={category}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
					required
				>
					<option value="">
						{$i18n.language.startsWith('zh') ? '请选择类型' : 'Select Category'}
					</option>
					{#each Object.entries(categoryOptions) as [key, label]}
						<option value={key}>{label}</option>
					{/each}
				</select>
			</div>

			<!-- 标题 -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.language.startsWith('zh') ? '问题标题' : 'Title'} *
				</label>
				<input 
					bind:value={title}
					type="text"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
					placeholder={$i18n.language.startsWith('zh') ? '简要描述问题' : 'Brief description'}
					required
				/>
			</div>

			<!-- 详细描述 -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.language.startsWith('zh') ? '详细描述' : 'Detailed Description'}
				</label>
				<textarea 
					bind:value={description}
					rows="4"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white resize-none"
					placeholder={$i18n.language.startsWith('zh') ? '请详细说明遇到的问题...' : 'Please describe the issue in detail...'}
				></textarea>
			</div>

			<!-- 联系方式 -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.language.startsWith('zh') ? '联系方式' : 'Contact Info'}
					<span class="text-gray-500 text-xs ml-1">
						({$i18n.language.startsWith('zh') ? '可选' : 'Optional'})
					</span>
				</label>
				<input 
					bind:value={contactInfo}
					type="text"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
					placeholder={$i18n.language.startsWith('zh') ? '邮箱或手机号' : 'Email or phone number'}
				/>
			</div>

			<!-- 截图上传 -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					{$i18n.language.startsWith('zh') ? '截图' : 'Screenshots'}
					<span class="text-gray-500 text-xs ml-1">
						({$i18n.language.startsWith('zh') ? '最多3张，每张不超过5MB' : 'Max 3 files, 5MB each'})
					</span>
				</label>
				<input 
					type="file"
					accept="image/*"
					multiple
					on:change={handleScreenshotUpload}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
				/>
				
				<!-- 预览已选择的截图 -->
				{#if screenshots.length > 0}
					<div class="mt-2 flex flex-wrap gap-2">
						{#each screenshots as screenshot, index}
							<div class="relative">
								<img 
									src={URL.createObjectURL(screenshot)} 
									alt="Screenshot preview"
									class="w-20 h-20 object-cover rounded border"
								/>
								<button
									type="button"
									on:click={() => removeScreenshot(index)}
									class="absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs"
								>
									×
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- 匿名选项 -->
			<div class="flex items-center">
				<input 
					type="checkbox"
					id="anonymous"
					bind:checked={isAnonymous}
					class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
				/>
				<label for="anonymous" class="ml-2 text-sm text-gray-600 dark:text-gray-400">
					{$i18n.language.startsWith('zh') ? '匿名提交' : 'Submit anonymously'}
				</label>
			</div>

			<!-- 提交按钮 -->
			<div class="flex justify-end gap-3 mt-6">
				<button
					type="button"
					on:click={closeModal}
					class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
				>
					{$i18n.language.startsWith('zh') ? '取消' : 'Cancel'}
				</button>
				<button
					type="submit"
					disabled={loading || !category || !title}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium"
				>
					{loading ? 
						($i18n.language.startsWith('zh') ? '提交中...' : 'Submitting...') : 
						($i18n.language.startsWith('zh') ? '提交举报' : 'Submit Report')
					}
				</button>
			</div>
		</form>
	</div>
</Modal>