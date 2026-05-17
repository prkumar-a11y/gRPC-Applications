package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"

	pb "github.com/prkumar-a11y/gRPC-Applications/hello-world/pkg"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/reflection"
)

var (
	port    = flag.Int("port", 50051, "The server port")
	tlsFlag = flag.Bool("tls", false, "Enable TLS")
	cert    = flag.String("cert", "server.crt", "TLS certificate file")
	key     = flag.String("key", "server.key", "TLS private key file")
)

// Server is used to implement helloworld.GreeterServer
type Server struct {
	pb.UnimplementedGreeterServer
}

// SayHello implements helloworld.GreeterServer
func (s *Server) SayHello(ctx context.Context, in *pb.HelloRequest) (*pb.HelloReply, error) {
	log.Printf("Received: %v", in.GetName())
	return &pb.HelloReply{Message: "Hello " + in.GetName()}, nil
}

func main() {
	flag.Parse()
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	var opts []grpc.ServerOption
	if *tlsFlag {
		creds, err := credentials.NewServerTLSFromFile(*cert, *key)
		if err != nil {
			log.Fatalf("failed to load TLS credentials: %v", err)
		}
		opts = append(opts, grpc.Creds(creds))
	}

	s := grpc.NewServer(opts...)
	pb.RegisterGreeterServer(s, &Server{})
	reflection.Register(s)
	log.Printf("server listening at %v (tls=%v)", lis.Addr(), *tlsFlag)
	if err := s.Serve(lis); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
