"""Media Watermark Service for AI-generated content."""

import logging
import io
import os
from typing import Optional, Dict, Any, Tuple, Union
from enum import Enum
from PIL import Image, ImageDraw, ImageFont
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logger = logging.getLogger(__name__)


class WatermarkPosition(Enum):
    """Watermark position options."""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    CENTER = "center"


class WatermarkService:
    """Service for adding watermarks to AI-generated media content."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.default_font_size = 16
        self.default_opacity = 128  # Semi-transparent
        self.margin = 10  # Pixels from edge
        
        # Try to load a system font, fallback to PIL default
        self.font_path = self._get_font_path()
    
    def _get_font_path(self) -> Optional[str]:
        """Get available system font path."""
        # Common font locations on different systems
        font_paths = [
            # Windows
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            # macOS
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Arial.ttf",
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                return font_path
        
        return None
    
    def _get_font(self, size: int = None) -> ImageFont.ImageFont:
        """Get font for watermark text."""
        font_size = size or self.default_font_size
        
        try:
            if self.font_path:
                return ImageFont.truetype(self.font_path, font_size)
            else:
                return ImageFont.load_default()
        except Exception as e:
            logger.warning(f"Failed to load font: {e}")
            return ImageFont.load_default()
    
    def _calculate_watermark_position(
        self,
        image_size: Tuple[int, int],
        text_size: Tuple[int, int],
        position: WatermarkPosition
    ) -> Tuple[int, int]:
        """Calculate watermark position coordinates."""
        img_width, img_height = image_size
        text_width, text_height = text_size
        
        positions = {
            WatermarkPosition.TOP_LEFT: (self.margin, self.margin),
            WatermarkPosition.TOP_RIGHT: (img_width - text_width - self.margin, self.margin),
            WatermarkPosition.BOTTOM_LEFT: (self.margin, img_height - text_height - self.margin),
            WatermarkPosition.BOTTOM_RIGHT: (
                img_width - text_width - self.margin,
                img_height - text_height - self.margin
            ),
            WatermarkPosition.CENTER: (
                (img_width - text_width) // 2,
                (img_height - text_height) // 2
            )
        }
        
        return positions.get(position, positions[WatermarkPosition.BOTTOM_RIGHT])
    
    def add_text_watermark(
        self,
        image: Union[Image.Image, str, bytes],
        watermark_text: str,
        position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
        opacity: int = None,
        font_size: int = None,
        color: Tuple[int, int, int] = (255, 255, 255),  # White
        background_color: Optional[Tuple[int, int, int, int]] = None
    ) -> Image.Image:
        """
        Add text watermark to an image.
        
        Args:
            image: PIL Image, file path, or bytes
            watermark_text: Text to add as watermark
            position: Position of the watermark
            opacity: Opacity (0-255, 128 is semi-transparent)
            font_size: Font size for watermark text
            color: Text color (RGB)
            background_color: Optional background color (RGBA)
            
        Returns:
            PIL Image with watermark
        """
        try:
            # Load image if needed
            if isinstance(image, str):
                img = Image.open(image)
            elif isinstance(image, bytes):
                img = Image.open(io.BytesIO(image))
            else:
                img = image.copy()
            
            # Convert to RGBA for transparency support
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create transparent overlay
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Get font
            font = self._get_font(font_size)
            
            # Get text bounding box
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
            x, y = self._calculate_watermark_position(
                img.size, (text_width, text_height), position
            )
            
            # Add background rectangle if specified
            if background_color:
                padding = 4
                bg_rect = [
                    x - padding,
                    y - padding,
                    x + text_width + padding,
                    y + text_height + padding
                ]
                draw.rectangle(bg_rect, fill=background_color)
            
            # Add text with specified opacity
            text_opacity = opacity or self.default_opacity
            text_color = (*color, text_opacity)
            draw.text((x, y), watermark_text, font=font, fill=text_color)
            
            # Composite overlay onto original image
            watermarked = Image.alpha_composite(img, overlay)
            
            # Convert back to RGB if original was RGB
            if watermarked.mode == 'RGBA' and image.mode == 'RGB':
                # Create white background
                rgb_img = Image.new('RGB', watermarked.size, (255, 255, 255))
                rgb_img.paste(watermarked, mask=watermarked.split()[3])
                watermarked = rgb_img
            
            return watermarked
            
        except Exception as e:
            logger.error(f"Failed to add text watermark: {e}", exc_info=True)
            raise
    
    def add_logo_watermark(
        self,
        image: Union[Image.Image, str, bytes],
        logo: Union[Image.Image, str, bytes],
        position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
        opacity: int = None,
        scale_factor: float = 0.1
    ) -> Image.Image:
        """
        Add logo watermark to an image.
        
        Args:
            image: PIL Image, file path, or bytes
            logo: Logo PIL Image, file path, or bytes
            position: Position of the watermark
            opacity: Opacity (0-255)
            scale_factor: Scale logo relative to image size (0.0-1.0)
            
        Returns:
            PIL Image with logo watermark
        """
        try:
            # Load image if needed
            if isinstance(image, str):
                img = Image.open(image)
            elif isinstance(image, bytes):
                img = Image.open(io.BytesIO(image))
            else:
                img = image.copy()
            
            # Load logo if needed
            if isinstance(logo, str):
                logo_img = Image.open(logo)
            elif isinstance(logo, bytes):
                logo_img = Image.open(io.BytesIO(logo))
            else:
                logo_img = logo.copy()
            
            # Convert images to RGBA
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            if logo_img.mode != 'RGBA':
                logo_img = logo_img.convert('RGBA')
            
            # Scale logo
            img_width, img_height = img.size
            max_logo_size = min(img_width, img_height) * scale_factor
            
            # Maintain aspect ratio
            logo_width, logo_height = logo_img.size
            if logo_width > logo_height:
                new_width = int(max_logo_size)
                new_height = int(max_logo_size * logo_height / logo_width)
            else:
                new_height = int(max_logo_size)
                new_width = int(max_logo_size * logo_width / logo_height)
            
            logo_img = logo_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Apply opacity to logo
            if opacity is not None:
                alpha = logo_img.split()[3]
                alpha = alpha.point(lambda p: int(p * (opacity / 255.0)))
                logo_img.putalpha(alpha)
            
            # Calculate position
            x, y = self._calculate_watermark_position(
                img.size, logo_img.size, position
            )
            
            # Paste logo onto image
            img.paste(logo_img, (x, y), logo_img)
            
            return img
            
        except Exception as e:
            logger.error(f"Failed to add logo watermark: {e}", exc_info=True)
            raise
    
    async def add_watermark_async(
        self,
        image_data: bytes,
        watermark_text: str,
        position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
        opacity: int = None,
        font_size: int = None,
        **kwargs
    ) -> bytes:
        """
        Add watermark to image asynchronously.
        
        Args:
            image_data: Image data as bytes
            watermark_text: Text to add as watermark
            position: Position of the watermark
            opacity: Opacity level
            font_size: Font size
            **kwargs: Additional arguments
            
        Returns:
            Watermarked image as bytes
        """
        loop = asyncio.get_event_loop()
        
        def sync_watermark():
            img = self.add_text_watermark(
                image_data, watermark_text, position, 
                opacity, font_size, **kwargs
            )
            # Convert to bytes
            output = io.BytesIO()
            img_format = kwargs.get('format', 'PNG')
            img.save(output, format=img_format)
            return output.getvalue()
        
        return await loop.run_in_executor(self.executor, sync_watermark)
    
    def batch_add_watermarks(
        self,
        images: list,
        watermark_text: str,
        position: WatermarkPosition = WatermarkPosition.BOTTOM_RIGHT,
        **kwargs
    ) -> list:
        """
        Add watermarks to multiple images in batch.
        
        Args:
            images: List of images (PIL Image, file paths, or bytes)
            watermark_text: Text to add as watermark
            position: Position of the watermark
            **kwargs: Additional arguments
            
        Returns:
            List of watermarked images
        """
        watermarked_images = []
        
        for image in images:
            try:
                watermarked = self.add_text_watermark(
                    image, watermark_text, position, **kwargs
                )
                watermarked_images.append(watermarked)
            except Exception as e:
                logger.error(f"Failed to watermark image: {e}")
                # Add original image if watermarking fails
                watermarked_images.append(image)
        
        return watermarked_images
    
    def get_optimal_watermark_config(
        self,
        image_size: Tuple[int, int],
        watermark_text: str
    ) -> Dict[str, Any]:
        """
        Get optimal watermark configuration for given image size.
        
        Args:
            image_size: Tuple of (width, height)
            watermark_text: Watermark text
            
        Returns:
            Dictionary with optimal configuration
        """
        width, height = image_size
        
        # Calculate optimal font size based on image dimensions
        min_dimension = min(width, height)
        
        if min_dimension < 200:
            font_size = 10
            opacity = 160
        elif min_dimension < 500:
            font_size = 12
            opacity = 140
        elif min_dimension < 1000:
            font_size = 16
            opacity = 128
        else:
            font_size = 20
            opacity = 120
        
        # Adjust for text length
        text_length = len(watermark_text)
        if text_length > 20:
            font_size = max(8, font_size - 2)
        elif text_length < 5:
            font_size += 2
        
        # Choose position based on aspect ratio
        aspect_ratio = width / height
        if aspect_ratio > 1.5:  # Wide image
            position = WatermarkPosition.BOTTOM_RIGHT
        elif aspect_ratio < 0.7:  # Tall image
            position = WatermarkPosition.BOTTOM_CENTER if hasattr(WatermarkPosition, 'BOTTOM_CENTER') else WatermarkPosition.BOTTOM_RIGHT
        else:
            position = WatermarkPosition.BOTTOM_RIGHT
        
        return {
            'font_size': font_size,
            'opacity': opacity,
            'position': position,
            'color': (255, 255, 255),  # White text
            'background_color': (0, 0, 0, 100)  # Semi-transparent black background
        }
    
    def create_ai_watermark_preset(self, language: str = 'en') -> Dict[str, Any]:
        """
        Create preset configuration for AI content watermarks.
        
        Args:
            language: Language code for watermark text
            
        Returns:
            Dictionary with preset configuration
        """
        # Default AI watermark texts
        ai_texts = {
            'en': 'AI Generated',
            'zh': 'AI生成',
            'ja': 'AI生成',
            'ko': 'AI 생성',
            'fr': 'Généré par IA',
            'de': 'KI-generiert',
            'es': 'Generado por IA',
            'pt': 'Gerado por IA',
            'ru': 'Создано ИИ'
        }
        
        watermark_text = ai_texts.get(language, ai_texts['en'])
        
        return {
            'watermark_text': watermark_text,
            'position': WatermarkPosition.BOTTOM_RIGHT,
            'opacity': 128,
            'font_size': 14,
            'color': (255, 255, 255),
            'background_color': (0, 0, 0, 120)
        }
    
    def validate_image_format(self, image_path: str) -> bool:
        """
        Validate if image format is supported for watermarking.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if format is supported
        """
        supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        
        try:
            file_ext = Path(image_path).suffix.lower()
            return file_ext in supported_formats
        except Exception:
            return False
    
    async def cleanup_resources(self):
        """Cleanup resources and shutdown executor."""
        try:
            self.executor.shutdown(wait=True)
            logger.info("Watermark service resources cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up watermark service: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)
        except Exception:
            pass