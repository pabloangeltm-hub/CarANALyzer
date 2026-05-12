#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${AGARTHA_APP_DIR:-/opt/agartha}"
REPO_URL="${AGARTHA_REPO_URL:-}"
BRANCH="${AGARTHA_BRANCH:-main}"
SERVICE_NAME="${AGARTHA_SERVICE_NAME:-agartha}"
CONFIGURE_UFW="${AGARTHA_CONFIGURE_UFW:-1}"
START_SERVICE="${AGARTHA_START_SERVICE:-1}"

log() {
  printf '[agartha-setup] %s\n' "$*"
}

fail() {
  printf '[agartha-setup] ERROR: %s\n' "$*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "run this script as root: sudo ./setup_vps.sh"
  fi
}

load_os_release() {
  if [[ ! -r /etc/os-release ]]; then
    fail "/etc/os-release not found; this script supports Ubuntu/Debian hosts"
  fi
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_ID="${ID:-}"
  OS_CODENAME="${VERSION_CODENAME:-}"
  if [[ "${OS_ID}" != "ubuntu" && "${OS_ID}" != "debian" ]]; then
    fail "unsupported OS '${OS_ID}'. Use Ubuntu or Debian"
  fi
  if [[ -z "${OS_CODENAME}" ]]; then
    fail "VERSION_CODENAME missing in /etc/os-release"
  fi
}

install_base_packages() {
  log "installing base packages"
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ca-certificates \
    curl \
    git \
    gnupg \
    ufw
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "docker and compose plugin already installed"
    return
  fi

  log "installing docker engine from official apt repository"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL "https://download.docker.com/linux/${OS_ID}/gpg" -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/%s %s stable\n' \
    "$(dpkg --print-architecture)" "${OS_ID}" "${OS_CODENAME}" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
  systemctl enable --now docker
}

prepare_app_dir() {
  if [[ -n "${REPO_URL}" && ! -d "${APP_DIR}/.git" ]]; then
    log "cloning ${REPO_URL} into ${APP_DIR}"
    mkdir -p "$(dirname "${APP_DIR}")"
    git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
  fi

  if [[ ! -f "${APP_DIR}/docker-compose.yml" ]]; then
    fail "docker-compose.yml not found in ${APP_DIR}. Set AGARTHA_REPO_URL or copy the repo there first"
  fi

  mkdir -p "${APP_DIR}/.tmp" "${APP_DIR}/logs"
}

install_systemd_unit() {
  local unit_src="${APP_DIR}/deploy/systemd/agartha.service"
  local unit_dst="/etc/systemd/system/${SERVICE_NAME}.service"

  if [[ ! -f "${unit_src}" ]]; then
    fail "systemd unit not found: ${unit_src}"
  fi

  log "installing systemd unit ${unit_dst}"
  install -m 0644 "${unit_src}" "${unit_dst}"
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}.service"
}

configure_firewall() {
  if [[ "${CONFIGURE_UFW}" != "1" ]]; then
    log "skipping ufw configuration"
    return
  fi
  if ! command -v ufw >/dev/null 2>&1; then
    log "ufw not available; skipping firewall configuration"
    return
  fi

  log "allowing SSH, HTTP and HTTPS through ufw"
  ufw allow OpenSSH
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
}

start_stack() {
  if [[ "${START_SERVICE}" != "1" ]]; then
    log "skipping service start"
    return
  fi
  if [[ ! -f "${APP_DIR}/.env" ]]; then
    log ".env not found in ${APP_DIR}; leaving ${SERVICE_NAME}.service enabled but stopped"
    log "create ${APP_DIR}/.env, then run: systemctl start ${SERVICE_NAME}.service"
    return
  fi

  log "building compose images"
  docker compose --project-directory "${APP_DIR}" -f "${APP_DIR}/docker-compose.yml" build
  log "starting ${SERVICE_NAME}.service"
  systemctl restart "${SERVICE_NAME}.service"
}

main() {
  require_root
  load_os_release
  install_base_packages
  install_docker
  prepare_app_dir
  install_systemd_unit
  configure_firewall
  start_stack
  log "setup complete"
}

main "$@"
