#!/usr/bin/env python3
"""
創建專業的啟動畫面圖片

使用 PIL 創建一個包含 logo 和版本資訊的啟動畫面圖片。
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_splash_image(output_path='splash.png', width=640, height=400):
    """創建啟動畫面圖片
    
    Args:
        output_path: 輸出檔案路徑
        width: 圖片寬度
        height: 圖片高度
    """
    # 創建圖片（深色背景）
    img = Image.new('RGB', (width, height), color=(42, 45, 50))
    draw = ImageDraw.Draw(img)
    
    # 嘗試使用系統字型，否則使用預設字型
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        version_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        loading_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
    except IOError:
        # 如果找不到字型，使用預設字型
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        version_font = ImageFont.load_default()
        loading_font = ImageFont.load_default()
    
    # 繪製機器人圖示（使用簡單的幾何形狀）
    # 頭部
    draw.ellipse([270, 80, 370, 160], fill=(100, 150, 255), outline=(150, 180, 255), width=3)
    # 眼睛
    draw.ellipse([295, 105, 315, 125], fill=(255, 255, 255))
    draw.ellipse([355, 105, 375, 125], fill=(255, 255, 255))
    # 瞳孔
    draw.ellipse([302, 112, 308, 118], fill=(42, 45, 50))
    draw.ellipse([362, 112, 368, 118], fill=(42, 45, 50))
    # 嘴巴
    draw.arc([295, 130, 345, 150], 0, 180, fill=(255, 255, 255), width=3)
    # 天線
    draw.line([320, 80, 320, 60], fill=(100, 150, 255), width=3)
    draw.ellipse([315, 55, 325, 65], fill=(255, 100, 100))
    
    # 繪製標題
    title_text = "Robot Command Console"
    title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (width - title_width) // 2
    draw.text((title_x, 180), title_text, fill=(255, 255, 255), font=title_font)
    
    # 繪製副標題
    subtitle_text = "Tiny Edge Application"
    subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
    subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    subtitle_x = (width - subtitle_width) // 2
    draw.text((subtitle_x, 230), subtitle_text, fill=(200, 200, 200), font=subtitle_font)
    
    # 繪製版本資訊
    version_text = "Version 3.2.0-beta"
    version_bbox = draw.textbbox((0, 0), version_text, font=version_font)
    version_width = version_bbox[2] - version_bbox[0]
    version_x = (width - version_width) // 2
    draw.text((version_x, 270), version_text, fill=(150, 150, 150), font=version_font)
    
    # 繪製載入提示
    loading_text = "正在啟動服務..."
    loading_bbox = draw.textbbox((0, 0), loading_text, font=loading_font)
    loading_width = loading_bbox[2] - loading_bbox[0]
    loading_x = (width - loading_width) // 2
    draw.text((loading_x, 350), loading_text, fill=(100, 150, 255), font=loading_font)
    
    # 繪製進度條底部
    bar_y = 370
    bar_height = 6
    draw.rectangle([100, bar_y, 540, bar_y + bar_height], fill=(60, 60, 60))
    
    # 儲存圖片
    img.save(output_path, 'PNG')
    print(f"啟動畫面圖片已創建：{output_path}")


if __name__ == '__main__':
    # 取得腳本目錄
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'splash.png')
    
    create_splash_image(output_path)
