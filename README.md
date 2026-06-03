# gRPC-Applications
Create installable gRPC applications

## Shared Apache 443 Host

This repo includes a shared Apache `443` virtual host for serving these applications behind one hostname:

- `chat-service` at `/chat-service/`
- `stock-ticker-service` at `/stock-ticker/`
- `job-orchestrator-service` at `/job-orchestrator/`
- `grpcbin` gRPC test services proxied directly by service path to `127.0.0.1:50054`

Use the shared hostname:

```text
grpc-service-apache-origin.qa.akamai.com
```

Deployment assets:

- Apache vhost: `deploy/apache-grpc-services-443.conf`
- Self-signed cert helper: `deploy/create-grpc-services-cert.sh`
- grpcbin systemd unit: `gRPC-BIN/grpcbin.service`
- grpcbin installer: `gRPC-BIN/install-grpcbin.sh`

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

Install grpcbin on Ubuntu:

```bash
cd /path/to/gRPC-Applications
chmod +x gRPC-BIN/install-grpcbin.sh
sudo ./gRPC-BIN/install-grpcbin.sh
sudo systemctl status grpcbin --no-pager
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
grpcbin.GRPCBin
hello.HelloService
addsvc.Add
grpc.gateway.examples.examplepb.ABitOfEverythingService
```

Note: generic reflection and gRPC health paths are not routed in the shared Apache config because those well-known paths collide when multiple backends share one hostname and port.

Example grpcurl calls through Apache `443`:

```bash
grpcurl -insecure \
	-d '{}' \
	grpc-service-apache-origin.qa.akamai.com:443 \
	grpcbin.GRPCBin/Index

grpcurl -insecure \
	-proto <(curl -fsSL https://raw.githubusercontent.com/moul/pb/master/hello/hello.proto) \
	-d '{"greeting":"hello"}' \
	grpc-service-apache-origin.qa.akamai.com:443 \
	hello.HelloService/SayHello
```

grpcbin deployment note: upstream `grpcbin` always starts both an insecure listener and a TLS listener. The provided installer in `gRPC-BIN/` binds the h2c backend to `127.0.0.1:50054`, binds the required TLS listener to `127.0.0.1:50056`, and generates a local self-signed certificate under `/opt/grpcbin/cert/` so the systemd service can start cleanly.
