<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import AIContentLabel from './AIContentLabel.svelte';
	import { detectAIGeneratedContent, createVideoWatermarkOverlay, adjustWatermarkForViewport } from '$lib/utils/aiWatermark';
	
	const i18n = getContext('i18n');
	
	export let src = '';
	export let className = '';
	export let controls = true;
	export let autoplay = false;
	export let loop = false;
	export let muted = false;
	export let forceAIWatermark = false; // 强制添加AI标识
	
	let videoElement: HTMLVideoElement;
	let videoContainer: HTMLDivElement;
	let isAIGenerated = false;
	let showAILabel = false;
	let watermarkOverlay: HTMLDivElement;
	
	onMount(() => {
		// 检测是否为AI生成内容
		isAIGenerated = forceAIWatermark || detectAIGeneratedContent({ 
			getAttribute: (attr: string) => {
				if (attr === 'src') return src;
				return null;
			},
			hasAttribute: (attr: string) => false,
			classList: { contains: () => false }
		} as Element);
		
		if (isAIGenerated) {
			showAILabel = true;
			addWatermarkToVideo();
		}
	});
	
	function addWatermarkToVideo() {
		if (!videoElement || !videoContainer) return;
		
		try {
			// 获取响应式水印设置
			const watermarkOptions = adjustWatermarkForViewport(videoElement);
			
			// 添加中英文水印
			const watermarkText = $i18n?.language?.startsWith('zh') ? '内容由AI生成' : 'AI Generated';
			
			// 创建水印覆盖层
			watermarkOverlay = createVideoWatermarkOverlay(videoElement, {
				...watermarkOptions,
				text: watermarkText
			});
			
			// 添加到容器中
			videoContainer.appendChild(watermarkOverlay);
			
		} catch (error) {
			console.warn('Failed to add AI watermark to video:', error);
		}
	}
	
	// 响应式调整水印
	function handleResize() {
		if (isAIGenerated && watermarkOverlay) {
			const options = adjustWatermarkForViewport(videoElement);
			Object.assign(watermarkOverlay.style, {
				fontSize: `${options.fontSize}px`,
				opacity: options.opacity!.toString()
			});
		}
	}
</script>

<svelte:window on:resize={handleResize} />

<div bind:this={videoContainer} class="ai-video-container {className}">
	<video 
		bind:this={videoElement}
		{src}
		{controls}
		{autoplay}
		{loop}
		{muted}
		class="w-full h-auto rounded-lg"
		on:loadedmetadata={addWatermarkToVideo}
	>
		<track kind="captions" />
		Your browser does not support the video tag.
	</video>
	
	<!-- AI内容标识 -->
	{#if showAILabel}
		<AIContentLabel type="video" />
	{/if}
</div>

<style>
	.ai-video-container {
		position: relative;
		display: inline-block;
		width: fit-content;
	}
	
	.ai-video-container video {
		display: block;
	}
	
	:global(.ai-watermark-overlay) {
		font-family: Arial, sans-serif;
		font-weight: bold;
		white-space: nowrap;
	}
</style>