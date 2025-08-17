"""
QR Code Generator with Logo/Watermark
=====================================
This script generates QR codes with custom logos or watermarks overlaid on them.
The logo is automatically resized and positioned in the center of the QR code.

Requirements:
pip install qrcode[pil] pillow

Author: Enhanced version for better functionality
"""

from PIL import Image, ImageDraw
import os
import sys
import qrcode
# Try to import qrcode once
try:
    from qrcode.constants import ERROR_CORRECT_H
    QRCODE_AVAILABLE = True
except ImportError:
    print("ERROR: qrcode library not found!")
    print("Please install it using: pip install qrcode[pil]")
    QRCODE_AVAILABLE = False


def check_dependencies():
    """
    Check if all required dependencies are installed.
    """
    missing_deps = []

    try:
        from PIL import Image
    except ImportError:
        missing_deps.append ("Pillow")

    if not QRCODE_AVAILABLE:
        missing_deps.append ("qrcode[pil]")

    if missing_deps:
        print ("Missing dependencies:")
        for dep in missing_deps:
            print (f"  - {dep}")
        print ("\nTo install missing dependencies, run:")
        print ("pip install " + " ".join (missing_deps))
        return False

    return True


def create_simple_qr_fallback(data, output_filename="simple_qr.png"):
    """
    Fallback function to create a simple QR code without logo if qrcode fails.
    """
    try:
        # Try using a different approach
        import qrcode

        qr = qrcode.make (data)
        qr.save (output_filename)
        print (f"Simple QR code (without logo) saved as: {output_filename}")
        return True

    except Exception as e:
        print (f"Error creating simple QR code: {e}")
        return False


# The main QR-with-logo function
def create_qr_with_logo(
    data,
    logo_path,
    output_filename="qr_with_logo.png",
    fill_color="black",
    back_color="white",
    logo_size_ratio=0.2,
    border_size=4,
):
    """
    Create a QR code with a logo/watermark in the center.

    Args:
        data (str): The data to encode in the QR code.
        logo_path (str): Path to the logo image file.
        output_filename (str): Output filename for the QR code.
        fill_color (str): QR code fill color (default: "black").
        back_color (str): QR code background color (default: "white").
        logo_size_ratio (float): Logo size as ratio of QR code size (default: 0.3).
        border_size (int): QR code border size (default: 4).

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Check if qrcode is available
        if not QRCODE_AVAILABLE:
            print("Error: qrcode library not available. Please install with: pip install qrcode[pil]")
            return False

        # Validate inputs
        if not data:
            print("Error: No data provided for QR code")
            return False

        if not os.path.exists(logo_path):
            print(f"Error: Logo file not found: {logo_path}")
            return False

        # Create QR code with error correction
        qr = qrcode.QRCode(
            version=None,  # Auto-select minimum version based on data
            error_correction=ERROR_CORRECT_H,  # High error correction for logo overlay
            box_size=10,
            border=border_size,
        )

        # Add data and optimize
        qr.add_data(data)
        qr.make(fit=True)

        # Clamp logo ratio to a conservative safe cap based on density (modules per side)
        modules_count = qr.modules_count
        safe_cap = 0.22  # for ERROR_CORRECT_H
        if modules_count >= 45:       # very dense
            safe_cap -= 0.03
        elif modules_count >= 33:     # moderately dense
            safe_cap -= 0.02
        if logo_size_ratio > safe_cap:
            print(f"Warning: logo_size_ratio {logo_size_ratio:.2f} too high; clamped to {safe_cap:.2f}")
            logo_size_ratio = safe_cap
        logo_size_ratio = max(0.12, logo_size_ratio)

        # Create QR code image
        qr_image = qr.make_image(fill_color=fill_color, back_color=back_color).convert('RGBA')

        # Load and process logo
        try:
            logo = Image.open(logo_path).convert('RGBA')
        except Exception as e:
            print(f"Error loading logo: {e}")
            return False

        # Calculate logo size (maintaining aspect ratio)
        qr_width, qr_height = qr_image.size
        logo_size = int(min(qr_width, qr_height) * logo_size_ratio)

        # Resize logo maintaining aspect ratio
        logo_aspect = logo.size[0] / logo.size[1]
        if logo_aspect > 1:
            # Logo is wider
            new_width = logo_size
            new_height = int(logo_size / logo_aspect)
        else:
            # Logo is taller or square
            new_height = logo_size
            new_width = int(logo_size * logo_aspect)

        logo = logo.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate position to center the logo
        logo_x = (qr_width - new_width) // 2
        logo_y = (qr_height - new_height) // 2

        # Create a white background for the logo area (optional, for better visibility)
        pad = max(2, int(0.02 * min(qr_width, qr_height)))
        logo_bg = Image.new('RGBA', (new_width + 2*pad, new_height + 2*pad), (255, 255, 255, 255))
        logo_bg_x = logo_x - pad
        logo_bg_y = logo_y - pad

        # Paste the white background first
        qr_image.paste(logo_bg, (logo_bg_x, logo_bg_y), logo_bg)

        # Paste the logo
        qr_image.paste(logo, (logo_x, logo_y), logo)

        # Convert back to RGB for saving
        final_image = qr_image.convert('RGB')

        # Save the image
        final_image.save(output_filename, 'PNG', optimize=True)
        print(f"QR code with logo saved successfully as: {output_filename}")

        # Display image info
        print(f"QR Code size: {qr_width}x{qr_height}")
        print(f"Logo size: {new_width}x{new_height}")
        print(f"Data encoded: {data}")

        return True

    except Exception as e:
        print(f"Error creating QR code: {e}")
        print("Trying fallback method...")

        # Try fallback method
        if create_simple_qr_fallback(data, output_filename.replace("_with_logo", "_simple")):
            print("Created simple QR code without logo as fallback")

        return False


def main():
    """
    Main function to run the QR code generator interactively.
    """
    print ("=== QR Code Generator with Logo ===")
    print ()

    # Check dependencies first
    if not check_dependencies ():
        return

    # Get user input
    data = input ("Enter the data for the QR code (URL, text, etc.): ").strip ()
    if not data:
        print ("No data provided. Exiting.")
        return

    logo_path = input ("Enter the path to your logo image: ").strip ()
    if not logo_path:
        logo_path = "logo.png"  # Default logo name
        print (f"Using default logo path: {logo_path}")

    output_name = input ("Enter output filename (default: qr_with_logo.png): ").strip ()
    if not output_name:
        output_name = "qr_with_logo.png"

    # Optional customization
    print ("\n=== Optional Customization ===")
    fill_color = input ("QR code color (default: black): ").strip () or "black"
    back_color = input ("Background color (default: white): ").strip () or "white"

    try:
        logo_ratio = input ("Logo size ratio 0.1-0.4 (default: 0.3): ").strip ()
        logo_ratio = float (logo_ratio) if logo_ratio else 0.3
        logo_ratio = max (0.1, min (0.4, logo_ratio))  # Clamp between 0.1 and 0.4
    except ValueError:
        logo_ratio = 0.3
        print ("Invalid ratio, using default: 0.3")

    # Generate QR code
    print (f"\nGenerating QR code...")
    success = create_qr_with_logo (
        data=data,
        logo_path=logo_path,
        output_filename=output_name,
        fill_color=fill_color,
        back_color=back_color,
        logo_size_ratio=logo_ratio
    )

    if success:
        print (f"\n✓ Success! Your QR code has been created.")
        try:
            # Try to open the image (works on most systems)
            if sys.platform.startswith ('darwin'):  # macOS
                os.system (f'open "{output_name}"')
            elif sys.platform.startswith ('win'):  # Windows
                os.system (f'start "{output_name}"')
            elif sys.platform.startswith ('linux'):  # Linux
                os.system (f'xdg-open "{output_name}"')
        except:
            print ("Could not auto-open the image, but it's saved successfully!")
    else:
        print ("✗ Failed to create QR code. Please check the error messages above.")


# Example usage function
def create_example_qr():
    """
    Create an example QR code - useful for testing
    """
    example_data = "https://www.python.org"

    # This assumes you have a logo file named 'logo.png' in the same directory
    if create_qr_with_logo (
            data=example_data,
            logo_path="logo.png",  # Make sure this file exists
            output_filename="example_qr.png",
            fill_color="darkblue",
            back_color="lightgray",
            logo_size_ratio=0.25
    ):
        print ("Example QR code created: example_qr.png")


if __name__ == "__main__":
    # Check if running with example flag
    if len (sys.argv) > 1 and sys.argv[1] == "--example":
        create_example_qr ()
    else:
        main ()