<script>
	import { createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	let sliderContainer;
	let slider;
	let sliderText;
	let isDragging = false;
	let startX = 0;
	let currentX = 0;
	let verified = false;
	let sliderWidth = 300;
	let thumbWidth = 50;

	function handleMouseDown(e) {
		if (verified) return;
		isDragging = true;
		startX = e.clientX;
		currentX = 0;
		sliderText.textContent = '松开完成验证';
	}

	function handleMouseMove(e) {
		if (!isDragging || verified) return;

		const deltaX = e.clientX - startX;
		const maxX = sliderWidth - thumbWidth;
		currentX = Math.max(0, Math.min(deltaX, maxX));

		slider.style.left = currentX + 'px';
		slider.style.backgroundColor = `hsl(${(currentX / maxX) * 120}, 70%, 50%)`;
	}

	function handleMouseUp() {
		if (!isDragging || verified) return;
		isDragging = false;

		const maxX = sliderWidth - thumbWidth;
		const threshold = maxX * 0.9; // 需要滑动90%以上

		if (currentX >= threshold) {
			verified = true;
			slider.style.left = maxX + 'px';
			slider.style.backgroundColor = '#4CAF50';
			sliderText.textContent = '验证成功';
			dispatch('verified', { success: true });
		} else {
			// 验证失败，重置滑块
			currentX = 0;
			slider.style.left = '0px';
			slider.style.backgroundColor = '#ccc';
			sliderText.textContent = '请拖动滑块完成验证';
		}
	}

	function handleTouchStart(e) {
		if (verified) return;
		isDragging = true;
		startX = e.touches[0].clientX;
		currentX = 0;
		sliderText.textContent = '松开完成验证';
	}

	function handleTouchMove(e) {
		if (!isDragging || verified) return;
		e.preventDefault();

		const deltaX = e.touches[0].clientX - startX;
		const maxX = sliderWidth - thumbWidth;
		currentX = Math.max(0, Math.min(deltaX, maxX));

		slider.style.left = currentX + 'px';
		slider.style.backgroundColor = `hsl(${(currentX / maxX) * 120}, 70%, 50%)`;
	}

	function handleTouchEnd() {
		if (!isDragging || verified) return;
		isDragging = false;

		const maxX = sliderWidth - thumbWidth;
		const threshold = maxX * 0.9;

		if (currentX >= threshold) {
			verified = true;
			slider.style.left = maxX + 'px';
			slider.style.backgroundColor = '#4CAF50';
			sliderText.textContent = '验证成功';
			dispatch('verified', { success: true });
		} else {
			currentX = 0;
			slider.style.left = '0px';
			slider.style.backgroundColor = '#ccc';
			sliderText.textContent = '请拖动滑块完成验证';
		}
	}

	export function reset() {
		verified = false;
		currentX = 0;
		if (slider) {
			slider.style.left = '0px';
			slider.style.backgroundColor = '#ccc';
		}
		if (sliderText) {
			sliderText.textContent = '请拖动滑块完成验证';
		}
	}
</script>

<svelte:window
	on:mousemove={handleMouseMove}
	on:mouseup={handleMouseUp}
	on:touchmove={handleTouchMove}
	on:touchend={handleTouchEnd}
/>

<div class="slider-captcha">
	<div
		bind:this={sliderContainer}
		class="slider-container"
		style="width: {sliderWidth}px;"
	>
		<div class="slider-track">
			<div
				bind:this={sliderText}
				class="slider-text"
				class:verified
			>
				请拖动滑块完成验证
			</div>
			<div
				bind:this={slider}
				class="slider-thumb"
				class:verified
				on:mousedown={handleMouseDown}
				on:touchstart={handleTouchStart}
				style="width: {thumbWidth}px;"
			>
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
					<path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
				</svg>
			</div>
		</div>
	</div>
</div>

<style>
	.slider-captcha {
		margin: 10px 0;
	}

	.slider-container {
		position: relative;
		height: 40px;
		border: 1px solid #ddd;
		border-radius: 20px;
		background-color: #f8f9fa;
		overflow: hidden;
	}

	.slider-track {
		position: relative;
		width: 100%;
		height: 100%;
		border-radius: 20px;
		background: linear-gradient(90deg, #e3f2fd 0%, #bbdefb 100%);
	}

	.slider-text {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		font-size: 14px;
		color: #666;
		pointer-events: none;
		z-index: 1;
		transition: color 0.3s ease;
	}

	.slider-text.verified {
		color: #4CAF50;
		font-weight: bold;
	}

	.slider-thumb {
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		background-color: #ccc;
		border-radius: 20px;
		cursor: grab;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: background-color 0.3s ease;
		box-shadow: 0 2px 4px rgba(0,0,0,0.1);
		z-index: 2;
	}

	.slider-thumb:active {
		cursor: grabbing;
	}

	.slider-thumb.verified {
		background-color: #4CAF50 !important;
		cursor: default;
	}

	.slider-thumb svg {
		color: white;
		width: 16px;
		height: 16px;
	}

	/* 暗色主题适配 */
	:global(.dark) .slider-container {
		border-color: #555;
		background-color: #2a2a2a;
	}

	:global(.dark) .slider-track {
		background: linear-gradient(90deg, #1e3a8a 0%, #1e40af 100%);
	}

	:global(.dark) .slider-text {
		color: #ccc;
	}

	:global(.dark) .slider-thumb {
		background-color: #555;
	}
</style>