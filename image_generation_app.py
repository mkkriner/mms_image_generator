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

st.sidebar.header("Text Configuration")
font_size = st.sidebar.slider("Font Size", 10, 200, 54)
text_x = st.sidebar.number_input("Text X Position", value=650, help="Horizontal position of the text")
text_y = st.sidebar.number_input("Text Y Position", value=1075, help="Vertical position of the text")
text_spacing = st.sidebar.slider("Line Spacing", 0, 50, 6)
text_align = st.sidebar.selectbox("Text Alignment", ["left", "center", "right"], index=1)

# Color picker
text_color = st.sidebar.color_picker("Text Color", "#2B4396")
text_color_rgb = tuple(int(text_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def fit_into(img, max_w, max_h):
    w, h = img.size
    scale = min(max_w / w, max_h / h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

def make_color_transparent(img, target_color, threshold=50):
    """Make a specific color transparent in an image"""
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    
    for item in datas:
        # Calculate Euclidean distance between pixel color and target color
        diff = sum((item[i] - target_color[i])**2 for i in range(3))**0.5
        
        # If color is within threshold, make transparent
        if diff < threshold:
            new_data.append((item[0], item[1], item[2], 0))  # alpha = 0
        else:
            new_data.append(item)
    
    img.putdata(new_data)
    return img

def generate_image(template, overlay, custom_text, font):
    canvas = template.copy()
    draw = ImageDraw.Draw(canvas)
    
    # Paste overlay
    if overlay:
        overlay_resized = fit_into(overlay, overlay_max_w, overlay_max_h)
        canvas.alpha_composite(overlay_resized, (overlay_x, overlay_y))
    
    # Draw text
    if custom_text:
        draw.multiline_text((text_x, text_y), custom_text, font=font, 
                          fill=text_color_rgb, spacing=text_spacing, align=text_align)
    
    return canvas

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
    tab1, tab2, tab3 = st.tabs(["Single Image Generator", "Batch Generator", "Background Remover"])
    
    with tab3:
        st.header("Background Remover")
        st.write("Remove a specific color from your overlay images to make them transparent.")
        
        if overlays_dict:
            bg_overlay_choice = st.selectbox("Select image to process:", 
                                           list(overlays_dict.keys()),
                                           key="bg_removal_select")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Settings")
                
                # Color picker for background color
                bg_color = st.color_picker("Select background color to remove", "#FFFFFF",
                                          help="Pick the color you want to make transparent")
                bg_color_rgb = tuple(int(bg_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                
                # Threshold slider
                threshold = st.slider("Threshold", 0, 255, 50,
                                    help="Higher values remove more similar colors. Lower values are more precise.")
                
                # Process button
                if st.button("🎨 Remove Background", type="primary", key="remove_bg_btn"):
                    original_img = overlays_dict[bg_overlay_choice]
                    processed_img = make_color_transparent(original_img.copy(), bg_color_rgb, threshold)
                    st.session_state['processed_overlay'] = processed_img
                    st.session_state['processed_overlay_name'] = bg_overlay_choice
            
            with col2:
                st.subheader("Preview")
                
                # Show before/after
                if 'processed_overlay' in st.session_state:
                    # Create a checkerboard background to show transparency
                    checker_size = 20
                    w, h = st.session_state['processed_overlay'].size
                    checker = Image.new('RGB', (w, h), (200, 200, 200))
                    draw = ImageDraw.Draw(checker)
                    for y in range(0, h, checker_size):
                        for x in range(0, w, checker_size):
                            if (x // checker_size + y // checker_size) % 2:
                                draw.rectangle([x, y, x + checker_size, y + checker_size], 
                                             fill=(255, 255, 255))
                    
                    # Composite the processed image over checker
                    checker.paste(st.session_state['processed_overlay'], (0, 0), 
                                st.session_state['processed_overlay'])
                    
                    st.image(checker, caption="Processed (transparent areas show checkered)", 
                           use_container_width=True)
                    
                    # Download button
                    buf = io.BytesIO()
                    st.session_state['processed_overlay'].save(buf, format='PNG')
                    buf.seek(0)
                    
                    st.download_button(
                        label="⬇️ Download Processed Image",
                        data=buf.getvalue(),
                        file_name=f"transparent_{st.session_state['processed_overlay_name']}",
                        mime="image/png",
                        key="download_processed"
                    )
                    
                    # Option to use in generator
                    if st.button("✅ Use This in Generator", key="use_processed"):
                        overlays_dict[f"processed_{bg_overlay_choice}"] = st.session_state['processed_overlay']
                        st.success(f"Added as 'processed_{bg_overlay_choice}' to overlay list!")
                else:
                    st.info("Click 'Remove Background' to see the result")
        else:
            st.info("Upload overlay images in the sidebar first to use the background remover.")
    
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
                preview_img = generate_image(template, selected_overlay, custom_text, font)
                st.session_state['preview_img'] = preview_img
        
        with col2:
            # Display preview
            if 'preview_img' in st.session_state:
                st.image(st.session_state['preview_img'], caption="Preview", use_container_width=True)
                
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
                    img = generate_image(template, overlay, custom_text, font)
                    
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
    
    ### Tips:
    - Use the configuration sliders to position text and overlays
    - Text supports multiple lines (use line breaks in the text area)
    - Overlay images are automatically resized to fit within max dimensions
    - In batch mode, overlay reference is optional
    """)
