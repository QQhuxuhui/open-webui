<script lang="ts">
	export let className: string = 'size-4';
	export let text: string = '加载中...';
</script>

<div class="flex justify-center items-center text-center gap-3">
	<!-- 现代化loading动画：三个跳动的点 -->
	<div class="flex space-x-1">
		<div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
		<div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
		<div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
	</div>

	<!-- 可选的文字提示 -->
	{#if text}
		<span class="text-sm text-gray-600 dark:text-gray-400">{text}</span>
	{/if}
</div>

<style>
	@keyframes bounce {
		0%, 20%, 50%, 80%, 100% {
			transform: translateY(0);
		}
		40% {
			transform: translateY(-10px);
		}
		60% {
			transform: translateY(-5px);
		}
	}

	.animate-bounce {
		animation: bounce 1.5s infinite;
	}
</style>