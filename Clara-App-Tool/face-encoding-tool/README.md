# Face Encoding Console

A lightweight static web console for triggering the Clara face-encoding job.

## Features

- 🚀 One-click button to invoke the backend endpoint that runs `encode_faces.py`
- 📡 Live status indicator (Idle / Running / Success / Error)
- 🕒 Displays last run time and runtime duration
- 🧮 Shows encoded employee count (when returned by backend)
- 🧾 Rolling execution log in the browser
- ⚙️ Configurable endpoint URL (saved only in the current session)

## Folder Structure

```
face-encoding-tool/
├── index.html      # Main static page
├── styles.css      # Glassmorphism UI styling
├── app.js          # Front-end logic to call backend endpoint
└── assets/
    └── face-icon.svg (placeholder icon for header)
```

## Setup Instructions

### 1. Prepare the Backend Trigger
This UI expects an HTTP endpoint that triggers the face-encoding process. Examples:
- **API Gateway + Lambda** wrapping `encode_faces.py`
- **FastAPI** route exposed by the backend that calls `run_face_encoder.py`
- **Internal service** accessible only within your VPC

The endpoint should accept `POST` requests and ideally return JSON like:
```json
{
  "status": "success",
  "encoded_count": 42,
  "details": "Uploaded to s3://clara-employee-images/Pickle_file/encoding.pkl"
}
```

### 2. Host the Static App
Option A – **Local usage**: open `index.html` directly in the browser.
Option B – **S3 Static Website**:
1. Create an S3 bucket (disable public-block for static hosting).
2. Enable **Static website hosting** under bucket properties.
3. Upload all files inside `face-encoding-tool/` (keep folder structure).
4. Make the files public (via ACL or bucket policy).
5. Load the S3 website endpoint URL in your browser.

Option C – **CloudFront** in front of S3 for TLS + caching (recommended for production).

### 3. Configure the Endpoint
In the app, paste your trigger URL into the **Face Encoding Trigger Endpoint** field. The value is used only in memory (no storage). Then click **Run Face Encoding**.

## Security Considerations
- Protect the trigger endpoint with authentication (IAM, Cognito, API keys, etc.).
- Consider IP allowlists or private VPC connectivity for internal tools.
- If exposing through API Gateway, require signed requests or bearer tokens.

## Development Notes
- The UI is pure HTML/CSS/JS—no build tooling required.
- To customize styling, edit `styles.css`.
- Logs are limited to the last 400 lines to avoid browser performance issues.

## Next Steps
- Integrate with CloudWatch logs or backend APIs to fetch run history.
- Add authentication (e.g., Cognito Hosted UI) before showing the console.
- Extend the API to return detailed stats (encoded IDs, skipped records, errors).

---
Built for Clara Ops to simplify face encoding maintenance.
