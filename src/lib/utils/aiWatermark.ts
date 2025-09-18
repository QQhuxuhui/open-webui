/**
 * AI内容水印工具
 * AI Content Watermark Utilities
 */

export interface WatermarkOptions {
  text?: string;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  opacity?: number;
  fontSize?: number;
  color?: string;
}

const DEFAULT_OPTIONS: WatermarkOptions = {
  text: '内容由AI生成',
  position: 'bottom-right',
  opacity: 0.7,
  fontSize: 14,
  color: '#ffffff'
};

/**
 * 为图片添加AI生成水印
 * Add AI watermark to image
 */
export function addImageWatermark(
  imageElement: HTMLImageElement, 
  options: WatermarkOptions = {}
): Promise<string> {
  return new Promise((resolve, reject) => {
    try {
      const opts = { ...DEFAULT_OPTIONS, ...options };
      
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      if (!ctx) {
        reject(new Error('Canvas context not available'));
        return;
      }
      
      // 设置画布尺寸与图片一致
      canvas.width = imageElement.naturalWidth || imageElement.width;
      canvas.height = imageElement.naturalHeight || imageElement.height;
      
      // 绘制原始图片
      ctx.drawImage(imageElement, 0, 0);
      
      // 配置水印样式
      ctx.font = `${opts.fontSize}px Arial, sans-serif`;
      ctx.fillStyle = opts.color!;
      ctx.globalAlpha = opts.opacity!;
      ctx.textAlign = 'right';
      ctx.textBaseline = 'bottom';
      
      // 添加文字阴影以提高可读性
      ctx.shadowColor = 'rgba(0,0,0,0.5)';
      ctx.shadowBlur = 2;
      ctx.shadowOffsetX = 1;
      ctx.shadowOffsetY = 1;
      
      // 计算水印位置
      const padding = 10;
      let x, y;
      
      switch (opts.position) {
        case 'top-left':
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          x = padding;
          y = padding;
          break;
        case 'top-right':
          ctx.textAlign = 'right';
          ctx.textBaseline = 'top';
          x = canvas.width - padding;
          y = padding;
          break;
        case 'bottom-left':
          ctx.textAlign = 'left';
          ctx.textBaseline = 'bottom';
          x = padding;
          y = canvas.height - padding;
          break;
        default: // bottom-right
          x = canvas.width - padding;
          y = canvas.height - padding;
          break;
      }
      
      // 绘制水印文字
      ctx.fillText(opts.text!, x, y);
      
      // 返回带水印的图片数据URL
      resolve(canvas.toDataURL());
      
    } catch (error) {
      reject(error);
    }
  });
}

/**
 * 为视频添加AI生成水印覆盖层
 * Add AI watermark overlay to video
 */
export function createVideoWatermarkOverlay(
  videoElement: HTMLVideoElement,
  options: WatermarkOptions = {}
): HTMLDivElement {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  const overlay = document.createElement('div');
  overlay.className = 'ai-watermark-overlay';
  overlay.textContent = opts.text!;
  
  // 设置水印样式
  Object.assign(overlay.style, {
    position: 'absolute',
    fontSize: `${opts.fontSize}px`,
    color: opts.color,
    opacity: opts.opacity!.toString(),
    fontFamily: 'Arial, sans-serif',
    fontWeight: 'bold',
    textShadow: '1px 1px 2px rgba(0,0,0,0.5)',
    pointerEvents: 'none',
    userSelect: 'none',
    zIndex: '10',
    padding: '10px'
  });
  
  // 设置位置
  switch (opts.position) {
    case 'top-left':
      overlay.style.top = '0';
      overlay.style.left = '0';
      break;
    case 'top-right':
      overlay.style.top = '0';
      overlay.style.right = '0';
      break;
    case 'bottom-left':
      overlay.style.bottom = '0';
      overlay.style.left = '0';
      break;
    default: // bottom-right
      overlay.style.bottom = '0';
      overlay.style.right = '0';
      break;
  }
  
  return overlay;
}

/**
 * 检测元素是否包含AI生成的媒体内容
 * Detect if element contains AI-generated media content
 */
export function detectAIGeneratedContent(element: Element): boolean {
  // 检查data属性或class名称中的AI标识
  if (element.hasAttribute('data-ai-generated') ||
      element.classList.contains('ai-generated') ||
      element.getAttribute('alt')?.includes('AI generated') ||
      element.getAttribute('title')?.includes('AI generated')) {
    return true;
  }
  
  // 检查来源URL是否包含AI生成服务的标识
  const src = element.getAttribute('src');
  if (src) {
    const aiServiceIndicators = [
      'openai',
      'midjourney', 
      'stable-diffusion',
      'dall-e',
      'ai-generated',
      'generated-image'
    ];
    
    return aiServiceIndicators.some(indicator => 
      src.toLowerCase().includes(indicator)
    );
  }
  
  return false;
}

/**
 * 自动为页面中的AI生成媒体添加水印
 * Automatically add watermarks to AI-generated media on page
 */
export function autoWatermarkAIContent(container: Element = document.body): void {
  // 处理图片
  const images = container.querySelectorAll('img') as NodeListOf<HTMLImageElement>;
  images.forEach(async (img) => {
    if (detectAIGeneratedContent(img) && img.complete) {
      try {
        const watermarkedSrc = await addImageWatermark(img);
        img.src = watermarkedSrc;
        img.setAttribute('data-watermarked', 'true');
      } catch (error) {
        console.warn('Failed to add watermark to image:', error);
      }
    }
  });
  
  // 处理视频
  const videos = container.querySelectorAll('video') as NodeListOf<HTMLVideoElement>;
  videos.forEach((video) => {
    if (detectAIGeneratedContent(video)) {
      // 确保视频容器是相对定位的
      const videoContainer = video.parentElement;
      if (videoContainer && getComputedStyle(videoContainer).position === 'static') {
        videoContainer.style.position = 'relative';
      }
      
      // 添加水印覆盖层
      const overlay = createVideoWatermarkOverlay(video);
      if (videoContainer) {
        videoContainer.appendChild(overlay);
      } else {
        video.parentNode?.insertBefore(overlay, video.nextSibling);
      }
      
      video.setAttribute('data-watermarked', 'true');
    }
  });
}

/**
 * 响应式水印大小调整
 * Responsive watermark size adjustment
 */
export function adjustWatermarkForViewport(element: Element): WatermarkOptions {
  const viewport = {
    width: window.innerWidth,
    height: window.innerHeight
  };
  
  let fontSize = 14;
  if (viewport.width < 640) { // mobile
    fontSize = 12;
  } else if (viewport.width < 1024) { // tablet
    fontSize = 13;
  }
  
  return {
    fontSize,
    opacity: viewport.width < 640 ? 0.6 : 0.7
  };
}