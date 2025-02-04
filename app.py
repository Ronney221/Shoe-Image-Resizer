from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageChops
from flask_cors import CORS
from io import BytesIO
import base64
import numpy as np

app = Flask(__name__)
CORS(app)

def crop_shoe(image, tolerance=50):
    """
    Detects the shoe in the image by finding the tightest bounding box
    around all non-white pixels (with some tolerance) and crops to that box.
    
    Args:
      image (PIL.Image): Input image.
      tolerance (int): Tolerance for detecting non-white pixels. Pixels with all 
                       channels greater than (255 - tolerance) are considered white.
    
    Returns:
      PIL.Image: The cropped image.
    """
    # Convert image to numpy array
    np_img = np.array(image)

    # Create a boolean mask: consider pixels non-white if any channel is less than (255 - tolerance)
    # This allows a small tolerance for compression artifacts or noise.
    mask = (np_img < (255 - tolerance)).any(axis=-1)

    # If the mask is empty (i.e., the image is nearly all white), return the original image
    if not mask.any():
        return image

    # Find the bounding box of non-white pixels.
    coords = np.argwhere(mask)
    # coords are in (row, col) order = (y, x)
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1  # add 1 since slicing is non-inclusive

    # Crop and return the image using (left, upper, right, lower)
    return image.crop((x0, y0, x1, y1))

def scale_image(image, target_width=1024):
    """
    Scales the image horizontally to the target width while preserving the aspect ratio.
    
    Args:
      image (PIL.Image): The image to scale.
      target_width (int): The desired width of the image.
    
    Returns:
      PIL.Image: The scaled image.
    """
    orig_width, orig_height = image.size
    if orig_width == target_width:
        return image  # Already the desired width.
    new_height = int(orig_height * (target_width / orig_width))
    return image.resize((target_width, new_height), Image.LANCZOS)

def add_padding(image, pad_lr, pad_tb):
    """
    Add uniform white padding around an image.
    
    pad_lr: padding to add on the left and right sides.
    pad_tb: padding to add on the top and bottom.
    """
    orig_width, orig_height = image.size
    new_width = orig_width + 2 * pad_lr
    new_height = orig_height + 2 * pad_tb

    # Create a new white background image
    new_image = Image.new("RGB", (new_width, new_height), (255, 255, 255))
    # Paste the image onto the white background
    new_image.paste(image, (pad_lr, pad_tb))
    return new_image

def pil_image_to_base64(image):
    """
    Converts a PIL image to a base64-encoded PNG string.
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@app.route('/crop', methods=['POST'])
def crop_endpoint():
    """
    Debug endpoint: Crops the shoe from the image and returns the cropped image
    as a base64-encoded PNG. This is intended for debugging the cropping functionality.
    """
    files = request.files.getlist("images")
    processed_images = []

    for file in files:
        try:
            # Open the image in RGB mode.
            image = Image.open(file).convert("RGB")
            cropped = crop_shoe(image)

            img_str = pil_image_to_base64(cropped)
            processed_images.append({
                "filename": file.filename,
                "data": img_str
            })
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")
    return jsonify(processed_images)

@app.route('/process', methods=['POST'])
def process_images():
    """
    Main endpoint: Crops the shoe from the image, scales it to a width of 1024 pixels,
    and then adds uniform white padding. Returns the processed image as a base64-encoded PNG.
    """
    files = request.files.getlist("images")
    processed_images = []

    for file in files:
        try:
            # Open the image and convert it to "RGB" (if it has transparency, replace it with white)
            image = Image.open(file).convert("RGBA")  # Keep transparency info
            
            # Handle transparency: Convert alpha channel to a white background
            white_bg = Image.new("RGB", image.size, (255, 255, 255))  # White background
            image = Image.alpha_composite(white_bg.convert("RGBA"), image).convert("RGB")  

            # Crop the shoe
            cropped = crop_shoe(image)

            # Scale the cropped image to a width of 1024 pixels
            scaled = scale_image(cropped, target_width=1698)
            width, height = scaled.size

            # Then, add the uniform padding.
            yPadding = int((2048 - height) / 2)
            padded = add_padding(scaled, 175, yPadding)

            img_str = pil_image_to_base64(padded)
            processed_images.append({
                "filename": file.filename,
                "data": img_str
            })
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")

    return jsonify(processed_images)

if __name__ == '__main__':
    app.run(debug=True)
