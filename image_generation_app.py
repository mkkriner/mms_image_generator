#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 15 14:17:17 2025

@author: mikekriner
"""


import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import io
import zipfile

# Page config
st.set_page_config(page_title="Custom Image Generator", layout="wide")

st.title("🎨 Custom Image Generator")
st.write("Generate custom images by combining a template with overlays and text.")

# File uploaders
st.sidebar.header("Upload Files")
template_file = st.sidebar.file_uploader("Upload Template Image", type=['png', 'jpg', 'jpeg'])
font_file = st.sidebar.file_uploader("Upload Font File (.ttf)", type=['ttf'])
overlay_files = st.sidebar.file_uploader("Upload Overlay Images", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

# Configuration inputs
st.sidebar.header("Overlay Configuration")
overlay_x = st.sidebar.number_input("Overlay X Position", value=400, help="Horizontal position of the overlay")
overlay_y = st.sidebar.number_input("Overlay Y Position", value=1060, help="Vertical position of the overlay")
overlay_max_w = st.sidebar.number_input("Overlay Max Width", value=225, help="Maximum width the overlay can be")
overlay_max_h = st.sidebar.number_input("Overlay Max Height", value=175, help="Maximum height the overlay can be")

# Whitespace options
st.sidebar.header("Whitespace Options")
trim_whitespace = st.sidebar.checkbox("Trim whitespace from overlays", value=True, 
                                      help="Remove transparent borders from overlay images")
center_overlay = st.sidebar.checkbox("Center overlay in bounding box", value=True,
                                     help="Center the overlay within the specified dimensions")
show_whitespace_analysis = st.sidebar.checkbox("Show whitespace analysis", value=False,
                                               help="Display whitespace percentage for debugging")

st.sidebar.header("Text Configuration")
font_size = st.sidebar.slider("Font Size", 10, 200, 54)
text_x = st.sidebar.number_input("Text X Position", value=650, help="Horizontal position of the text")
text_y = st.sidebar.number_input("Text Y Position", value=1075, help="Vertical position of the text")
text_spacing = st.sidebar.slider("Line Spacing", 0, 50, 6)
text_align = st.sidebar.selectbox("Text Alignment", ["left", "center", "right"], index=1)

# Color picker
text_color = st.sidebar.color_picker("Text Color", "#2B4396")
text_color_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def get_bounding_box(img):
    """Find the bounding box of non-transparent pixels in an RGBA image"""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    # Get alpha channel
    alpha = img.split()[-1]
    bbox = alpha.getbbox()  # returns (left, top, right, bottom) or None
    return bbox

def trim_whitespace_from_image(img):
    """Remove transparent/whitespace borders from image"""
    bbox = get_bounding_box(img)
    if bbox:
        return img.crop(bbox)
    return img

def analyze_whitespace_in_region(img, x, y, w, h):
    """
    Analyze how much whitespace is in a specific region.
    Returns percentage of transparent/white pixels (0-100)
    """
    # Ensure coordinates are within image bounds
    img_w, img_h = img.size
    x = max(0, min(x, img_w))
    y = max(0, min(y, img_h))
    w = min(w, img_w - x)
    h = min(h, img_h - y)
    
    if w <= 0 or h <= 0:
        return 0
    
    region = img.crop((x, y, x + w, y + h))
    
    if region.mode != 'RGBA':
        region = region.convert('RGBA')
    
    pixels = region.getdata()
    transparent_count = 0
    total_pixels = len(pixels)
    
    if total_pixels == 0:
        return 0
    
    for pixel in pixels:
        # Check if pixel is transparent (alpha < 10) or white-ish
        if len(pixel) == 4:  # RGBA
            r, g, b, a = pixel
            if a < 10 or (r > 240 and g > 240 and b > 240):
                transparent_count += 1
        elif len(pixel) == 3:  # RGB
            r, g, b = pixel
            if r > 240 and g > 240 and b > 240:
                transparent_count += 1
    
    return (transparent_count / total_pixels) * 100

def center_in_box(img, box_w, box_h):
    """Calculate offset to center image within a box"""
    img_w, img_h = img.size
    offset_x = (box_w - img_w) // 2
    offset_y = (box_h - img_h) // 2
    return offset_x, offset_y

def fit_into(img, max_w, max_h):
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

def generate_image(template, overlay, custom_text, font):
    canvas = template.copy()
    draw = ImageDraw.Draw(canvas)
    
    whitespace_info = None
    
    # Paste overlay
    if overlay:
        processed_overlay = overlay.copy()
        
        # Trim whitespace if enabled
        if trim_whitespace:
            processed_overlay = trim_whitespace_from_image(processed_overlay)
        
        # Resize to fit
        overlay_resized = fit_into(processed_overlay, overlay_max_w, overlay_max_h)
        
        # Calculate position (centered or not)
        if center_overlay:
            offset_x, offset_y = center_in_box(overlay_resized, overlay_max_w, overlay_max_h)
            paste_x = overlay_x + offset_x
            paste_y = overlay_y + offset_y
        else:
            paste_x = overlay_x
            paste_y = overlay_y
        
        canvas.alpha_composite(overlay_resized, (paste_x, paste_y))
        
        # Analyze whitespace if requested
        if show_whitespace_analysis:
            whitespace_pct = analyze_whitespace_in_region(
                canvas, overlay_x, overlay_y, overlay_max_w, overlay_max_h
            )
            whitespace_info = {
                'whitespace_pct': whitespace_pct,
                'original_size': overlay.size,
                'trimmed_size': processed_overlay.size if trim_whitespace else overlay.size,
                'final_size': overlay_resized.size
            }
    
    # Draw text
    if custom_text:
        draw.multiline_text((text_x, text_y), custom_text, font=font, 
                          fill=text_color_rgb, spacing=text_spacing, align=text_align)
    
    return canvas, whitespace_info

# Main app logic
if template_file and font_file:
    # Load template
    template = Image.open(template_file).convert("RGBA")
    
    # Load font
    font = ImageFont.truetype(font_file, font_size)
    
    # Load overlay images
    overlays_dict = {}
    if overlay_files:
        for overlay_file in overlay_files:
            name = overlay_file.name
            overlays_dict[name] = Image.open(overlay_file).convert("RGBA")
        st.success(f"✅ Loaded template, font, and {len(overlays_dict)} overlay images")
    else:
        st.success(f"✅ Loaded template and font")
    
    # Tab interface
    tab1, tab2 = st.tabs(["Single Image Generator", "Batch Generator"])
    
    with tab1:
        st.header("Single Image Generator")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Text input
            custom_text = st.text_area(
                "Enter your text (use line breaks for multiple lines):",
                value="Your text here\ngoes on multiple lines!",
                height=150
            )
            
            # Overlay selection
            selected_overlay = None
            if overlays_dict:
                overlay_choice = st.selectbox("Select overlay image (optional):", 
                                             ["None"] + list(overlays_dict.keys()))
                if overlay_choice != "None":
                    selected_overlay = overlays_dict[overlay_choice]
            
            # Generate button
            if st.button("🎨 Generate Preview", type="primary"):
                preview_img, ws_info = generate_image(template, selected_overlay, custom_text, font)
                st.session_state['preview_img'] = preview_img
                st.session_state['ws_info'] = ws_info
        
        with col2:
            # Display preview
            if 'preview_img' in st.session_state:
                st.image(st.session_state['preview_img'], caption="Preview", use_container_width=True)
                
                # Display whitespace analysis
                if show_whitespace_analysis and 'ws_info' in st.session_state and st.session_state['ws_info']:
                    ws_info = st.session_state['ws_info']
                    st.info(f"""
                    **Whitespace Analysis:**
                    - Whitespace in overlay area: {ws_info['whitespace_pct']:.1f}%
                    - Original size: {ws_info['original_size']}
                    - Trimmed size: {ws_info['trimmed_size']}
                    - Final size: {ws_info['final_size']}
                    """)
                
                # Download button
                buf = io.BytesIO()
                st.session_state['preview_img'].save(buf, format='PNG')
                buf.seek(0)
                
                st.download_button(
                    label="⬇️ Download Image",
                    data=buf.getvalue(),
                    file_name="generated_image.png",
                    mime="image/png"
                )
    
    with tab2:
        st.header("Batch Generator")
        st.write("Generate multiple images at once with different text/overlay combinations.")
        
        # Input area for batch data
        st.subheader("Enter Image Data")
        st.write("Format: `filename | text line 1 | text line 2 | ... | overlay_image_name (optional)`")
        
        batch_input = st.text_area(
            "Enter one image per line:",
            value="""image1 | First line | Second line | overlay1.png
image2 | Different text | Another line
image3 | Just one line | overlay2.png""",
            height=200,
            help="Each line creates one image. Separate values with | symbol."
        )
        
        if st.button("🚀 Generate Batch Images", type="primary"):
            lines = [line.strip() for line in batch_input.split('\n') if line.strip()]
            
            if not lines:
                st.error("Please enter at least one line of data")
            else:
                progress_bar = st.progress(0)
                generated_images = {}
                
                for idx, line in enumerate(lines):
                    parts = [p.strip() for p in line.split('|')]
                    
                    if len(parts) < 2:
                        st.warning(f"Skipping line {idx+1}: needs at least filename and one text part")
                        continue
                    
                    filename = parts[0]
                    
                    # Check if last part is an overlay reference
                    overlay = None
                    if parts[-1] in overlays_dict:
                        overlay = overlays_dict[parts[-1]]
                        text_parts = parts[1:-1]
                    else:
                        text_parts = parts[1:]
                    
                    custom_text = '\n'.join(text_parts)
                    
                    # Generate image
                    img, _ = generate_image(template, overlay, custom_text, font)
                    
                    # Convert to bytes
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    buf.seek(0)
                    generated_images[f"{filename}.png"] = buf.getvalue()
                    
                    progress_bar.progress((idx + 1) / len(lines))
                
                st.success(f"✅ Generated {len(generated_images)} images!")
                
                # Create ZIP file
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, img_bytes in generated_images.items():
                        zip_file.writestr(filename, img_bytes)
                
                zip_buf.seek(0)
                
                # Download ZIP
                st.download_button(
                    label="⬇️ Download All as ZIP",
                    data=zip_buf.getvalue(),
                    file_name="generated_images.zip",
                    mime="application/zip"
                )
                
                # Individual downloads
                with st.expander("Download Individual Images"):
                    cols = st.columns(4)
                    for idx, (filename, img_bytes) in enumerate(generated_images.items()):
                        col = cols[idx % 4]
                        with col:
                            st.download_button(
                                label=filename,
                                data=img_bytes,
                                file_name=filename,
                                mime="image/png",
                                key=f"download_{idx}"
                            )

else:
    st.info("👈 Please upload a template image and font file in the sidebar to get started.")
    
    st.markdown("""
    ### How to Use:
    
    **Single Image Mode:**
    1. Upload a template image and font file
    2. Optionally upload overlay images (logos, icons, shapes, etc.)
    3. Enter your custom text
    4. Select an overlay (optional)
    5. Click "Generate Preview"
    6. Download your image
    
    **Batch Mode:**
    1. Upload template, font, and overlays
    2. Enter image data in the format: `filename | text line 1 | text line 2 | overlay_name`
    3. Generate all images at once
    4. Download as a ZIP file
    
    ### Whitespace Features:
    - **Trim whitespace**: Automatically removes transparent borders from overlay images
    - **Center overlay**: Centers the trimmed overlay within the bounding box
    - **Whitespace analysis**: Shows statistics about overlay positioning (for debugging)
    
    ### Tips:
    - Use the configuration sliders to position text and overlays
    - Text supports multiple lines (use line breaks in the text area)
    - Overlay images are automatically resized to fit within max dimensions
    - In batch mode, overlay reference is optional
    - Enable "Trim whitespace" for consistent positioning of irregularly-shaped overlays
    """)
