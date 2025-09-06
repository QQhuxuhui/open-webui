<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Image from '$lib/components/common/Image.svelte';
	import AIContentLabel from './AIContentLabel.svelte';
	import { detectAIGeneratedContent, addImageWatermark, adjustWatermarkForViewport } from '$lib/utils/aiWatermark';
	
	const i18n = getContext('i18n');
	
	export let src = '';
	export let alt = '';
	export let className = '';
	export let imageClassName = 'rounded-lg';
	export let dismissible = false;
	export let onDismiss = () => {};
	export let forceAIWatermark = false; // 强制添加AI标识
	
	let imageElement: HTMLImageElement;
	let isAIGenerated = false;
	let watermarkedSrc = '';
	let showAILabel = false;
	
	onMount(() => {
		// 检测是否为AI生成内容
		isAIGenerated = forceAIWatermark || detectAIGeneratedContent({ 
			getAttribute: (attr: string) => {
				if (attr === 'src') return src;
				if (attr === 'alt') return alt;
				return null;
			},
			hasAttribute: (attr: string) => false,
			classList: { contains: () => false }
		} as Element);
		
		if (isAIGenerated) {
			showAILabel = true;
			addWatermarkToImage();
		}
	});
	
	async function addWatermarkToImage() {
		if (!imageElement) return;
		
		try {
			// 等待图片加载完成
			if (!imageElement.complete) {
				await new Promise((resolve) => {
					imageElement.onload = resolve;
				});
			}
			
			// 获取响应式水印设置
			const watermarkOptions = adjustWatermarkForViewport(imageElement);
			
			// 添加中英文水印
			const watermarkText = $i18n?.language?.startsWith('zh') ? '内容由AI生成' : 'AI Generated';
			
			const watermarked = await addImageWatermark(imageElement, {
				...watermarkOptions,
				text: watermarkText
			});
			
			watermarkedSrc = watermarked;
		} catch (error) {
			console.warn('Failed to add AI watermark to image:', error);
		}
	}
</script>

<div class="ai-image-container">
	{#if isAIGenerated && watermarkedSrc}
		<!-- 带水印的AI图片 -->
		<Image 
			src={watermarkedSrc}
			{alt}
			{className}
			{imageClassName}
			{dismissible}
			{onDismiss}
		/>
	{:else}
		<!-- 普通图片 -->
		<Image 
			{src}
			{alt}
			{className}
			{imageClassName}
			{dismissible}
			{onDismiss}
			bind:imageElement
		/>
	{/if}
	
	<!-- 隐藏的原始图片用于水印处理 -->
	{#if isAIGenerated && !watermarkedSrc}
		<img 
			bind:this={imageElement}
			{src} 
			{alt}
			style="display: none;"
			on:load={addWatermarkToImage}
			crossorigin="anonymous"
		/>
	{/if}
	
	<!-- AI内容标识 -->
	{#if showAILabel}
		<AIContentLabel type="image" />
	{/if}
</div>

<style>
	.ai-image-container {
		position: relative;
		display: inline-block;
		width: fit-content;
	}
</style>