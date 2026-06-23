# Google Cloud Run Deployment Guide

This guide outlines the steps to containerize and deploy the geospatial dashboard to **Google Cloud Run**.

---

## 1. Container Configuration

We have created the necessary files in the root of the project to prepare the application for containerization:
*   [Dockerfile](file:///c:/Users/davic/flc26/Dockerfile) - Uses a lightweight Python 3.11 image and installs the system-level packages (GDAL, PROJ, etc.) required for geospatial operations.
*   [.dockerignore](file:///c:/Users/davic/flc26/.dockerignore) - Excludes local virtual environments (`venv`), Jupyter notebooks (`.ipynb`), and environment secrets (`.env`) from the built container image.

---

## 2. Prerequisites

Before deploying, ensure you have the following set up:
1.  **Google Cloud Project**: An active GCP project with billing enabled.
2.  **gcloud CLI**: Installed and initialized on your local machine ([Download gcloud CLI](https://cloud.google.com/sdk/docs/install)).
3.  **Required APIs**: Enable the Cloud Run, Cloud Build, and Secret Manager APIs:
    ```powershell
    gcloud services enable run.googleapis.com build.googleapis.com secretmanager.googleapis.com
    ```

---

## 3. Step-by-Step Deployment Instructions

### Step 1: Initialize gcloud CLI
Authenticate and set your target GCP project:
```powershell
# Authenticate your terminal
gcloud auth login

# Set your active GCP project
gcloud config set project [YOUR_PROJECT_ID]
```

### Step 2: Configure Secrets (For Gemini API Key)
Do not hardcode or pass the Gemini API key as a plain environment variable. Use GCP Secret Manager:

1.  Create a secret name `gemini-api-key`:
    ```powershell
    gcloud secrets create gemini-api-key --replication-policy="automatic"
    ```
2.  Add your API key value to the secret:
    ```powershell
    # Windows PowerShell
    "YOUR_GEMINI_API_KEY" | gcloud secrets versions add gemini-api-key --data-file=-
    ```

### Step 3: (Optional) Build and Run the Container Locally
Before deploying to Google Cloud, you can build and test the container image on your local machine using Docker to ensure there are no startup or C library compilation issues:

1.  **Build the Docker Image**:
    ```powershell
    docker build -t geospatial-dashboard:local .
    ```
2.  **Run the Container**:
    Inject your environment variables and access token:
    ```powershell
    docker run -p 8080:8080 --env-file=.env -e GEMINI_API_KEY="your-api-key-here" geospatial-dashboard:local
    ```
3.  **Access the App**:
    Navigate to `http://localhost:8080` in your web browser.

### Step 4: Build and Deploy the Container to Cloud Run
Run the deployment command from the project root. This command uses Cloud Build to package your source files into a container, uploads it to the container registry, and deploys it:

```powershell
gcloud run deploy geospatial-dashboard `
  --source . `
  --region us-central1 `
  --allow-unauthenticated `
  --port 8080 `
  --set-secrets=GEMINI_API_KEY=gemini-api-key:latest
```

Once deployment is complete, `gcloud` will output a service URL (e.g., `https://geospatial-dashboard-xxxxxx-uc.a.run.app`).

---

## 4. Production Adjustments (WordPress Integration / Nginx)

As defined in `.env.production`, you might want to serve the application under a custom domain (`app.yourdomain.com`) or route it through a reverse proxy (e.g., your WordPress site under `yourdomain.com/dashboard`).

### Streamlit Base URL Path Adjustment
If serving the dashboard at a path (e.g. `/dashboard`), modify the `CMD` instruction at the end of the [Dockerfile](file:///c:/Users/davic/flc26/Dockerfile) to pass the base path:
```dockerfile
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.baseUrlPath=/dashboard"]
```

### Nginx Reverse Proxy Config
To embed the dashboard under `/dashboard` on your main site, add the following to your Nginx configuration:

```nginx
location /dashboard {
    proxy_pass https://geospatial-dashboard-xxxxxx-uc.a.run.app/dashboard;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

*Note: Streamlit relies on persistent WebSockets. The `Upgrade` and `Connection` headers are required for the connection to remain stable.*
