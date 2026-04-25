#!/bin/sh
set -e

apk add --no-cache openssl >/dev/null 2>&1

openssl req -new -nodes \
  -keyout /etc/nginx/tls/server.key \
  -out /tmp/server.csr \
  -subj "/CN=mcp-tls"

openssl x509 -req -in /tmp/server.csr \
  -CA /etc/nginx/ca/ca-cert.pem \
  -CAkey /etc/nginx/ca/ca-key.pem \
  -CAcreateserial \
  -out /etc/nginx/tls/server.crt \
  -days 365 \
  -extfile /dev/stdin <<EOF
subjectAltName = DNS:mcp-tls
EOF

rm -f /tmp/server.csr

exec nginx -g 'daemon off;'
