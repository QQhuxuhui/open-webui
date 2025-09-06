/**
 * 中国合规性组件导出
 * Chinese Compliance Components Export
 */

export { default as AIContentLabel } from './AIContentLabel.svelte';
export { default as AIImage } from './AIImage.svelte';
export { default as AIVideo } from './AIVideo.svelte';
export { default as PhoneAuth } from './PhoneAuth.svelte';

// 工具函数
export * from '$lib/utils/aiWatermark';

/**
 * 自动初始化AI内容标识系统
 * Auto-initialize AI content labeling system
 */
export function initAIContentLabeling(): void {
  // 监听DOM变化，自动为新添加的媒体内容添加标识
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            const element = node as Element;
            
            // 检查新添加的图片
            const images = element.querySelectorAll ? 
              element.querySelectorAll('img[data-ai-generated], img.ai-generated') :
              [];
            
            // 检查新添加的视频
            const videos = element.querySelectorAll ?
              element.querySelectorAll('video[data-ai-generated], video.ai-generated') :
              [];
            
            // 为检测到的AI媒体内容添加标识
            [...images, ...videos].forEach((media) => {
              if (!media.hasAttribute('data-ai-labeled')) {
                // 触发AI内容处理
                media.setAttribute('data-ai-labeled', 'true');
              }
            });
          }
        });
      }
    });
  });
  
  // 开始观察文档变化
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
  
  // 页面可见性变化时重新检测
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      // 延迟检测以确保内容已渲染
      setTimeout(() => {
        import('$lib/utils/aiWatermark').then(({ autoWatermarkAIContent }) => {
          autoWatermarkAIContent();
        });
      }, 1000);
    }
  });
}