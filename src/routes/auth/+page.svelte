<script>
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp, phoneSignIn, phoneSignUp, phoneSignInWithPassword, sendVerificationCode } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest, querystringValue } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import SliderCaptcha from '$lib/components/SliderCaptcha.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'phone-signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';
	let phoneNumber = '';
	let verificationCode = '';
	let phoneLoginMethod = 'code'; // 'code' 或 'password'
	let accountInput = ''; // 用于邮箱/手机号混合输入
	let sliderCaptcha;
	let captchaVerified = false;

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const phoneSignInHandler = async () => {
		let sessionUser;
		if (phoneLoginMethod === 'password') {
			// 邮箱/手机号+密码登录
			// 判断输入是邮箱还是手机号，使用对应的登录方式
			const isPhone = /^1[3-9]\d{9}$/.test(accountInput);
			if (isPhone) {
				// 使用手机号密码登录
				sessionUser = await phoneSignInWithPassword(accountInput, password).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			} else {
				// 使用邮箱密码登录
				sessionUser = await userSignIn(accountInput, password).catch((error) => {
					toast.error(`${error}`);
					return null;
				});
			}
		} else {
			// 手机号+验证码登录
			sessionUser = await phoneSignIn(phoneNumber, verificationCode).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		}
		await setSessionUser(sessionUser);
	};

	const phoneSignUpHandler = async () => {
		const sessionUser = await phoneSignUp(name, phoneNumber, verificationCode, password, generateInitialsImage(name), email)
			.catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		await setSessionUser(sessionUser);
	};

	const sendCodeHandler = async () => {
		if (!captchaVerified) {
			toast.error('请先完成滑块验证');
			return;
		}

		if (!phoneNumber) {
			toast.error('请输入手机号');
			return;
		}

		await sendVerificationCode(phoneNumber).catch((error) => {
			toast.error(`${error}`);
			return;
		});

		toast.success('验证码已发送');
		// 重置滑块验证，防止重复发送
		if (sliderCaptcha) {
			sliderCaptcha.reset();
			captchaVerified = false;
		}
	};

	const handleCaptchaVerified = (event) => {
		captchaVerified = event.detail.success;
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else if (mode === 'phone-signin') {
			await phoneSignInHandler();
		} else if (mode === 'phone-signup') {
			await phoneSignUpHandler();
		} else {
			await signUpHandler();
		}
	};

	const checkOauthCallback = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = $page.url.searchParams.get('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();

		form = $page.url.searchParams.get('form');

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'phone-signup';
	}}
/>

<!-- 工业级专业认证页面背景 -->
<div class="w-full h-screen max-h-[100dvh] text-gray-800 relative overflow-hidden" id="auth-page">
	<!-- 工业级背景设计 -->
	<div class="auth-background absolute inset-0">
		<!-- 主背景：浅蓝色渐变 -->
		<div class="absolute inset-0 bg-gradient-to-br from-slate-50 via-blue-50 to-blue-100"></div>

		<!-- 几何网格纹理 -->
		<div class="absolute inset-0 opacity-40">
			<svg class="w-full h-full" xmlns="http://www.w3.org/2000/svg">
				<defs>
					<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
						<path d="M 40 0 L 0 0 0 40" fill="none" stroke="#94a3b8" stroke-width="0.5"/>
					</pattern>
					<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">
						<circle cx="10" cy="10" r="1" fill="#64748b" opacity="0.3"/>
					</pattern>
				</defs>
				<rect width="100%" height="100%" fill="url(#grid)" />
				<rect width="100%" height="100%" fill="url(#dots)" />
			</svg>
		</div>

		<!-- 工业风几何装饰 -->
		<div class="absolute inset-0">
			<!-- 左上角装饰 -->
			<div class="absolute top-0 left-0 w-64 h-64 transform -translate-x-32 -translate-y-32">
				<div class="w-full h-full border border-blue-200/30 rounded-full"></div>
				<div class="absolute inset-8 border border-blue-300/50 rounded-full"></div>
			</div>

			<!-- 右下角装饰 -->
			<div class="absolute bottom-0 right-0 w-96 h-96 transform translate-x-48 translate-y-48">
				<div class="w-full h-full border border-blue-200/30 rounded-full"></div>
				<div class="absolute inset-12 border border-blue-300/50 rounded-full"></div>
				<div class="absolute inset-24 border border-blue-400/40 rounded-full"></div>
			</div>

			<!-- 中间的六边形装饰 -->
			<div class="absolute top-1/4 right-1/4 w-32 h-32 transform rotate-12">
				<svg viewBox="0 0 100 100" class="w-full h-full">
					<polygon points="50,5 90,25 90,75 50,95 10,75 10,25"
						fill="none" stroke="#60a5fa" stroke-width="1" opacity="0.3"/>
				</svg>
			</div>
		</div>
	</div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-10" />

	{#if loaded}
		<!-- 现代化认证容器 -->
		<div
			class="fixed bg-transparent min-h-screen w-full flex justify-center items-center font-primary z-50"
			id="auth-container"
		>
			<div class="w-full max-w-md mx-auto px-6">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full sm:max-w-md">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200"
						>
							<div>
								{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>

							<div>
								<Spinner className="size-5" />
							</div>
						</div>
					</div>
				{:else}
					<!-- 工业风格认证卡片 -->
					<div class="glass-container-industrial p-8 animate-slide-up">
						<div class="w-full text-gray-800 dark:text-gray-100">
							{#if $config?.metadata?.auth_logo_position === 'center'}
								<div class="flex justify-center mb-8">
									<div class="relative">
										<img
											id="logo"
											crossorigin="anonymous"
											src="{WEBUI_BASE_URL}/static/favicon.png"
											class="size-20 rounded-2xl shadow-lg border-2 border-white/20"
											alt=""
										/>
										<div class="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/20 to-transparent"></div>
									</div>
								</div>
							{/if}
							<form
								class=" flex flex-col justify-center"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								<!-- 现代化标题 -->
								<div class="mb-6 text-center">
									<h1 class="text-3xl font-bold gradient-text mb-2">
										{#if $config?.onboarding ?? false}
											{$i18n.t(`Get started with {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'ldap'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}} with LDAP`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'signin'}
											{$i18n.t(`Sign in to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{:else if mode === 'phone-signin'}
											使用账号登录 {{$WEBUI_NAME}}
										{:else if mode === 'phone-signup'}
											使用手机号注册 {{$WEBUI_NAME}}
										{:else}
											{$i18n.t(`Sign up to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
										{/if}
									</h1>

									{#if $config?.onboarding ?? false}
										<p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
											ⓘ {$WEBUI_NAME}
											{$i18n.t(
												'does not make any external connections, and your data stays securely on your locally hosted server.'
											)}
										</p>
									{/if}
								</div>

								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<div class="flex flex-col mt-4">
										{#if mode === 'signup' || mode === 'phone-signup'}
											<div class="input-modern-wrapper">
												<input
													bind:value={name}
													type="text"
													id="name"
													class="input-modern"
													autocomplete="name"
													placeholder=" "
													required
												/>
												<label for="name" class="floating-label">
													{$i18n.t('Name')}
												</label>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div class="input-modern-wrapper">
												<input
													bind:value={ldapUsername}
													type="text"
													id="username"
													class="input-modern"
													autocomplete="username"
													name="username"
													placeholder=" "
													required
												/>
												<label for="username" class="floating-label">
													{$i18n.t('Username')}
												</label>
											</div>
										{:else if mode === 'phone-signup'}
											<div class="input-modern-wrapper">
												<input
													bind:value={phoneNumber}
													type="tel"
													id="phone"
													class="input-modern"
													autocomplete="tel"
													name="phone"
													placeholder=" "
													required
												/>
												<label for="phone" class="floating-label">
													手机号 <span class="text-red-500 ml-1">*</span>
												</label>
											</div>

											<div class="input-modern-wrapper">
												<input
													bind:value={email}
													type="email"
													id="email-signup"
													class="input-modern"
													autocomplete="email"
													name="email"
													placeholder=" "
												/>
												<label for="email-signup" class="floating-label">
													邮箱 <span class="text-gray-500 ml-1 text-xs">(可选)</span>
												</label>
											</div>
										{:else if mode === 'phone-signin'}
											<!-- 手机号登录：支持密码或验证码两种方式 -->
											<div class="mb-6">
												<div class="flex gap-3 mb-6">
													<button
														type="button"
														class="flex-1 py-2.5 px-4 text-sm rounded-lg font-medium transition-all duration-200 {phoneLoginMethod === 'password' ? 'btn-primary-modern' : 'btn-secondary-modern'}"
														on:click={() => phoneLoginMethod = 'password'}
													>
														密码登录
													</button>
													<button
														type="button"
														class="flex-1 py-2.5 px-4 text-sm rounded-lg font-medium transition-all duration-200 {phoneLoginMethod === 'code' ? 'btn-primary-modern' : 'btn-secondary-modern'}"
														on:click={() => phoneLoginMethod = 'code'}
													>
														验证码登录
													</button>
												</div>

												{#if phoneLoginMethod === 'password'}
													<div class="input-modern-wrapper">
														<input
															bind:value={accountInput}
															type="text"
															id="account-input"
															class="input-modern"
															placeholder=" "
															autocomplete="username"
															required
														/>
														<label for="account-input" class="floating-label">
															邮箱或手机号
														</label>
													</div>

													<div class="input-modern-wrapper">
														<SensitiveInput
															bind:value={password}
															type="password"
															id="account-password"
															class="input-modern"
															placeholder=" "
															autocomplete="current-password"
															required
														/>
														<label for="account-password" class="floating-label">
															密码
														</label>
													</div>
												{:else}
													<div class="input-modern-wrapper">
														<input
															bind:value={phoneNumber}
															type="tel"
															id="phone"
															class="input-modern"
															autocomplete="tel"
															name="phone"
															placeholder=" "
															required
														/>
														<label for="phone" class="floating-label">
															手机号
														</label>
													</div>

													<!-- 验证码登录逻辑 -->
													<!-- 滑块验证 -->
													<div class="mb-6">
														<label class="block text-sm font-medium industrial-text-primary mb-3">
															安全验证
														</label>
														<div class="glass-card-industrial p-4">
															<SliderCaptcha
																bind:this={sliderCaptcha}
																on:verified={handleCaptchaVerified}
															/>
														</div>
													</div>

													<div class="input-modern-wrapper relative">
														<input
															bind:value={verificationCode}
															type="text"
															id="verification-code"
															class="input-modern pr-24"
															placeholder=" "
															required
														/>
														<label for="verification-code" class="floating-label">
															验证码
														</label>
														<button
															type="button"
															on:click={sendCodeHandler}
															class="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 {captchaVerified ? 'btn-primary-modern' : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed border border-gray-300 dark:border-gray-600'}"
															disabled={!captchaVerified}
														>
															发送验证码
														</button>
													</div>
													{/if}
												</div>
										{:else}
											<div class="input-modern-wrapper">
												<input
													bind:value={email}
													type="email"
													id="email"
													class="input-modern"
													autocomplete="email"
													name="email"
													placeholder=" "
													required
												/>
												<label for="email" class="floating-label">
													{$i18n.t('Email')}
												</label>
											</div>
										{/if}

										{#if mode !== 'phone-signin' && mode === 'phone-signup'}
											<!-- 手机号注册需要密码 -->
											<div class="input-modern-wrapper">
												<SensitiveInput
													bind:value={password}
													type="password"
													id="password"
													class="input-modern"
													placeholder=" "
													autocomplete="new-password"
													name="password"
													required
												/>
												<label for="password" class="floating-label">
													设置密码
												</label>
											</div>
										{:else if mode !== 'phone-signin' && mode !== 'phone-signup'}
											<!-- 传统邮箱认证的密码字段 -->
											<div class="input-modern-wrapper">
												<SensitiveInput
													bind:value={password}
													type="password"
													id="password"
													class="input-modern"
													placeholder=" "
													autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
													name="password"
													required
												/>
												<label for="password" class="floating-label">
													{$i18n.t('Password')}
												</label>
											</div>
										{/if}

										{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
											<div class="input-modern-wrapper">
												<SensitiveInput
													bind:value={confirmPassword}
													type="password"
													id="confirm-password"
													class="input-modern"
													placeholder=" "
													autocomplete="new-password"
													name="confirm-password"
													required
												/>
												<label for="confirm-password" class="floating-label">
													{$i18n.t('Confirm Password')}
												</label>
											</div>
										{/if}
									</div>
								{/if}
								<div class="mt-8">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										{#if mode === 'ldap'}
											<button
												class="btn-primary-modern w-full py-3 text-base font-semibold relative overflow-hidden"
												type="submit"
											>
												<span class="btn-ripple"></span>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												class="btn-primary-modern w-full py-3 text-base font-semibold relative overflow-hidden"
												type="submit"
											>
												<span class="btn-ripple"></span>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: mode === 'phone-signin'
														? '登录'
														: mode === 'phone-signup'
															? '手机号注册'
															: ($config?.onboarding ?? false)
																? $i18n.t('Create Admin Account')
																: $i18n.t('Create Account')}
											</button>

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div class="mt-6 text-sm text-center">
													<span class="text-gray-600 dark:text-gray-400">
														{mode === 'signin' || mode === 'phone-signin'
															? $i18n.t("Don't have an account?")
															: $i18n.t('Already have an account?')}
													</span>

													<button
														class="ml-2 font-semibold text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors duration-200 underline decoration-2 underline-offset-4 hover:decoration-primary-500"
														type="button"
														on:click={() => {
															if (mode === 'signin') {
																mode = 'signup';
															} else if (mode === 'phone-signin') {
																mode = 'phone-signup';
															} else if (mode === 'phone-signup') {
																mode = 'phone-signin';
															} else {
																mode = 'signin';
															}
														}}
													>
														{mode === 'signin' || mode === 'phone-signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
													</button>
												</div>
											{/if}
										{/if}
									{/if}
								</div>
							</form>

							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="relative flex items-center justify-center w-full my-6">
									<hr class="w-full h-px border-0 bg-gradient-to-r from-transparent via-gray-300/30 to-transparent dark:via-gray-600/30" />
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<span
											class="absolute px-4 text-sm font-medium text-gray-500 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm rounded-full"
											>{$i18n.t('or')}</span
										>
									{/if}
								</div>
								<div class="flex flex-col space-y-3">
									{#if $config?.oauth?.providers?.google}
										<button
											class="btn-secondary-modern flex justify-center items-center w-full py-3 text-sm font-semibold"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												class="size-6 mr-3"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/><path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/><path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/><path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/><path fill="none" d="M0 0h48v48H0z" />
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="btn-secondary-modern flex justify-center items-center w-full py-3 text-sm font-semibold"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												class="size-6 mr-3"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
													x="1"
													y="11"
													width="9"
													height="9"
													fill="#00a4ef"
												/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
													x="11"
													y="11"
													width="9"
													height="9"
													fill="#ffb900"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.github}
										<button
											class="btn-secondary-modern flex justify-center items-center w-full py-3 text-sm font-semibold"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												class="size-6 mr-3"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}
									{#if $config?.oauth?.providers?.oidc}
										<button
											class="btn-secondary-modern flex justify-center items-center w-full py-3 text-sm font-semibold"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-6 mr-3"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>

											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}
								</div>
							{/if}

							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-6">
									<button
										class="btn-ghost-modern w-full py-2.5 text-sm font-medium"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										<span
											>{mode === 'ldap'
												? $i18n.t('Continue with Email')
												: $i18n.t('Continue with LDAP')}</span
										>
									</button>
								</div>
							{/if}
						</div>
						{#if $config?.metadata?.login_footer}
							<div class="max-w-3xl mx-auto">
								<div class="mt-2 text-[0.7rem] text-gray-500 dark:text-gray-400 marked">
									{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>

		{#if !$config?.metadata?.auth_logo_position}
			<div class="fixed m-10 z-50">
				<div class="flex space-x-2">
					<div class=" self-center">
						<img
							id="logo"
							crossorigin="anonymous"
							src="{WEBUI_BASE_URL}/static/favicon.png"
							class=" w-6 rounded-full"
							alt=""
						/>
					</div>
				</div>
			</div>
		{/if}
	{/if}
</div>
