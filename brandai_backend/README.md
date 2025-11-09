# BrandAI - AI Critique Engine
## Hack-Nation Global AI Hackathon

A comprehensive AI system that critiques, improves, and generates high-quality marketing advertisements using multi-dimensional analysis.

### Project Structure

```
brandai_backend/
├── main.py                 # FastAPI backend application
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── brand_kits/
│   └── database.json      # Brand guidelines database
└── static/
    ├── index.html         # Frontend UI
    ├── style.css          # Professional styling
    └── script.js          # Frontend logic
```

### Features

**Hero Feature: AI Critique Engine**
- Multi-dimensional brand ad analysis
- Brand Alignment scoring (color palette, logo, tone)
- Visual Quality assessment (clarity, composition, artifacts)
- Message Clarity evaluation (product visibility, CTA)
- Safety & Ethics verification

**Improvement Pipeline**
- AI-powered refinement prompt generation
- Automatic ad regeneration using DALL-E 3
- Structured critique scorecard delivery

### Setup Instructions

#### 1. Install Dependencies
```bash
cd brandai_backend
pip install -r requirements.txt
```

#### 2. Configure Environment Variables
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
GOOGLE_CLOUD_API_KEY=your_google_cloud_vision_api_key
OPENAI_API_KEY=your_openai_api_key
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
```

**Getting API Keys:**
- **Google Cloud Vision API**: [https://cloud.google.com/vision/docs/setup](https://cloud.google.com/vision/docs/setup)
- **OpenAI API Key**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

#### 3. Run the Backend
```bash
python main.py
```

The server will start at `http://localhost:8000`

#### 4. Access the Frontend
Open your browser and navigate to:
```
http://localhost:8000
```

### API Endpoints

#### POST /evaluate-and-improve
Main endpoint for ad critique and improvement.

**Request:**
- `image` (File): Ad image (JPEG, PNG, WebP, max 10MB)
- `prompt` (String): Original ad prompt

**Response:**
```json
{
  "brand_detected": "nike",
  "brand_name": "Nike",
  "original_image": "data:image/jpeg;base64,...",
  "original_prompt": "...",
  "scorecard": {
    "brand_alignment": { "score": 0.85, "feedback": "..." },
    "visual_quality": { "score": 0.78, "feedback": "..." },
    "message_clarity": { "score": 0.82, "feedback": "..." },
    "safety_ethics": { "score": 0.9, "feedback": "..." },
    "overall_score": 0.84,
    "what_to_improve": ["..."],
    "strengths": ["..."]
  },
  "refinement_plan": "...",
  "regenerated_image_url": "..."
}
```

#### GET /health
Health check endpoint.

### How It Works

1. **Upload Phase**: User submits ad image and original prompt
2. **Brand Detection**: Google Vision API identifies the brand
3. **Critique Analysis**: GPT-4 Vision evaluates across 4 dimensions
4. **Refinement**: LLM generates improved prompt based on feedback
5. **Regeneration**: DALL-E 3 creates improved ad from refined prompt
6. **Display**: Results shown in three-column dashboard

### Brand Kits

The system includes built-in brand guidelines for:
- **Nike**: Athletic, inspirational tone
- **Coca-Cola**: Happiness, togetherness focus
- **Apple**: Innovation, minimalist aesthetic

Add custom brands to `brand_kits/database.json`:
```json
{
  "your_brand": {
    "brand_name": "Your Brand",
    "color_palette_hex": ["#000000", "#FFFFFF"],
    "tone_of_voice_keywords": ["keyword1", "keyword2"],
    "taglines": ["Tagline 1"],
    "safety_rules": ["Rule 1"]
  }
}
```

### Error Handling

The system gracefully falls back to mock data if:
- API keys are not configured
- External APIs are unavailable
- Image processing fails

This allows testing without valid API credentials.

### Performance

- Image upload limit: 10MB
- Critique generation time: ~15-30 seconds
- Ad regeneration time: ~30-60 seconds

### Security

- CORS enabled for frontend access
- Input validation for image formats
- API key environment variables (never hardcoded)
- File type and size restrictions

### Future Enhancements

- Batch processing for multiple ads
- Critique history and analytics
- Custom brand kit creation UI
- A/B testing recommendations
- Export critique reports as PDF

### Support

For issues or questions, refer to the FastAPI and OpenAI documentation:
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [OpenAI API Docs](https://platform.openai.com/docs/)
- [Google Cloud Vision Docs](https://cloud.google.com/vision/docs/)
