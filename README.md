# Image Caption Generator — Vercel Deployment

A one-page app that uploads an image and returns a single-line AI-generated
caption, using the Gemini API from a Vercel Python serverless function.

## Deploying to Vercel

1. Push this folder to a GitHub repo (or run `vercel --prod` from inside it).
2. Go to [vercel.com](https://vercel.com) → **New Project** → import the repo.
3. In **Project Settings → Environment Variables**, add:
   - `GEMINI_API_KEY` = your Google Gemini API key (get one at [ai.google.dev](https://ai.google.dev))
4. Click **Deploy**. Your app goes live at `https://your-app.vercel.app`.

### Or via CLI
```bash
vercel env add GEMINI_API_KEY
vercel --prod
```

## What was fixed

The project as uploaded would not deploy/run correctly on Vercel. Fixes made:

- **`requirements.txt` listed the wrong package.** It pinned
  `google-generativeai` (the old SDK), but `api/caption.py` imported
  `from google import genai`, which belongs to the newer `google-genai`
  package. Mismatched import → `ModuleNotFoundError` at runtime.
  Fixed to `google-genai`, and the client code now matches that SDK
  (`genai.Client(api_key=...)` instead of the old `genai.configure(...)`).
- **Wrong Vercel function contract.** `api/caption.py` defined
  `def handler(request): return {"statusCode": ...}`, which is the AWS
  Lambda shape, not what Vercel's Python runtime expects. Vercel requires
  either a `BaseHTTPRequestHandler` subclass named `handler` or a WSGI
  `app`. Rewritten as a proper `BaseHTTPRequestHandler`, so the endpoint
  actually responds instead of erroring on every request.
- **Deprecated model name.** `gemini-pro-vision` has been retired.
  Switched to `gemini-2.0-flash`.
- **Hardcoded `image/jpeg` mime type** even for PNG/WebP uploads, which
  Gemini could reject. Now parsed from the incoming data URL.
- **No `GEMINI_API_KEY` guard.** A missing key used to throw an opaque
  500 stack trace. Now it returns a clear, actionable error message
  instead of crashing.
- **Removed ~130MB of unused local-model files** (`caption_model.keras`,
  `yolov8m.pt`, `tokenizer.pkl`, `app_gradio.py`) left over from an
  earlier local Keras/YOLO/Gradio prototype that the Vercel/Gemini path
  never uses. They were only bloating the repo and slowing every deploy.
- Added `maxDuration: 30` in `vercel.json` so the function has enough
  time for the Gemini round trip on the Hobby plan.
- Added CORS/OPTIONS handling and a friendlier `GET` response on the
  API route.

## Usage

1. Open the deployed app.
2. Upload (or drag & drop) any image.
3. Click **Generate Caption** to get a one-line AI caption.

## Local development

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
vercel dev
```
