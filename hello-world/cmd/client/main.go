package main

import (
	"context"
	"crypto/tls"
	"flag"
	"log"
	"time"

	pb "github.com/prkumar-a11y/gRPC-Applications/hello-world/pkg"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	defaultName = "world"
)

var (
	addr               = flag.String("addr", "localhost:50051", "the address to connect to")
	name               = flag.String("name", defaultName, "Name to greet")
	tlsFlag            = flag.Bool("tls", false, "Enable TLS")
	caCert             = flag.String("ca_cert", "", "CA certificate file for TLS")
	serverNameOverride = flag.String("server_name", "", "Server name for TLS verification")
)

func main() {
	flag.Parse()

	var opts []grpc.DialOption
	if *tlsFlag {
		if *caCert != "" {
			creds, err := credentials.NewClientTLSFromFile(*caCert, *serverNameOverride)
			if err != nil {
				log.Fatalf("failed to load TLS credentials: %v", err)
			}
			opts = append(opts, grpc.WithTransportCredentials(creds))
		} else {
			tlsConfig := &tls.Config{}
			if *serverNameOverride != "" {
				tlsConfig.ServerName = *serverNameOverride
			}
			creds := credentials.NewTLS(tlsConfig)
			opts = append(opts, grpc.WithTransportCredentials(creds))
		}
	} else {
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}

	conn, err := grpc.Dial(*addr, opts...)
	if err != nil {
		log.Fatalf("did not connect: %v", err)
	}
	defer conn.Close()
	c := pb.NewGreeterClient(conn)

	// Contact the server and print out its response.
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	r, err := c.SayHello(ctx, &pb.HelloRequest{Name: *name})
	if err != nil {
		log.Fatalf("could not greet: %v", err)
	}
	log.Printf("Greeting: %s", r.GetMessage())
}
