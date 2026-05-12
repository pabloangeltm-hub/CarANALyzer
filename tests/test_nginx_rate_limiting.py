from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONF = ROOT / "nginx.conf"
SSL_TEMPLATE = ROOT / "deploy" / "nginx" / "nginx.ssl.conf.template"


def _text(path):
    return path.read_text(encoding="utf-8")


def _assert_rate_limits(text):
    assert "limit_req_zone $binary_remote_addr zone=agartha_api:10m rate=10r/s;" in text
    assert "limit_req_zone $binary_remote_addr zone=agartha_auth:10m rate=2r/s;" in text
    assert "limit_req_status 429;" in text
    assert "location /api/auth/" in text
    assert "limit_req zone=agartha_auth burst=10 nodelay;" in text
    assert "proxy_pass http://api:8000/auth/;" in text
    assert "location /api/" in text
    assert "limit_req zone=agartha_api burst=30 nodelay;" in text
    assert "proxy_pass http://api:8000/;" in text


def test_http_nginx_config_has_api_and_auth_rate_limits():
    _assert_rate_limits(_text(NGINX_CONF))


def test_ssl_nginx_template_keeps_same_rate_limits():
    _assert_rate_limits(_text(SSL_TEMPLATE))


def test_acme_challenge_is_not_rate_limited():
    for path in (NGINX_CONF, SSL_TEMPLATE):
        text = _text(path)
        acme_block = text.split("location /.well-known/acme-challenge/", 1)[1].split("}", 1)[0]
        assert "limit_req" not in acme_block
