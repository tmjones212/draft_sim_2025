"""
Create a simple icon for the Mock Draft Simulator
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_app_icon():
    """Create a simple icon with 'MDS' text"""
    # Create a 256x256 image with dark background
    size = 256
    img = Image.new('RGBA', (size, size), color=(28, 35, 43, 255))  # Dark theme color
    draw = ImageDraw.Draw(img)
    
    # Draw a rounded rectangle border
    border_color = (139, 122, 184, 255)  # Purple accent color
    border_width = 8
    draw.rounded_rectangle(
        [(border_width, border_width), (size-border_width, size-border_width)],
        radius=20,
        outline=border_color,
        width=border_width
    )
    
    # Add "MDS" text
    text = "MDS"
    text_color = (255, 255, 255, 255)  # White text
    
    # Try to use a large font
    try:
        font = ImageFont.truetype("arial.ttf", 72)
    except:
        # Fallback to default font if arial not found
        font = ImageFont.load_default()
        # Scale up the image if using default font
        text = "MDS\n2025"
    
    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - 10  # Slight offset up
    
    draw.text((x, y), text, fill=text_color, font=font)
    
    # Add "2025" below if not already included
    if "2025" not in text:
        year_text = "2025"
        try:
            year_font = ImageFont.truetype("arial.ttf", 36)
        except:
            year_font = font
        
        bbox = draw.textbbox((0, 0), year_text, font=year_font)
        year_width = bbox[2] - bbox[0]
        year_x = (size - year_width) // 2
        year_y = y + text_height + 10
        
        draw.text((year_x, year_y), year_text, fill=(139, 122, 184, 255), font=year_font)
    
    # Save as ICO file with multiple resolutions
    os.makedirs('assets', exist_ok=True)
    
    # Create different sizes for ICO file
    icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    for icon_size in icon_sizes:
        resized = img.resize(icon_size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save as ICO
    icons[5].save('assets/app_icon.ico', format='ICO', sizes=icon_sizes)
    print("Icon created: assets/app_icon.ico")
    
    # Also save as PNG for other uses
    img.save('assets/app_icon.png')
    print("PNG version saved: assets/app_icon.png")

if __name__ == "__main__":
    create_app_icon()