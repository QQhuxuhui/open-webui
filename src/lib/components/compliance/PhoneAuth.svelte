<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	
	const dispatch = createEventDispatcher();

	export let loading = false;
	export let mode: 'signin' | 'signup' = 'signin';

	let phone = '';
	let code = '';
	let name = '';
	let privacyAgreed = false;
	let termsAgreed = false;
	let codeSent = false;
	let countdown = 0;

	let countdownInterval: NodeJS.Timeout | null = null;

	const startCountdown = () => {
		countdown = 60;
		countdownInterval = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				clearInterval(countdownInterval!);
				countdownInterval = null;
			}
		}, 1000);
	};

	const sendCode = async () => {
		if (!phone.match(/^1[3-9]\d{9}$/)) {
			toast.error('请输入正确的手机号');
			return;
		}

		try {
			const res = await fetch('/api/v1/auths/phone/send-code', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ phone })
			});

			if (res.ok) {
				codeSent = true;
				startCountdown();
				toast.success('验证码发送成功');
			} else {
				const error = await res.json();
				toast.error(error.detail || '验证码发送失败');
			}
		} catch (err) {
			toast.error('网络错误，请稍后再试');
		}
	};

	const handleSubmit = async () => {
		if (!phone || !code) {
			toast.error('请填写完整信息');
			return;
		}

		if (mode === 'signup') {
			if (!name) {
				toast.error('请输入姓名');
				return;
			}
			if (!privacyAgreed || !termsAgreed) {
				toast.error('请同意隐私协议和服务协议');
				return;
			}
		}

		loading = true;

		try {
			const endpoint = mode === 'signup' ? '/api/v1/auths/phone/signup' : '/api/v1/auths/phone/signin';
			const body = mode === 'signup' 
				? { phone, code, name, privacy_agreed: privacyAgreed, terms_agreed: termsAgreed }
				: { phone, code };

			const res = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body)
			});

			if (res.ok) {
				const data = await res.json();
				dispatch('success', data);
			} else {
				const error = await res.json();
				toast.error(error.detail || '认证失败');
			}
		} catch (err) {
			toast.error('网络错误，请稍后再试');
		} finally {
			loading = false;
		}
	};
</script>

<div class="w-full max-w-md mx-auto">
	<div class="space-y-4">
		<div>
			<label for="phone" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
				手机号
			</label>
			<input
				id="phone"
				bind:value={phone}
				type="tel"
				placeholder="请输入手机号"
				class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
				disabled={loading}
			/>
		</div>

		<div class="flex gap-2">
			<div class="flex-1">
				<label for="code" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					验证码
				</label>
				<input
					id="code"
					bind:value={code}
					type="text"
					placeholder="请输入验证码"
					maxlength="6"
					class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
					disabled={loading}
				/>
			</div>
			<button
				type="button"
				on:click={sendCode}
				disabled={loading || countdown > 0 || !phone}
				class="px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium min-w-[100px] transition-colors"
			>
				{countdown > 0 ? `${countdown}s` : '发送验证码'}
			</button>
		</div>

		{#if mode === 'signup'}
			<div>
				<label for="name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					姓名
				</label>
				<input
					id="name"
					bind:value={name}
					type="text"
					placeholder="请输入您的姓名"
					class="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
					disabled={loading}
				/>
			</div>

			<div class="space-y-2">
				<label class="flex items-center space-x-2">
					<input
						bind:checked={privacyAgreed}
						type="checkbox"
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
						disabled={loading}
					/>
					<span class="text-sm text-gray-600 dark:text-gray-400">
						我已阅读并同意
						<a href="/privacy" class="text-blue-600 hover:underline" target="_blank">《隐私协议》</a>
					</span>
				</label>
				<label class="flex items-center space-x-2">
					<input
						bind:checked={termsAgreed}
						type="checkbox"
						class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
						disabled={loading}
					/>
					<span class="text-sm text-gray-600 dark:text-gray-400">
						我已阅读并同意
						<a href="/terms" class="text-blue-600 hover:underline" target="_blank">《服务协议》</a>
					</span>
				</label>
			</div>
		{/if}

		<button
			type="button"
			on:click={handleSubmit}
			disabled={loading}
			class="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
		>
			{loading ? '处理中...' : mode === 'signup' ? '注册' : '登录'}
		</button>
	</div>
</div>