# ==============================================================================
# Security Best Practices for Production Deployment
# ==============================================================================

## Secrets Management

### DO NOT commit .env to version control
# The .env file contains sensitive credentials including:
# - API keys (Google Gemini, OpenAI, HuggingFace)
# - Database passwords
# - Grafana passwords

### Use a secrets manager in production
# Options:
# - AWS Secrets Manager
# - Azure Key Vault  
# - Google Secret Manager
# - HashiCorp Vault
# - Docker Secrets (for Docker Swarm)

### Example: Using Docker Secrets (Swarm mode)
# 1. Create secrets:
#    echo "your_password" | docker secret create postgres_password -
#    echo "your_api_key" | docker secret create google_api_key -
#
# 2. Reference in docker-compose.yml:
#    services:
#      backend:
#        secrets:
#          - google_api_key
#          - postgres_password
#        environment:
#          GOOGLE_API_KEY_FILE: /run/secrets/google_api_key
#          POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
#
# 3. Update backend code to read from files:
#    with open(os.getenv('GOOGLE_API_KEY_FILE'), 'r') as f:
#        api_key = f.read().strip()

## HTTPS/TLS Configuration

### Use a reverse proxy for SSL termination
# Recommended: Nginx, Traefik, or Caddy in front of the application

### Example: Nginx with Let's Encrypt
# 1. Install certbot:
#    apt-get install certbot python3-certbot-nginx
#
# 2. Get certificate:
#    certbot --nginx -d yourdomain.com
#
# 3. Update nginx.conf:
#    server {
#        listen 443 ssl http2;
#        server_name yourdomain.com;
#        
#        ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
#        ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
#        
#        # Strong SSL configuration
#        ssl_protocols TLSv1.2 TLSv1.3;
#        ssl_ciphers HIGH:!aNULL:!MD5;
#        ssl_prefer_server_ciphers on;
#        
#        location / {
#            proxy_pass http://localhost:80;
#        }
#    }

### Example: docker-compose with Traefik
# See: https://doc.traefik.io/traefik/user-guides/docker-compose/acme-http/

## Network Security

### Use internal network for backend services
# Already configured in docker-compose.yml:
# - postgres, backend, vllm on internal network
# - Only frontend exposed on port 80

### Firewall rules
# Configure UFW (Ubuntu) or firewalld (CentOS):
#   ufw allow 80/tcp    # HTTP
#   ufw allow 443/tcp   # HTTPS
#   ufw allow 22/tcp    # SSH (limit rate)
#   ufw deny 5432/tcp   # Block PostgreSQL from external access
#   ufw enable

## Database Security

### Strong password generation
# openssl rand -base64 32
# or
# python -c "import secrets; print(secrets.token_urlsafe(32))"

### Regular backups
# Use the backup script:
#   make backup
# Or set up automated backups via cron:
#   0 2 * * * cd /path/to/app && make backup

### Enable SSL for PostgreSQL connections (if across network)
# In docker-compose.yml:
#   postgres:
#     environment:
#       POSTGRES_SSL_MODE: require
#     volumes:
#       - ./certs/server-cert.pem:/var/lib/postgresql/server.crt:ro
#       - ./certs/server-key.pem:/var/lib/postgresql/server.key:ro

## API Security

### Rate Limiting
# Already configured in nginx.conf:
# - 20 requests/minute per IP for /api/*
# - Burst of 5 allowed

### Adjust based on your needs:
# frontend/nginx.conf:
#   limit_req_zone $binary_remote_addr zone=chat_zone:10m rate=20r/m;

### CORS Configuration
# Already configured in backend/main.py
# Update FRONTEND_ORIGIN in .env to match your domain:
#   FRONTEND_ORIGIN=https://yourdomain.com

## Container Security

### Run as non-root user
# Add to Dockerfile:
#   RUN adduser --disabled-password --gecos '' appuser
#   USER appuser

### Security options (already enabled in docker-compose.yml)
# - no-new-privileges:true
# - Resource limits (memory, CPU)
# - Read-only root filesystem (where applicable)

### Scan images for vulnerabilities
# docker scan backend:latest
# or use Trivy:
#   trivy image backend:latest

## Monitoring & Alerting

### Enable monitoring
# make monitor
# Access Grafana at http://localhost:3000

### Set up alerts
# In Grafana:
# - High error rate
# - Database connection failures
# - High latency
# - Resource exhaustion

### Log aggregation
# Forward logs to centralized logging:
# - ELK Stack (Elasticsearch, Logstash, Kibana)
# - Splunk
# - CloudWatch (AWS)
# - Stackdriver (GCP)

## Regular Security Tasks

### Daily
# - Review logs for anomalies
# - Check health endpoints

### Weekly  
# - Review access logs
# - Check for failed login attempts
# - Review API usage patterns

### Monthly
# - Update base images: make update
# - Rotate credentials
# - Review firewall rules
# - Test backup restoration

### Quarterly
# - Security audit
# - Penetration testing
# - Dependency updates
# - Review and update security policies

## Compliance Checklist

### Before Production Launch
- [ ] All default passwords changed
- [ ] .env file not in version control
- [ ] HTTPS enabled
- [ ] Firewall configured
- [ ] Rate limiting tested
- [ ] CORS properly configured
- [ ] Database backups automated
- [ ] Monitoring enabled
- [ ] Log aggregation configured
- [ ] Security headers verified (X-Frame-Options, CSP, etc.)
- [ ] Dependency vulnerabilities scanned
- [ ] Resource limits configured
- [ ] Error messages don't leak sensitive info
- [ ] API endpoints authenticated (if required)
- [ ] Regular backup tested and verified

## Incident Response

### If credentials are compromised:
# 1. Immediately rotate all affected credentials
# 2. Review access logs for unauthorized access
# 3. Check for data exfiltration
# 4. Update .env and redeploy:
#    make deploy

### If system is breached:
# 1. Isolate affected systems
# 2. Preserve evidence (logs, disk images)
# 3. Restore from known-good backup
# 4. Perform security audit
# 5. Update security measures

## References

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Docker Security Best Practices: https://docs.docker.com/develop/security-best-practices/
- CIS Docker Benchmark: https://www.cisecurity.org/benchmark/docker
- Nginx Security: https://www.nginx.com/blog/nginx-security-best-practices/
