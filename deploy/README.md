Deployment instructions for Droplet (DigitalOcean)

Prereqs: a Droplet (Ubuntu 22.04), Docker installed, and DNS pointing to Droplet IP.

Quick steps summary:
1. SSH into droplet and clone the repo into /opt/lab2_nieuwsMetAI
2. Put your secrets in `/opt/lab2_nieuwsMetAI/.env` (MONGODB_URI, COHERE_API_KEY, MONGODB_DB)
3. Build and run with docker compose:
   sudo docker compose up -d --build
4. Configure Nginx: copy `deploy/nginx/nieuwsmetai.conf` to `/etc/nginx/sites-available/nieuwsmetai` and symlink to sites-enabled, then restart Nginx.
5. Get TLS via certbot:
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d api.example.com
6. (Optional) enable systemd service to run on boot (copy `deploy/systemd/nieuwsmetai.service` to /etc/systemd/system/ and run `sudo systemctl enable nieuwsmetai`)

Notes:
- Update `server_name` in the nginx config to your real domain.
- The docker image listens on port 8000 inside the container; nginx proxies to localhost:8000.
- Ensure your Atlas cluster allows the Droplet IP in the IP whitelist.
