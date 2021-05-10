#!/bin/sh
# vim:sw=4:ts=4:et

set -e

LC_ALL=C
ME=$( basename "$0" )
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

touch /etc/nginx/sites-enabled/dashboard.conf 2>/dev/null || { echo >&2 "$ME: error: can not modify /etc/nginx/sites-enabled/dashboard.conf (read-only file system?)"; exit 0; }
rm /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-enabled/dashboard.conf << EOF
upstream aiohttp {
    # fail_timeout=0 means we always retry an upstream even if it failed
    # to return a good HTTP response

    # Unix domain servers
    server unix:/tmp/dashboard_1.sock fail_timeout=0;
}

server {
    listen 80;
    client_max_body_size 4G;

    location / {
      proxy_set_header Host \$http_host;
      proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
      proxy_redirect off;
      proxy_buffering off;
      proxy_pass http://aiohttp;
    }

    location /static {
      # path for static files
      root /srv/deep-dashboard/deep_dashboard;
    }
}
EOF
