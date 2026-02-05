import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from bannerDesign import analyze_image, composite_banner, critique_banner

app = FastAPI()
app.mount("/static", StaticFiles(directory=".", html=True), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

ASSETS_DIR = "assets"

SESSION_STATE = {
    "state": "START",
    "product_name": None,
    "selected_image_path": None,
    "headline": None,
    "description": None
}

class ChatRequest(BaseModel):
    message: str

# def get_image():
#     if not os.path.exists(ASSETS_DIR):
#         return []

#     files = os.listdir(ASSETS_DIR)
#     return [f for f in files if f.lower().endswith((".jpg", ".jpeg"))]

def get_image(product_name=None):
    if not os.path.exists(ASSETS_DIR):
        return []
    
    files = os.listdir(ASSETS_DIR)
    images = [f for f in files if f.lower().endswith((".jpg", ".jpeg"))]

    if product_name:
        key = product_name.lower().replace(" ", "_")
        images = [img for img in images if key in img.lower()]

    return images

def reset_session():
    SESSION_STATE.update({
        "state": "START",
        "product_name": None,
        "selected_image_path": None,
        "headline": None,
        "description": None
    })

@app.post("/chat")
async def chat(request: ChatRequest):
    msg = request.message.strip()
    state = SESSION_STATE['state']

    if state == 'START':
        if not msg:
            return {"reply": "Please type the product name."}
        
        SESSION_STATE["product_name"] = msg
        SESSION_STATE["state"] = "ASK_IMAGE"
        print(f">>> Product name set: {msg}")

        images = get_image(product_name=msg)

        if not images:
            reset_session()
            return {"reply": "No matching products found."}

        SESSION_STATE["images"] = images

        payload = [
            {"id": i + 1, "url": f"/static/assets/{img}"}
            for i, img in enumerate(images)
        ]

        return {
            "reply": "Matching products:",
            "images": payload
        }

        # return {"reply": f"Searching {msg} products..."}
    
    if state == "ASK_IMAGE":
        # images = get_image()

        if msg.isdigit():
            idx = int(msg) - 1
            images = SESSION_STATE.get("images", [])

            if 0 <= idx < len(images):
                SESSION_STATE["selected_image_path"] = os.path.join(
                    ASSETS_DIR, images[idx]
                )

                SESSION_STATE["headline"] = None
                SESSION_STATE["description"] = None
                SESSION_STATE["state"] = "COLLECT_TEXT"
                return {"reply": "Image selected. Enter headline."}

            return {"reply": "Invalid selection. Try again."}

        images = get_image(product_name=SESSION_STATE['product_name'])

        if not images:
            reset_session()
            return {"reply": "No images found in assets folder."}
        
        SESSION_STATE["images"] = images

        payload = [
            {"id": i + 1, "url": f"/static/assets/{img}"}
            for i, img in enumerate(images)
        ]

        return {
            "reply": "Matching products:",
            "images": payload
        }

    if state == "COLLECT_TEXT":
        if SESSION_STATE["headline"] is None:
            SESSION_STATE["headline"] = msg
            print(f">>> Headline set: {msg}")
            return {"reply": "Got headline \nNow enter description."}

        if SESSION_STATE["description"] is None:
            SESSION_STATE["description"] = msg
            print(f">>> Description set: {msg}")
            try:
                layout = analyze_image(SESSION_STATE["selected_image_path"])
            except Exception as e:
                print("Image analysis failed:", e)
                return {"reply": "Failed to analyze image. Try another image."}

            try:
                banner_b64, saved_path = composite_banner(
                    SESSION_STATE["selected_image_path"],
                    SESSION_STATE["headline"],
                    SESSION_STATE["description"],
                    layout
                )
            except Exception as e:
                print("Banner generation failed:", e)
                return {"reply": "Failed to generate banner."}
            
            try:
                critique = critique_banner(banner_b64)
            except Exception as e:
                print("Banner critique failed:", e)
                critique = {"is_legible": True, "critique": ""}

            if critique.get("is_legible"):
                reset_session()
                return {
                    "reply": "Banner generated successfully.",
                    "banner_base64": banner_b64,
                    "saved_path": saved_path
                }
            else:
                return {"reply": f"I tried to create a banner, but the text was not legible. Let's try different text"}