import streamlit as st
import zipfile
import io
import os
import tempfile
from PIL import Image
from algorithms.spr_png_to_gbstudio_anim import process, load_gbsres_file
import json


def scale_image_for_display(image, max_width=400, zoom_level=1):
    """Scale an image using nearest neighbor interpolation for pixel art."""
    # Apply zoom level first
    if zoom_level > 1:
        zoomed_width = image.width * zoom_level
        zoomed_height = image.height * zoom_level
        image = image.resize((zoomed_width, zoomed_height), Image.NEAREST)
    
    # Then apply max width constraint if needed
    if image.width <= max_width:
        return image
    
    # Calculate scale factor
    scale_factor = max_width / image.width
    
    # Calculate new dimensions
    new_width = int(image.width * scale_factor)
    new_height = int(image.height * scale_factor)
    
    # Resize using nearest neighbor
    scaled_image = image.resize((new_width, new_height), Image.NEAREST)
    
    return scaled_image


def create_pixel_perfect_display(image, max_width=400, zoom_level=1):
    """Create a pixel-perfect display by scaling and saving to temp file with CSS."""
    # Scale the image using nearest neighbor
    scaled_image = scale_image_for_display(image, max_width, zoom_level)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    scaled_image.save(temp_file.name, format='PNG')
    temp_file.close()
    
    return temp_file.name, scaled_image.size


def display_pixel_art(image, caption, max_width=400, zoom_level=1):
    """Display pixel art with proper scaling and CSS to prevent blurring."""
    temp_file_path, scaled_size = create_pixel_perfect_display(image, max_width, zoom_level)
    
    # Read the image data as base64
    import base64
    with open(temp_file_path, "rb") as img_file:
        img_data = base64.b64encode(img_file.read()).decode()
    
    # Create HTML with proper image rendering
    html = f"""
    <div style="text-align: center;">
        <img src="data:image/png;base64,{img_data}" 
             style="image-rendering: pixelated; 
                    image-rendering: -moz-crisp-edges; 
                    image-rendering: crisp-edges; 
                    image-rendering: -webkit-optimize-contrast; 
                    image-rendering: optimize-contrast; 
                    image-rendering: -ms-interpolation-mode: nearest-neighbor;
                    max-width: 100%; 
                    height: auto;"
             alt="{caption}">
        <p style="font-size: 0.8em; color: #666; margin-top: 5px;">{caption}</p>
    </div>
    """
    
    # Display the HTML
    st.markdown(html, unsafe_allow_html=True)
    
    # Clean up the temporary file
    try:
        os.unlink(temp_file_path)
    except:
        pass  # Ignore cleanup errors
    
    return scaled_size


def main():
    st.set_page_config(
        page_title="GB Studio Sprite Animator",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 GB Studio Sprite Animator")
    st.markdown("Convert PNG sprites to GB Studio animation format")
    
    # Sidebar for parameters
    with st.sidebar:
        st.header("⚙️ Parameters")
        
        # Basic parameters
        st.subheader("Basic Settings")
        filename = st.text_input("Filename", value="sprite", help="Base name for output files")
        enable_rgb = st.checkbox("Enable RGB Processing", value=True, help="Process RGB color layers")
        enable_processing = st.checkbox("Enable Processing", value=True, help="Generate JSON metadata")
        
        st.subheader("Tile Settings")
        tile_width = st.number_input("Tile Width", min_value=1, max_value=32, value=8, help="Width of each tile in pixels")
        tile_height = st.number_input("Tile Height", min_value=1, max_value=32, value=16, help="Height of each tile in pixels")
        hor_tiles = st.number_input("Horizontal Tiles per Frame", min_value=1, max_value=8, value=1, help="Number of tiles horizontally per frame")
        vert_tiles = st.number_input("Vertical Tiles per Frame", min_value=1, max_value=8, value=1, help="Number of tiles vertically per frame")
        
        st.subheader("Animation Settings")
        st.write("Add state types (you can add the same type multiple times):")
        
        # Container for state types
        if 'state_types' not in st.session_state:
            st.session_state.state_types = ["fixed"]
        
        col1, col2 = st.columns([3, 1])
        with col1:
            new_state = st.selectbox(
                "Add state type:",
                options=["fixed", "multi", "multi#f", "multi_movement", "multi_movement#f"],
                key="new_state_select"
            )
        with col2:
            if st.button("➕ Add", key="add_state"):
                st.session_state.state_types.append(new_state)
        
        # Display current state types
        if st.session_state.state_types:
            st.write("Current state types:")
            for i, state in enumerate(st.session_state.state_types):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{i+1}. {state}")
                with col2:
                    if st.button("🗑️", key=f"remove_{i}"):
                        st.session_state.state_types.pop(i)
                        st.rerun()
        
        state_types = st.session_state.state_types
        
        st.subheader("Layer Settings")
        layer_palettes = st.text_input("Layer Palettes", value="1", help="Comma-separated palette indices (e.g., '1,2,3')")
        
        st.subheader("Display Settings")
        zoom_level = st.selectbox(
            "Zoom Level",
            options=[1, 2, 4, 8, 16],
            index=1,  # Default to x2
            format_func=lambda x: f"x{x}",
            help="Zoom level for displaying images"
        )
        
        st.subheader("Advanced")
        checksum = st.text_input("Checksum", value="TBD", help="File checksum (leave as TBD for auto)")
    
    # Main content area
    st.header("📁 Upload & Process Sprite")
    
    # File upload section
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🖼️ PNG Sprite")
        uploaded_png = st.file_uploader(
            "Choose a PNG file",
            type=['png'],
            help="Upload a PNG sprite image to process",
            key="png_uploader"
        )
    
    with col2:
        st.subheader("📄 GBSRES Template")
        uploaded_gbsres = st.file_uploader(
            "Choose a GBSRES file (optional)",
            type=['gbsres'],
            help="Upload a GBSRES file to use as template (preserves ID and metadata)",
            key="gbsres_uploader"
        )
    
    if uploaded_png is not None:
        # Display the uploaded image
        image = Image.open(uploaded_png)
        
        # Load GBSRES data if provided
        gbsres_data = None
        if uploaded_gbsres is not None:
            gbsres_data = load_gbsres_file(uploaded_gbsres)
            if gbsres_data:
                st.success("✅ GBSRES template loaded successfully!")
            else:
                st.warning("⚠️ Could not load GBSRES file. Processing without template.")
        
        # Processing controls and results above images
        st.subheader("🔧 Processing & Results")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if st.button("🚀 Process Sprite", type="primary", use_container_width=True):
                with st.spinner("Processing sprite..."):
                    try:
                        # Prepare parameters
                        params = f"fname={filename} processing={enable_processing} rgb={'y' if enable_rgb else 'n'} twidth={tile_width} theight={tile_height} htiles={hor_tiles} vtiles={vert_tiles} states={','.join(state_types)} palettes={layer_palettes} chksum={checksum}"
                        
                        # Process the image with optional GBSRES template
                        processed_image = process(image, gbsres_data, params)
                        
                        # Store processed image in session state
                        st.session_state.processed_image = processed_image
                        st.session_state.zip_buffer = create_zip_file(processed_image, filename, enable_rgb)
                        st.session_state.processing_success = True
                        
                        st.rerun()  # Refresh to show the processed image
                        
                    except Exception as e:
                        st.error(f"❌ Error processing image: {str(e)}")
                        st.session_state.processing_success = False
        
        with col2:
            if 'processed_image' in st.session_state and st.session_state.get('processing_success', False):
                st.success("✅ Processing completed!")
        
        with col3:
            if 'zip_buffer' in st.session_state and st.session_state.get('processing_success', False):
                st.download_button(
                    label="📦 Download ZIP",
                    data=st.session_state.zip_buffer.getvalue(),
                    file_name=f"{filename}_gbstudio.zip",
                    mime="application/zip",
                    use_container_width=True
                )
        
        # Images side by side
        st.subheader("🖼️ Image Comparison")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📤 Input Image**")
            scaled_size = display_pixel_art(image, f"Original Image (x{zoom_level})", zoom_level=zoom_level)
            st.info(f"Original size: {image.size[0]}x{image.size[1]} pixels | Display zoom: x{zoom_level}")
        
        with col2:
            st.markdown("**📤 Output Image**")
            if 'processed_image' in st.session_state:
                processed_image = st.session_state.processed_image
                scaled_size = display_pixel_art(processed_image, f"Processed Sprite (x{zoom_level})", zoom_level=zoom_level)
                st.info(f"Processed size: {processed_image.size[0]}x{processed_image.size[1]} pixels | Display zoom: x{zoom_level}")
            else:
                st.info("👆 Click 'Process Sprite' to see the output image here")
        
        # GBSRES metadata display (collapsed by default)
        if 'processed_image' in st.session_state and st.session_state.get('processing_success', False):
            processed_image = st.session_state.processed_image
            
            with st.expander("📄 Generated GBSRES Metadata", expanded=False):
                if hasattr(processed_image, 'extra_data') and processed_image.extra_data:
                    if isinstance(processed_image.extra_data, str):
                        st.info(f"Processing info: {processed_image.extra_data}")
                    else:
                        st.json(processed_image.extra_data)
    
    else:
        st.info("👆 Please upload a PNG file to begin processing")
    
    # Instructions
    with st.expander("📖 Instructions"):
        st.markdown("""
        ### How to use this tool:
        
        1. **Upload a PNG file** - Your sprite image (required)
        2. **Upload a GBSRES file** - Template file to preserve ID and metadata (optional)
        3. **Configure parameters** in the sidebar:
           - **Basic Settings**: Set filename and processing options
           - **Tile Settings**: Define tile dimensions and frame layout
           - **Animation Settings**: Add multiple state types (same type can be added multiple times)
           - **Layer Settings**: Set palette indices for layers
        4. **Click Process Sprite** to generate the GB Studio files
        5. **Download the ZIP file** containing:
           - `/assets/sprites/` - Processed PNG file
           - `/project/sprites/` - GB Studio resource file (.gbsres)
        
        ### File Uploads:
        
        - **PNG File**: Your sprite image to process (required)
        - **GBSRES File**: Template file to use as starting point (optional)
          - Preserves important metadata like ID, name, symbol
          - If not provided, generates new metadata
          - Useful for maintaining consistency across sprite variations
        
        ### Parameter Explanations:
        
        - **Tile Width/Height**: Size of individual tiles in pixels
        - **Tiles per Frame**: How many tiles make up one animation frame
        - **State Types**: Different animation patterns (fixed, multi, etc.) - you can add the same type multiple times
        - **Layer Palettes**: Color palette indices for different layers
        - **RGB Processing**: Converts RGB images to 3-color GB Studio format (enabled by default)
        """)


def create_zip_file(processed_image, filename, enable_rgb):
    """Create a ZIP file with the proper folder structure."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add the processed PNG to assets/sprites/
        png_buffer = io.BytesIO()
        processed_image.save(png_buffer, format='PNG')
        png_buffer.seek(0)
        zip_file.writestr(f"assets/sprites/{filename}.png", png_buffer.getvalue())
        
        # Add the JSON metadata to project/sprites/
        if hasattr(processed_image, 'extra_data') and processed_image.extra_data:
            if isinstance(processed_image.extra_data, dict):
                json_buffer = io.BytesIO()
                json_str = json.dumps(processed_image.extra_data, indent=2)
                json_buffer.write(json_str.encode('utf-8'))
                json_buffer.seek(0)
                zip_file.writestr(f"project/sprites/{filename}.gbsres", json_buffer.getvalue())
    
    zip_buffer.seek(0)
    return zip_buffer


if __name__ == "__main__":
    main()
