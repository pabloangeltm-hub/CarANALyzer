#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${AGARTHA_APP_DIR:-/opt/agartha}"
DOMAIN="${AGARTHA_DOMAIN:-}"
EMAIL="${AGARTHA_EMAIL:-}"
INCLUDE_WWW="${AGARTHA_INCLUDE_WWW:-1}"
STAGING="${AGARTHA_LETSENCRYPT_STAGING:-0}"
COMPOSE_FILE="${AGARTHA_COMPOSE_FILE:-${APP_DIR}/docker-compose.yml}"
TEMPLATE_PATH="${AGARTHA_SSL_TEMPLATE:-${APP_DIR}/deploy/nginx/nginx.ssl.conf.template}"
NGINX_CONF="${AGARTHA_NGINX_CONF:-${APP_DIR}/nginx.conf}"

log() {
  printf '[agartha-tls] %s\n' "$*"
}

fail() {
  printf '[agartha-tls] ERROR: %s\n' "$*" >&2
  exit 1
}

compose() {
  docker compose --project-directory "${APP_DIR}" -f "${COMPOSE_FILE}" --profile certbot "$@"
}

require_inputs() {
  [[ -n "${DOMAIN}" ]] || fail "set AGARTHA_DOMAIN, for example agartha.example.com"
  [[ -n "${EMAIL}" ]] || fail "set AGARTHA_EMAIL for Let's Encrypt expiry notices"
  [[ -f "${COMPOSE_FILE}" ]] || fail "compose file not found: ${COMPOSE_FILE}"
  [[ -f "${TEMPLATE_PATH}" ]] || fail "nginx SSL template not found: ${TEMPLATE_PATH}"
}

certbot_domain_args() {
  printf -- '-d\n%s\n' "${DOMAIN}"
  if [[ "${INCLUDE_WWW}" == "1" && "${DOMAIN}" != www.* ]]; then
    printf -- '-d\nwww.%s\n' "${DOMAIN}"
  fi
}

render_nginx_ssl_config() {
  local escaped_domain
  local escaped_cert_name
  escaped_domain="$(printf '%s' "${DOMAIN}" | sed 's/[\/&]/\\&/g')"
  escaped_cert_name="${escaped_domain}"

  log "rendering SSL nginx config to ${NGINX_CONF}"
  if [[ -f "${NGINX_CONF}" ]]; then
    cp "${NGINX_CONF}" "${NGINX_CONF}.pre-ssl"
  fi
  sed \
    -e "s/{{DOMAIN}}/${escaped_domain}/g" \
    -e "s/{{CERT_NAME}}/${escaped_cert_name}/g" \
    "${TEMPLATE_PATH}" >"${NGINX_CONF}"
}

issue_certificate() {
  local staging_args=()
  local domain_args=()
  if [[ "${STAGING}" == "1" ]]; then
    staging_args=(--staging)
  fi
  mapfile -t domain_args < <(certbot_domain_args)

  log "starting HTTP stack for ACME webroot challenge"
  compose up -d nginx

  log "requesting Let's Encrypt certificate for ${DOMAIN}"
  compose run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --keep-until-expiring \
    "${staging_args[@]}" \
    "${domain_args[@]}"
}

reload_nginx() {
  log "reloading nginx with SSL configuration"
  compose up -d nginx
  compose exec -T nginx nginx -s reload
}

main() {
  require_inputs
  issue_certificate
  render_nginx_ssl_config
  reload_nginx
  log "TLS setup complete"
}

main "$@"
