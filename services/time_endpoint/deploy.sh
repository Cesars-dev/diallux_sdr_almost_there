#!/bin/bash
set -e

echo "Deploying time_endpoint to VPS..."

VPS_USER="2nd_workspace"
VPS_HOST="MainVps"
VPS_PROJECT_DIR="~/projects/Retell_AI_MCP_connection/time_endpoint"

echo "Copying files to VPS..."
rsync -avz --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  . ${VPS_USER}@${VPS_HOST}:${VPS_PROJECT_DIR}/

echo "Files copied successfully"

echo "Installing systemd service..."
ssh ${VPS_USER}@${VPS_HOST} << 'REMOTE_EOF'
cd ~/projects/Retell_AI_MCP_connection/time_endpoint

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo "Installing systemd service..."
systemctl --user link --force time-service.service
systemctl --user daemon-reload

echo "Service installation completed"
REMOTE_EOF

echo "Deployment completed successfully!"
echo ""
echo "Next steps:"
echo "1. Start service: systemctl --user start time-service"
echo "2. Check status:  systemctl --user status time-service"
echo "3. View logs:     journalctl --user -u time-service -f"
echo ""
echo "4. Add the /time-function block to the existing slots.diallux-ai.site site"
echo "   block in /etc/caddy/Caddyfile (see README.md), then:"
echo "   sudo caddy validate --config /etc/caddy/Caddyfile"
echo "   sudo systemctl reload caddy"
