#!/bin/bash
set -euo pipefail

# ============================================================================
# Generate mTLS certificates for magma-cycling MCP server
#
# Usage: ./generate-certs.sh [output_dir] [nas_ip]
#   output_dir  — default: ~/.magma-certs
#   nas_ip      — default: 192.168.1.78
#
# Output:
#   ca.crt, ca.key          — Certificate Authority (EC P-256, 10 years)
#   server.crt, server.key  — Server cert with SAN (825 days)
#   client.crt, client.key  — Client cert for Mac (825 days)
# ============================================================================

CERTS_DIR="${1:-$HOME/.magma-certs}"
NAS_IP="${2:-192.168.1.78}"

mkdir -p "$CERTS_DIR"
cd "$CERTS_DIR"

echo "=== Generating CA (EC P-256, 10 years) ==="
openssl ecparam -genkey -name prime256v1 -noout -out ca.key
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 \
    -subj "/CN=magma-cycling-ca/O=magma-cycling"

echo "=== Generating Server Certificate (825 days) ==="
openssl ecparam -genkey -name prime256v1 -noout -out server.key

cat > _server-ext.cnf <<EOF
[req]
distinguished_name = req_dn
req_extensions = v3_req
prompt = no

[req_dn]
CN = magma-nas
O = magma-cycling

[v3_req]
subjectAltName = IP:${NAS_IP},DNS:magma-nas
EOF

openssl req -new -key server.key -out _server.csr -config _server-ext.cnf
openssl x509 -req -in _server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 825 \
    -extfile _server-ext.cnf -extensions v3_req

echo "=== Generating Client Certificate (825 days) ==="
openssl ecparam -genkey -name prime256v1 -noout -out client.key
openssl req -new -key client.key -out _client.csr \
    -subj "/CN=magma-mac-client/O=magma-cycling"
openssl x509 -req -in _client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days 825

# Cleanup temp files
rm -f _server.csr _client.csr _server-ext.cnf ca.srl

# Restrict permissions on private keys
chmod 600 ca.key server.key client.key
chmod 644 ca.crt server.crt client.crt

echo ""
echo "=== Certificates generated in ${CERTS_DIR} ==="
echo ""
echo "  CA:     ca.crt, ca.key"
echo "  Server: server.crt, server.key"
echo "  Client: client.crt, client.key"
echo ""
echo "Next steps:"
echo "  1. Copy ca.crt, server.crt, server.key to NAS (scp to ${NAS_IP})"
echo "  2. Keep ca.crt, client.crt, client.key on this Mac"
echo "  3. Set MTLS_CERTS_PATH on NAS Portainer to the server certs directory"
echo "  4. NEVER commit private keys (.key files) to git"
