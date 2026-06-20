# MediVision AI FastAPI Backend

## Structure

```text
backend/
  app/
    api/routes.py              # FastAPI endpoints
    core/config.py             # Paths and environment settings
    schemas/                   # Pydantic request/response models
    services/                  # Disease model and chatbot logic
    main.py                    # FastAPI app factory
  static/                      # HTML, CSS, JS, and image assets served by FastAPI
  main.py                      # Compatibility entrypoint
  requirements.txt
```

Start the API from the repository root:

```powershell
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Set your real Gemini key in `backend/.env`:

```text
FRONTEND_DIR="backend/static"
GEMINI_API_KEY="your-gemini-api-key"
GEMINI_MODEL="gemini-1.5-flash"
GEMINI_TEMPERATURE="0.3"
GEMINI_MAX_OUTPUT_TOKENS="1024"
X_RAY_GEMINI_MODEL="gemini-2.5-flash"
X_RAY_GEMINI_TEMPERATURE="0.2"
X_RAY_GEMINI_MAX_OUTPUT_TOKENS="2048"
X_RAY_MAX_FILE_SIZE_BYTES="10485760"
X_RAY_REQUEST_TIMEOUT_SECONDS="45"
```

You can also run the app package directly:

```powershell
uvicorn backend.app.main:app --reload
```

The Disease Prediction page calls `POST http://localhost:8000/predict` with one to five symptoms:

```json
{
  "symptoms": ["itching", "skin_rash", "nodal_skin_eruptions", "dischromic _patches", "fatigue"]
}
```

Use `GET http://localhost:8000/symptoms` to list valid symptom names.

The Health Chatbot page calls `POST http://localhost:8000/chat`:

```json
{
  "message": "What are common cold symptoms?"
}
```

Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` in `backend/.env` before starting FastAPI. This is the only env file loaded by the backend, and it is ignored by git.

Model-related environment variables can also be set in `backend/.env`, including Gemini settings and disease model file paths.

The X-Ray Analysis page calls `POST http://localhost:8000/api/xray/analyze` with multipart form data:

```text
file=<uploaded xray image>
```

Supported formats are `JPG`, `JPEG`, and `PNG`, with a default upload limit of `10MB`. The API returns structured JSON:

```json
{
  "image_type": "Chest",
  "findings": ["Mild bilateral streaky opacities"],
  "abnormalities": ["Possible lower-lobe infiltrate"],
  "severity": "Medium",
  "confidence": "84%",
  "summary": "AI-generated medical-style summary report. This is not a medical diagnosis.",
  "recommendations": ["Consult a qualified healthcare professional."]
}
```

The Health Reports page calls `POST http://localhost:8000/reports/generate` with a date range:

```json
{
  "user_id": 123,
  "start_date": "2026-06-01",
  "end_date": "2026-06-20"
}
```

After generation, the page can download the saved report as PDF or DOCX using the report ID returned by the API.

## FastAPI-served pages

The app no longer needs the React/Next dev server or a separate frontend folder. FastAPI serves static pages directly from `backend/static`:

```text
http://localhost:8000/
http://localhost:8000/dashboard
http://localhost:8000/predict
http://localhost:8000/chatbot
http://localhost:8000/xray
http://localhost:8000/reports
http://localhost:8000/history
http://localhost:8000/profile
http://localhost:8000/settings
http://localhost:8000/login
http://localhost:8000/register
```

Health check JSON is available at `GET http://localhost:8000/health`.
