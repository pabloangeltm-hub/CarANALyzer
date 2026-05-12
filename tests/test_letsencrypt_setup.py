from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = ROOT / "docker-compose.yml"
TLS_SCRIPT = ROOT / "tools" / "setup_letsencrypt.sh"
NGINX_TEMPLATE = ROOT / "deploy" / "nginx" / "nginx.ssl.conf.template"
RENEW_SERVICE = ROOT / "deploy" / "systemd" / "agartha-certbot-renew.service"
RENEW_TIMER = ROOT / "deploy" / "systemd" / "agartha-certbot-renew.timer"


def test_compose_defines_certbot_service_with_shared_acme_volumes():
    text = COMPOSE_PATH.read_text(encoding="utf-8")

    assert "  certbot:" in text
    assert "image: certbot/certbot:latest" in text
    assert "profiles:" in text
    assert "- certbot" in text
    assert "certbot_www:/var/www/certbot" in text
    assert "certbot_conf:/etc/letsencrypt" in text
    assert "  certbot_www:" in text
    assert "  certbot_conf:" in text


def test_nginx_ssl_template_keeps_acme_http_and_proxies_https():
    text = NGINX_TEMPLATE.read_text(encoding="utf-8")

    assert "listen 80;" in text
    assert "server_name {{DOMAIN}} www.{{DOMAIN}};" in text
    assert "location /.well-known/acme-challenge/" in text
    assert "return 301 https://$host$request_uri;" in text
    assert "listen 443 ssl http2;" in text
    assert "ssl_certificate /etc/letsencrypt/live/{{CERT_NAME}}/fullchain.pem;" in text
    assert "ssl_certificate_key /etc/letsencrypt/live/{{CERT_NAME}}/privkey.pem;" in text
    assert "proxy_pass http://api:8000/;" in text
    assert "proxy_pass http://frontend:80;" in text


def test_setup_letsencrypt_script_uses_webroot_and_renders_template():
    text = TLS_SCRIPT.read_text(encoding="utf-8")

    assert text.startswith("#!/usr/bin/env bash\n")
    assert "set -Eeuo pipefail" in text
    assert "AGARTHA_DOMAIN" in text
    assert "AGARTHA_EMAIL" in text
    assert "certbot certonly" in text
    assert "--webroot-path /var/www/certbot" in text
    assert "--keep-until-expiring" in text
    assert "--staging" in text
    assert "nginx.ssl.conf.template" in text
    assert "nginx -s reload" in text


def test_certbot_renewal_timer_reloads_nginx_after_renewal():
    service = RENEW_SERVICE.read_text(encoding="utf-8")
    timer = RENEW_TIMER.read_text(encoding="utf-8")

    assert "certbot renew" in service
    assert "--webroot-path /var/www/certbot" in service
    assert "ExecStartPost=/usr/bin/docker compose exec -T nginx nginx -s reload" in service
    assert "OnCalendar=*-*-* 03,15:17:00" in timer
    assert "RandomizedDelaySec=1h" in timer
    assert "Persistent=true" in timer
