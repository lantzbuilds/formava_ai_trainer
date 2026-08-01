#!/usr/bin/env bash
# Deploy Formava to the VPS. Modelled on Clio's scripts/deploy.sh.
#
# Usage:
#   ./scripts/deploy_vps.sh            # build + sync + install + restart
#   ./scripts/deploy_vps.sh sync       # rsync only
#   ./scripts/deploy_vps.sh restart    # restart both units
#   ./scripts/deploy_vps.sh logs api   # follow logs (api|web)
#   ./scripts/deploy_vps.sh status
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

VPS_HOST="${VPS_HOST:-144.202.88.7}"
VPS_USER="${VPS_USER:-root}"
APP_PATH="${APP_PATH:-/opt/formava}"

SSH="ssh ${VPS_USER}@${VPS_HOST}"

GREEN='\033[0;32m'; NC='\033[0m'
log() { echo -e "${GREEN}[deploy]${NC} $1"; }

build_frontend() {
    log "Building Next.js standalone bundle locally..."
    # Built here, not on the host: `next build` wants 1.5-2 GB and would
    # needlessly contend with Clio.
    (cd "$PROJECT_DIR/frontend" && npm ci && npm run build)
}

sync_files() {
    log "Syncing to ${VPS_HOST}:${APP_PATH}..."
    $SSH "mkdir -p ${APP_PATH}"

    # Gradio is deliberately excluded -- it must never reach the VPS.
    #
    # node_modules excludes are anchored (leading '/') rather than a bare
    # 'node_modules' pattern: an unanchored pattern also matches
    # frontend/.next/standalone/node_modules, which is the trimmed,
    # production-only dependency set that `next build` traces into the
    # standalone bundle -- server.js requires it (e.g. the `next` package
    # itself) and won't start without it. Only the *source* node_modules
    # trees (repo root and frontend/, both rebuildable via npm install) are
    # meant to be skipped.
    rsync -avz --delete \
        --exclude '.git' \
        --exclude '.venv' \
        --exclude '/node_modules' \
        --exclude '/frontend/node_modules' \
        --exclude '__pycache__' \
        --exclude '.env' \
        --exclude '.next/cache' \
        --exclude 'app/pages' \
        --exclude 'app/routes.py' \
        --exclude 'app/theme.py' \
        --exclude 'app/config/state.py' \
        --exclude 'tests' \
        --exclude '*.log' \
        --exclude '.DS_Store' \
        "$PROJECT_DIR/" "${VPS_USER}@${VPS_HOST}:${APP_PATH}/"
}

install_deps() {
    log "Installing Python dependencies in the venv..."
    $SSH "cd ${APP_PATH} && \
        (test -d .venv || python3 -m venv .venv) && \
        .venv/bin/pip install --upgrade pip -q && \
        .venv/bin/pip install -r requirements-api.txt -q"
}

install_units() {
    log "Installing systemd units..."
    $SSH "cp ${APP_PATH}/scripts/vps/formava-api.service /etc/systemd/system/ && \
          cp ${APP_PATH}/scripts/vps/formava-web.service /etc/systemd/system/ && \
          systemctl daemon-reload && \
          systemctl enable formava-api formava-web"
}

restart_services() {
    log "Restarting services..."
    $SSH "systemctl restart formava-api formava-web"
    sleep 3
    $SSH "systemctl is-active formava-api formava-web"
}

case "${1:-deploy}" in
    deploy)  build_frontend; sync_files; install_deps; install_units; restart_services ;;
    build)   build_frontend ;;
    sync)    sync_files ;;
    install) install_deps; install_units ;;
    restart) restart_services ;;
    logs)    $SSH "journalctl -u formava-${2:-api} -f --no-pager -n 50" ;;
    status)  $SSH "systemctl status formava-api formava-web --no-pager" ;;
    *)       echo "Usage: $0 {deploy|build|sync|install|restart|logs|status}"; exit 1 ;;
esac

log "Done."
