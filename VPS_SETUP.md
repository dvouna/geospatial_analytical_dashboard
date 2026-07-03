# Dedicated VPS Setup Guide (healthdashboard.afiuk.org)

This guide outlines the commands and configurations required to set up a clean, dedicated Linux VPS (e.g. Ubuntu 22.04 / 24.04 LTS) for running the geospatial analytical dashboard.

---

## 1. System Updates & Essential Packages

Connect to your VPS via SSH:
```bash
ssh user@your_vps_ip
```

Update system packages and install essentials:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git ufw nginx certbot python3-certbot-nginx
```

---

## 2. Install Docker & Docker Compose

Install Docker using the official convenience script:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
```

Ensure your user is in the `docker` group to run commands without `sudo` (re-log after running this):
```bash
sudo usermod -aG docker $USER
```

Verify installation:
```bash
docker --version
docker compose version
```

---

## 3. Set Up Application Directory & Environment

1. Create a directory to host the application deployment configuration:
   ```bash
   sudo mkdir -p /opt/geospatial-dashboard
   sudo chown -R $USER:$USER /opt/geospatial-dashboard
   cd /opt/geospatial-dashboard
   ```

2. Create the `.env` configuration file:
   ```bash
   nano .env
   ```

   Paste and populate the following production environment settings:
   ```env
   # Gemini API Key (Required for AI assistant page)
   GEMINI_API_KEY=your_production_gemini_api_key_here

   # Streamlit Production Configuration
   STREAMLIT_SERVER_PORT=8501
   STREAMLIT_SERVER_ADDRESS=0.0.0.0
   STREAMLIT_SERVER_BASE_URL_PATH=/

   # App settings
   DEBUG=false
   MAX_UPLOAD_SIZE_MB=50
   DATA_DIR=data
   ```

3. Create the data persistence directory:
   ```bash
   mkdir -p data
   ```

---

## 4. Configure Nginx Reverse Proxy

Create an Nginx configuration file for the domain:
```bash
sudo nano /etc/nginx/sites-available/healthdashboard.afiuk.org
```

Paste the following configuration. This block reverse proxies requests to the Docker container running locally on port 8501, and includes the required headers for Streamlit's WebSocket connections:

```nginx
server {
    listen 80;
    server_name healthdashboard.afiuk.org;

    # Adjust client_max_body_size to allow CSV uploads
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        
        # Streamlit WebSocket headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Standard proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Keepalive/timeout settings for long-running map/data updates
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Enable the configuration and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/healthdashboard.afiuk.org /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 5. Obtain Let's Encrypt SSL Certificate

Run Certbot to request a free SSL certificate. Certbot will automatically configure Nginx to use SSL and redirect HTTP traffic to HTTPS:

```bash
sudo certbot --nginx -d healthdashboard.afiuk.org
```

Verify that Certbot's automatic renewal timer is active:
```bash
sudo systemctl status certbot.timer
```

---

## 6. Configure Firewall (UFW)

Restrict incoming traffic to HTTP, HTTPS, and SSH only:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Check firewall status:
```bash
sudo ufw status
```

---

## 7. Manual Startup Verification

Before setting up the CI/CD pipeline, pull and run the dashboard manually to verify components:

1. Copy the `docker-compose.yml` file from your local repository to `/opt/geospatial-dashboard/docker-compose.yml`.
2. Authenticate to GHCR (using a GitHub Personal Access Token with package read permissions):
   ```bash
   echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```
3. Run the container:
   ```bash
   docker compose up -d
   ```
4. Check the application logs:
   ```bash
   docker compose logs -f
   ```
5. Navigate to `https://healthdashboard.afiuk.org` in a browser. Confirm that the page loads correctly and map tiles display.
