# gRPC-Applications
Create installable gRPC applications

## Shared Apache 443 Host

This repo includes a shared Apache `443` virtual host for serving these three applications behind one hostname:

- `chat-service` at `/chat-service/`
- `stock-ticker-service` at `/stock-ticker/`
- `job-orchestrator-service` at `/job-orchestrator/`

Use the shared hostname:

```text
grpc-service-apache-origin.qa.akamai.com
```

Deployment assets:

- Apache vhost: `deploy/apache-grpc-services-443.conf`
- Self-signed cert helper: `deploy/create-grpc-services-cert.sh`

Example Ubuntu steps:

```bash
cd /path/to/gRPC-Applications
chmod +x deploy/create-grpc-services-cert.sh
sudo ./deploy/create-grpc-services-cert.sh grpc-service-apache-origin.qa.akamai.com

sudo a2enmod ssl proxy proxy_http proxy_http2 headers
sudo cp deploy/apache-grpc-services-443.conf /etc/apache2/sites-available/grpc-services.conf
sudo a2ensite grpc-services.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Expected browser URLs:

```text
https://grpc-service-apache-origin.qa.akamai.com/chat-service/
https://grpc-service-apache-origin.qa.akamai.com/stock-ticker/
https://grpc-service-apache-origin.qa.akamai.com/job-orchestrator/
```

Expected gRPC endpoints:

```text
chat.ChatService
stockticker.StockTickerService
joborchestrator.JobOrchestrator
```

Note: generic reflection and gRPC health paths are not routed in the shared Apache config because those well-known paths collide when multiple backends share one hostname and port.
