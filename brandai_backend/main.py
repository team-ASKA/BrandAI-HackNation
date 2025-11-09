import os
import json
import base64
import io
from datetime import datetime
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel

# Google Cloud Imports
import vertexai
from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
from google.cloud import vision

# Load environment variables from .env file
load_dotenv()

# --- Environment and GCP Configuration ---
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")

# --- FastAPI App Setup ---
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Vertex AI and load brand kits on startup."""
    if not GCP_PROJECT_ID or not GCP_LOCATION:
        print("Warning: GCP_PROJECT_ID or GCP_LOCATION not set. Google Cloud APIs will fail.")
    else:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        print(f"Vertex AI initialized for project '{GCP_PROJECT_ID}' in '{GCP_LOCATION}'")
    
    load_brand_kits()
    yield

app = FastAPI(
    title="BrandAI - Google Cloud Edition",
    description="AI-powered ad critique and improvement using Google Cloud's Vision, Gemini, and Imagen APIs.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegenerationRequest(BaseModel):
    refinement_plan: str

# --- Static File and Brand Kit Configuration ---
BRAND_KITS_PATH = Path(__file__).parent / "brand_kits" / "database.json"
STATIC_DIR = Path(__file__).parent / "static"
brand_kits = {}

def load_brand_kits():
    """Load brand kits from JSON file into memory."""
    global brand_kits
    try:
        with open(BRAND_KITS_PATH, "r") as f:
            brand_kits = json.load(f)
        print(f"Loaded {len(brand_kits)} brand kits: {list(brand_kits.keys())}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load brand kits from {BRAND_KITS_PATH}. Error: {e}")
        brand_kits = {}

# === CORE API FUNCTIONS ===

def analyze_image_with_vision_api(image_bytes: bytes) -> dict:
    """
    Analyzes an image using Google Cloud Vision API for logos, safety, and colors.
    """
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)
        logo_response = client.logo_detection(image=image)
        safe_search_response = client.safe_search_detection(image=image)
        properties_response = client.image_properties(image=image)
        analysis = {"detected_logo": None, "safety_ratings": {}, "dominant_colors": []}
        if logo_response.logo_annotations:
            logo = logo_response.logo_annotations[0]
            analysis["detected_logo"] = {"description": logo.description, "score": logo.score}
        if safe_search_response.safe_search_annotation:
            safety = safe_search_response.safe_search_annotation
            analysis["safety_ratings"] = {
                "adult": vision.Likelihood(safety.adult).name, "medical": vision.Likelihood(safety.medical).name,
                "spoof": vision.Likelihood(safety.spoof).name, "violence": vision.Likelihood(safety.violence).name,
                "racy": vision.Likelihood(safety.racy).name,
            }
        if properties_response.image_properties_annotation:
            props = properties_response.image_properties_annotation
            if props.dominant_colors and props.dominant_colors.colors:
                analysis["dominant_colors"] = [{"hex": f"#{int(c.color.red):02x}{int(c.color.green):02x}{int(c.color.blue):02x}", "percent": c.pixel_fraction} for c in props.dominant_colors.colors[:5]]
        return analysis
    except Exception as e:
        print(f"Error calling Google Vision API: {e}")
        raise Exception(f"Google Cloud Vision API failed: {e}")

def get_critique_and_refinement_with_gemini(image_bytes: bytes, brand_kit: dict, vision_analysis: dict) -> dict:
    """
    Uses Gemini to critique an ad and generate a refinement plan.
    """
    try:
        model = GenerativeModel("gemini-2.0-flash")
        brand_name = brand_kit.get("brand_name", "Unknown")
        prompt = f"""
        You are a Creative Director and Brand Compliance Officer for '{brand_name}'.
        Your task is to analyze the provided advertisement image based on the brand guidelines and a pre-analysis from the Google Vision API.

        **1. Brand Guidelines:**
        - Brand Name: {brand_name}
        - Official Color Palette (HEX): {", ".join(brand_kit.get("color_palette_hex", []))}
        - Tone of Voice Keywords: {", ".join(brand_kit.get("tone_of_voice_keywords", []))}
        - Official Taglines: {", ".join(brand_kit.get("taglines", []))}
        - Safety Rules: {" ".join(brand_kit.get("safety_rules", []))}

        **2. Google Vision API Pre-Analysis:**
        - Detected Logo: {vision_analysis.get('detected_logo') or 'None'}
        - Dominant Colors Found: {[c['hex'] for c in vision_analysis.get('dominant_colors', [])]}
        - Safety Analysis: {vision_analysis.get('safety_ratings', {})}

        **3. Your Task:**
        Based on all the information above, analyze the ad image and provide a detailed critique.
        Evaluate the ad across four dimensions: Brand Alignment, Visual Quality, Message Clarity, and Safety & Ethics.
        After the critique, generate a new, improved prompt for an image generation model (like Imagen) that would create a better version of this ad, addressing the weaknesses you identified.

        **4. Response Format (Strict JSON only):**
        Return a single JSON object with the following structure. Do not include any text outside of this JSON object.
        {{
          "scorecard": {{
            "brand_alignment": {{"score": <0-1>, "feedback": "<detailed feedback on logo, color, and tone>"}},
            "visual_quality": {{"score": <0-1>, "feedback": "<detailed feedback on composition, clarity, and professionalism>"}},
            "message_clarity": {{"score": <0-1>, "feedback": "<detailed feedback on the ad's message and call-to-action>"}},
            "safety_ethics": {{"score": <0-1>, "feedback": "<detailed feedback based on the Vision API safety analysis and brand rules>"}},
            "overall_score": <0-1>,
            "strengths": ["<list of 2-3 strengths>"],
            "what_to_improve": ["<list of 3-5 specific, actionable improvements>"]
          }},
          "refinement_plan": "<The new, detailed, and improved prompt for the image generation model.>"
        }}
        """
        image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
        generation_config = GenerationConfig(response_mime_type="application/json", temperature=0.7)
        response = model.generate_content([image_part, prompt], generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        raise Exception(f"Google Gemini API failed: {e}")

def regenerate_ad_with_imagen(refined_prompt: str) -> str:
    """
    Generates a new ad image using Imagen on Vertex AI.
    """
    try:
        # Using a specific, modern model version is better practice.
        model = GenerativeModel("imagen-3.0-generate-001")
        
        # Correctly structured parameters based on the official documentation.
        # These are passed to the 'parameters' field in the underlying REST API.
        # The Python SDK maps the 'generation_config' dict to these parameters.
        generation_parameters = {
            "candidate_count": 1,
            "aspectRatio": "1:1",
            "addWatermark": False,
            "safetySetting": "block_only_high"
        }
        
        response = model.generate_content(
            [refined_prompt],
            generation_config=generation_parameters
        )
        
        if not response.candidates:
            raise Exception("Imagen returned no image candidates.")

        image_part = response.candidates[0].content.parts[0]
        
        if image_part.mime_type not in ["image/png", "image/jpeg"]:
            raise Exception(f"Unexpected MIME type from Imagen: {image_part.mime_type}")

        image_bytes = image_part.data
        encoded_string = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

    except Exception as e:
        print(f"Error calling Imagen API: {e}")
        raise Exception(f"Google Imagen API failed: {e}")


# === MAIN API ENDPOINTS ===

@app.get("/")
async def root():
    """Serve main HTML file."""
    return FileResponse(STATIC_DIR / "index.html")

@app.post("/evaluate")
async def evaluate(image: UploadFile = File(...)):
    """
    Main endpoint to orchestrate the ad critique workflow.
    """
    print("\n" + "="*60)
    print("📥 NEW EVALUATION REQUEST RECEIVED")
    print(f"📎 Image: {image.filename}, Type: {image.content_type}")
    print("="*60 + "\n")

    try:
        image_bytes = await image.read()

        # --- Step 1: Analyze image with Vision API ---
        print("🔍 Step 1: Analyzing image with Cloud Vision API...")
        vision_analysis = analyze_image_with_vision_api(image_bytes)
        print(f"✅ Vision API analysis complete. Detected logo: {vision_analysis.get('detected_logo')}")

        # --- Step 2: Determine Brand ---
        print("🔍 Step 2: Determining brand from logo...")
        logo_analysis = vision_analysis.get("detected_logo")
        if not logo_analysis or not logo_analysis.get("description"):
            raise HTTPException(
                status_code=404, 
                detail="Brand logo could not be detected in the image. Please try another image."
            )

        logo_desc = logo_analysis["description"]
        detected_brand_name = None
        
        # Improved Matching Logic
        logo_words = logo_desc.lower().replace('-', ' ').split()

        for brand_key in brand_kits:
            # Check if the brand key (e.g., "cocacola") is in the logo description (e.g., "the coca-cola company")
            # This handles cases where the key has no spaces/hyphens.
            if brand_key in logo_desc.lower().replace('-', '').replace(' ', ''):
                detected_brand_name = brand_key
                break
            
            # Check if any significant word from the logo description is in the brand key
            if not detected_brand_name:
                for word in logo_words:
                    if len(word) > 2 and word in brand_key:
                        detected_brand_name = brand_key
                        break
            if detected_brand_name:
                break

        if not detected_brand_name:
            raise HTTPException(
                status_code=404,
                detail=f"Brand '{logo_desc}' was detected but is not supported. Supported brands are: {list(brand_kits.keys())}"
            )
        
        brand_kit = brand_kits.get(detected_brand_name)
        print(f"✅ Brand determined: {detected_brand_name}")

        # --- Step 3: Get Critique & Refinement from Gemini ---
        print("\n🤖 Step 3: Generating critique with Gemini API...")
        gemini_response = get_critique_and_refinement_with_gemini(image_bytes, brand_kit, vision_analysis)
        scorecard = gemini_response.get("scorecard")
        refined_prompt = gemini_response.get("refinement_plan")
        if not scorecard or not refined_prompt:
            raise Exception("Gemini response was missing scorecard or refinement_plan.")
        print(f"✅ Gemini critique complete. Overall score: {scorecard.get('overall_score', 'N/A')}")

        # --- Step 4: Assemble and Return Response ---
        original_image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        response_data = {
            "brand_detected": detected_brand_name,
            "brand_name": brand_kit.get("brand_name"),
            "original_image": f"data:{image.content_type};base64,{original_image_base64}",
            "scorecard": scorecard,
            "refinement_plan": refined_prompt,
            "timestamp": datetime.now().isoformat(),
            "vision_analysis": vision_analysis
        }
        
        print("\n" + "="*60)
        print("✅ EVALUATION COMPLETE - Sending response")
        print("="*60)
        return JSONResponse(content=response_data)

    except Exception as e:
        import traceback
        print(f"❌ Error in /evaluate workflow: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")

@app.post("/regenerate")
async def regenerate(request: RegenerationRequest):
    """
    Regenerates an ad image based on a refinement prompt.
    """
    print("\n" + "="*60)
    print("🎨 NEW REGENERATION REQUEST RECEIVED")
    print("="*60 + "\n")
    try:
        regenerated_image_url = regenerate_ad_with_imagen(request.refinement_plan)
        print("✅ Imagen regeneration complete.")
        return JSONResponse(content={"regenerated_image_url": regenerated_image_url})
    except Exception as e:
        import traceback
        print(f"❌ Error in /regenerate workflow: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An internal error occurred: {str(e)}")


# Mount static files for the frontend
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("\n" + "!"*80)
        print("! WARNING: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("! The application will not be able to authenticate with Google Cloud APIs.")
        print("! Please set it to the path of your service account JSON key file.")
        print("!"*80 + "\n")
    
    uvicorn.run(app, host=BACKEND_HOST, port=BACKEND_PORT)