# 🚀 CacheMind Production Deployment Guide

This guide walks you through deploying **CacheMind** to production. Depending on your infrastructure and budget, choose the method that best fits your needs:

| Method | Best For | Estimated Setup Time | Recommended Specs |
| :--- | :--- | :--- | :--- |
| **[Method 1: Docker Compose](#method-1-docker-compose-recommended)** | Cloud VPS (AWS EC2, DigitalOcean, Hetzner) or on-premise servers | 5 minutes | 2 vCPU, 4GB+ RAM |
| **[Method 2: Managed Cloud (Railway / Render + Vercel)](#method-2-managed-cloud-railway--render--vercel)** | Serverless / PaaS deployment without managing Linux VMs | 10 minutes | Free / Low tier |
| **[Method 3: Native Ubuntu VPS (Systemd + Nginx)](#method-3-native-ubuntu-vps-systemd--nginx--certbot)** | Bare-metal performance, custom domains & automated SSL | 15 minutes | 2 vCPU, 4GB+ RAM |

---

## 🏗️ Architecture & Component Overview

CacheMind consists of two core services:

```text
┌────────────────────────────────────────────────────────┐
│               Public Internet / Browser                │
└──────────────────────────┬─────────────────────────────┘
                           │ Port 80 / 443 (HTTP/HTTPS)
                           ▼
┌────────────────────────────────────────────────────────┐
│          Nginx Reverse Proxy & Static Host             │
│   • Serves React 18 / Tailwind / Vite Static SPA       │
│   • Proxies /api/* requests to FastAPI Backend         │
└──────────────────────────┬─────────────────────────────┘
                           │ Internal Docker Network / Port 8000
                           ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI Asynchronous Gateway              │
│   • 5-Tier Cache Hierarchy (L1 Exact, L2 Semantic...)  │
│   • Ingestion & Hybrid FAISS/BM25 Search               │
│   • Agentic Planner & Groq / llama.cpp Router          │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   Persistent Volume                    │
│   • SQLite Database (/app/data/cachemind.db)           │
│   • Uploaded Documents (/app/data/documents)           │
│   • FAISS Vector Indices (/app/data/indices)           │
└────────────────────────────────────────────────────────┘
```

---

## Method 1: Docker Compose (Recommended)

This is the easiest, battle-tested deployment method. It packages the FastAPI backend (with CPU-optimized PyTorch and pre-cached Sentence-Transformers) and the React frontend (with multi-stage Nginx) into lightweight containers.

### Step 1: Clone Repository & Configure Environment

```bash
git clone https://github.com/Ritesh-iiitn/docchat-genai.git
cd docchat-genai

# Copy sample environment configuration
cp ai_doc_assistant/.env.example ai_doc_assistant/.env
```

Edit `ai_doc_assistant/.env` to configure your API keys:

```bash
# Optional: Add Groq API Key for 500+ tokens/s cloud LLM inference
GROQ_API_KEY="gsk_your_groq_api_key_here"

# Model Routing & Cache settings (defaults are already tuned)
EMBEDDING_MODEL_NAME="all-MiniLM-L6-v2"
```

### Step 2: Build and Run Containers

From the repository root:

```bash
docker compose up -d --build
```

*(Or from inside `ai_doc_assistant/`: `docker compose up -d --build`)*

### Step 3: Verify Running Services

```bash
docker compose ps
```

You should see:
- `cachemind-backend` running on port `8000` (status: `healthy`)
- `cachemind-frontend` running on port `3000`

### Step 4: Access the Application

- **Frontend Observatory Dashboard**: `http://<your-server-ip>:3000`
- **Backend API & Swagger Docs**: `http://<your-server-ip>:8000/docs`
- **Healthcheck**: `http://<your-server-ip>:8000/health`

### Managing & Updating

```bash
# View live logs
docker compose logs -f

# Restart services
docker compose restart

# Stop services (data is preserved in ./ai_doc_assistant/data)
docker compose down

# Update to latest code and rebuild
git pull
docker compose up -d --build
```

---

## Method 2: Managed Cloud (Railway / Render / Vercel)

If you prefer not to manage Linux servers or Docker yourself, deploy the backend and frontend separately:

### Part A: Deploy Backend (Render or Railway)

#### Deploying on Render:
1. Go to [Render.com](https://render.com) and click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the service:
   - **Root Directory**: `ai_doc_assistant`
   - **Environment**: `Python 3` (or choose `Docker` using `Dockerfile.backend`)
   - **Build Command**: `pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. In **Environment Variables**, add:
   - `GROQ_API_KEY`: your key (optional)
   - `PYTHONPATH`: `/opt/render/project/src/ai_doc_assistant`
5. *(Optional)* Add a **Persistent Disk** mounted at `/app/data` (or set `STORAGE_DIR=/var/data`) so uploaded documents and FAISS indices persist across restarts.
6. Once deployed, note your backend URL (e.g., `https://cachemind-api.onrender.com`).

#### Deploying on Railway:
1. Go to [Railway.app](https://railway.app) -> **New Project** -> **Deploy from GitHub repo**.
2. Select your repository. In settings, set the Dockerfile path to `ai_doc_assistant/Dockerfile.backend`.
3. Add a persistent volume mounted to `/app/data`.
4. Add environment variables (`GROQ_API_KEY`).
5. Generate a public domain under **Networking**.

---

### Part B: Deploy Frontend (Vercel)

1. Go to [Vercel.com](https://vercel.com) and click **Add New...** -> **Project**.
2. Import your GitHub repository.
3. Configure Project:
   - **Root Directory**: click **Edit** and choose `ai_doc_assistant/frontend`.
   - **Framework Preset**: Vite.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. In **Environment Variables**, add:
   - `VITE_API_BASE_URL`: `https://<your-backend-domain>/api/v1`
   *(e.g., `https://cachemind-api.onrender.com/api/v1`)*
5. Click **Deploy**. Vercel will build and assign an HTTPS URL (e.g., `https://cachemind.vercel.app`).

---

## Method 3: Native Ubuntu VPS (Systemd + Nginx + Certbot)

For a dedicated VPS (Ubuntu 22.04 / 24.04 LTS) with full control and automated SSL:

### 1. System Packages & Python 3.11

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nodejs npm nginx git certbot python3-certbot-nginx
```

### 2. Clone & Setup Backend

```bash
cd /opt
sudo git clone https://github.com/Ritesh-iiitn/docchat-genai.git cachemind
sudo chown -R $USER:$USER /opt/cachemind
cd /opt/cachemind/ai_doc_assistant

# Create virtualenv
python3 -m venv venv
source venv/bin/activate

# Install CPU PyTorch and dependencies
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt

# Pre-cache embedding model
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### 3. Build Frontend

```bash
cd /opt/cachemind/ai_doc_assistant/frontend
npm install
npm run build
# Built files are located at /opt/cachemind/ai_doc_assistant/frontend/dist
```

### 4. Create Systemd Service for FastAPI

Create `/etc/systemd/system/cachemind-backend.service`:

```ini
[Unit]
Description=CacheMind FastAPI Backend Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/cachemind/ai_doc_assistant
Environment="PATH=/opt/cachemind/ai_doc_assistant/venv/bin"
Environment="PYTHONPATH=/opt/cachemind/ai_doc_assistant"
EnvironmentFile=/opt/cachemind/ai_doc_assistant/.env
ExecStart=/opt/cachemind/ai_doc_assistant/venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cachemind-backend
sudo systemctl start cachemind-backend
sudo systemctl status cachemind-backend
```

### 5. Configure Nginx

Create `/etc/nginx/sites-available/cachemind`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com; # Or your server IP

    client_max_body_size 100M;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # Frontend Static Files
    location / {
        root /opt/cachemind/ai_doc_assistant/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

Enable the configuration and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/cachemind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. Enable Free HTTPS (Let's Encrypt)

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## ⚙️ Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | `""` | Optional. If provided, queries use Groq Cloud API for ultra-fast Llama-3.3-70B generation. |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | Hugging Face embedding model used for dense semantic retrieval. |
| `EMBEDDING_DIMENSION` | `384` | Dimensionality of embeddings. |
| `EXACT_CACHE_TTL_SECONDS` | `86400` | Expiration for L1 Exact Cache (default: 24h). |
| `RETRIEVAL_CACHE_TTL_SECONDS` | `43200` | Expiration for L4 Retrieval Result Cache (default: 12h). |
| `LLAMA_CPP_BASE_URL` | `http://localhost:8080` | URL for local llama.cpp or Ollama instance if running local weights. |
| `USE_MOCK_LLM_IF_UNAVAILABLE` | `true` | When true, returns grounded template responses if neither Groq nor llama.cpp is reached. |
| `STORAGE_DIR` | `<root>/data` | Directory for persistent SQLite DB, documents, and FAISS indices. |
| `VITE_API_BASE_URL` | `/api/v1` | Frontend API URL pointing to the FastAPI backend. |

---

## 🧪 Post-Deployment Verification & Smoke Testing

Once deployed, run these quick sanity checks:

### 1. Healthcheck Endpoint
```bash
curl -i http://localhost:8000/health
# HTTP/1.1 200 OK
# {"status":"healthy","service":"CacheMind","version":"1.0.0"}
```

### 2. Verify Knowledge Base Creation
```bash
curl -X POST http://localhost:8000/api/v1/kb \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Smoke Test", "description": "Testing live deployment"}'
```

### 3. Check Real-Time Cache Stats
```bash
curl http://localhost:8000/api/v1/cache/stats
```

### 4. Test Frontend
Open `http://localhost:3000` (or your domain) in any browser, upload a sample document in the **Knowledge Base** tab, and ask a question in the **Query Playground**. Verify that latency telemetry and cache hits appear in real time!
