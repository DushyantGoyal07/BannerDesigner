import os
import io
import base64
import json
import warnings
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from google import genai

warnings.filterwarnings('ignore')
load_dotenv()

print(">>> bannerDesign loaded")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

ASSETS_DIR = "assets"
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.jpg")

def analyze_image(image_path):
    print(">>> analyze_image started")
    print(">>> image path:", image_path)

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    print(">>> image bytes loaded:", len(image_bytes))

    prompt =  f"""
You are a graphic design assistant. Analyze this image and find the best location to place a headline and description
without covering the main product. The text must be legible.

Always place:
- The headline in the top-left corner of the image.
- The description directly below the headline.

Return a JSON object with:

{{
    "text_placement": A dict with x and y coordinates for the headline,
    "text_color": "#FFFF00",
    "logo_placement": A dict with x and y for a small logo
}}

Base64 image: {image_b64}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-09-2025",
        contents=[prompt],
        config={
            "response_mime_type": "application/json"
        }
    )

    print(">>> Parsed layout:")
    return json.loads(response.text)

def composite_banner(base_image_path, headline, description, layout):
    print(">>> composite_banner started")
    print(">>> headline:", headline)
    print(">>> description:", description)
    # Load base image
    base = Image.open(base_image_path).convert("RGB")
    base = base.resize((900, 450))

    print(">>> base image loaded")

    # Load logo
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((100, 100))

    print(">>> logo loaded")

    # Draw object
    draw = ImageDraw.Draw(base)

    try:
        font_head = ImageFont.truetype("arial.ttf", 70)
        font_desc = ImageFont.truetype("arial.ttf", 50)
    except:
        font_head = ImageFont.load_default()
        font_desc = ImageFont.load_default()

    # Extract layout
    tx = layout["text_placement"]["x"]
    ty = layout["text_placement"]["y"]

    lx = layout["logo_placement"]["x"]
    ly = layout["logo_placement"]["y"]

    # color = layout["text_color"]
    color = "#FFFFFF"

    # Paste logo
    base.paste(logo, (lx, ly), logo)

    # Draw headline
    draw.text((tx, ty), headline, fill=color, font=font_head, stroke_width=2, stroke_fill="black")

    # Draw description below headline
    draw.text((tx, ty + 40), description, fill=color, font=font_desc, stroke_width=2, stroke_fill="black")

    # Save locally
    output_path = "final_banner.jpg"
    base.save(output_path, "JPEG")

    buffer = io.BytesIO()
    base.save(buffer, format="JPEG")

    banner_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return banner_base64, output_path

def critique_banner(banner_base64):
    image_part = genai.types.Part(banner_base64)

    prompt = f"""
Critique this banner. Is the headline text clearly legible and easy to read?
Answer with a simple JSON:

{{
    "is_legible": true/false,
    "critique": "explain in one sentence"
}}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-09-2025",
        contents=[
            prompt, image_part
        ],
        config={"response_mime_type": "application/json"}
    )
    return json.loads(response.text)