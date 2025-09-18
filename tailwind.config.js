import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				},
				// 现代化UI升级 - 主品牌色系
				primary: {
					50: '#eff6ff',
					100: '#dbeafe',
					200: '#bfdbfe',
					300: '#93c5fd',
					400: '#60a5fa',
					500: '#3b82f6',
					600: '#2563eb',
					700: '#1d4ed8',
					800: '#1e40af',
					900: '#1e3a8a',
					950: '#172554'
				},
				// 辅助色彩
				accent: {
					emerald: '#10b981',
					purple: '#8b5cf6',
					amber: '#f59e0b'
				},
				// 玻璃态效果
				glass: {
					light: 'rgba(255, 255, 255, 0.1)',
					dark: 'rgba(0, 0, 0, 0.1)',
					border: 'rgba(255, 255, 255, 0.2)'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			},
			// 现代化UI升级 - 扩展设计token
			backdropBlur: {
				xs: '2px'
			},
			animation: {
				'fade-in': 'fadeIn 0.2s ease-out',
				'slide-up': 'slideUp 0.3s ease-out',
				'slide-in-left': 'slideInLeft 0.3s ease-out',
				'pulse-slow': 'pulse 2s infinite',
				'gradient-shift': 'gradientShift 20s ease infinite',
				'float': 'float 6s ease-in-out infinite',
				'message-slide-in': 'messageSlideIn 0.3s ease-out',
				'bounce-subtle': 'bounceSubtle 1.4s infinite ease-in-out'
			},
			keyframes: {
				fadeIn: {
					from: { opacity: '0' },
					to: { opacity: '1' }
				},
				slideUp: {
					from: { opacity: '0', transform: 'translateY(20px)' },
					to: { opacity: '1', transform: 'translateY(0)' }
				},
				slideInLeft: {
					from: { transform: 'translateX(-100%)' },
					to: { transform: 'translateX(0)' }
				},
				gradientShift: {
					'0%, 100%': { transform: 'rotate(0deg) scale(1)' },
					'50%': { transform: 'rotate(180deg) scale(1.1)' }
				},
				float: {
					'0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
					'50%': { transform: 'translateY(-20px) rotate(180deg)' }
				},
				messageSlideIn: {
					from: { opacity: '0', transform: 'translateY(20px)' },
					to: { opacity: '1', transform: 'translateY(0)' }
				},
				bounceSubtle: {
					'0%, 80%, 100%': { transform: 'scale(0.8)', opacity: '0.5' },
					'40%': { transform: 'scale(1.2)', opacity: '1' }
				}
			},
			boxShadow: {
				'glass': '0 25px 50px rgba(0, 0, 0, 0.1)',
				'primary': '0 10px 25px rgba(59, 130, 246, 0.3)',
				'primary-lg': '0 15px 35px rgba(59, 130, 246, 0.4)'
			}
		}
	},
	plugins: [typography, containerQuries]
};
