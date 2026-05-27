package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"time"

	pb "github.com/grpc-applications/chat-service/pkg"
	"google.golang.org/grpc"
)

// ChatServer implements the ChatService
type ChatServer struct {
	pb.UnimplementedChatServiceServer
	rooms    map[string]*pb.Room
	messages map[string][]*pb.Message
}

// NewChatServer creates a new chat server
func NewChatServer() *ChatServer {
	return &ChatServer{
		rooms:    make(map[string]*pb.Room),
		messages: make(map[string][]*pb.Message),
	}
}

// GetRoom retrieves a specific room by ID
func (s *ChatServer) GetRoom(ctx context.Context, req *pb.GetRoomRequest) (*pb.GetRoomResponse, error) {
	room, ok := s.rooms[req.RoomId]
	if !ok {
		return &pb.GetRoomResponse{
			Status: "error",
			Room:   nil,
		}, nil
	}
	return &pb.GetRoomResponse{
		Status: "success",
		Room:   room,
	}, nil
}

// ListRooms retrieves all available rooms
func (s *ChatServer) ListRooms(ctx context.Context, req *pb.ListRoomsRequest) (*pb.ListRoomsResponse, error) {
	var rooms []*pb.Room
	for _, room := range s.rooms {
		rooms = append(rooms, room)
	}

	// Apply limit and offset
	start := int(req.Offset)
	end := start + int(req.Limit)
	if req.Limit == 0 {
		end = len(rooms)
	}
	if start > len(rooms) {
		start = len(rooms)
	}
	if end > len(rooms) {
		end = len(rooms)
	}

	var paginatedRooms []*pb.Room
	if start < end {
		paginatedRooms = rooms[start:end]
	}

	return &pb.ListRoomsResponse{
		Rooms: paginatedRooms,
		Total: int32(len(rooms)),
	}, nil
}

// CreateRoom creates a new chat room
func (s *ChatServer) CreateRoom(ctx context.Context, req *pb.CreateRoomRequest) (*pb.CreateRoomResponse, error) {
	roomID := fmt.Sprintf("room_%d", time.Now().UnixNano())
	room := &pb.Room{
		Id:          roomID,
		Name:        req.Name,
		Description: req.Description,
		MemberCount: 0,
		CreatedAt:   time.Now().String(),
	}
	s.rooms[roomID] = room
	s.messages[roomID] = make([]*pb.Message, 0)

	return &pb.CreateRoomResponse{
		Status: "success",
		Room:   room,
	}, nil
}

// SendMessage sends a message to a room
func (s *ChatServer) SendMessage(ctx context.Context, req *pb.SendMessageRequest) (*pb.SendMessageResponse, error) {
	if _, ok := s.rooms[req.RoomId]; !ok {
		return &pb.SendMessageResponse{
			Status: "error",
		}, nil
	}

	msgID := fmt.Sprintf("msg_%d", time.Now().UnixNano())
	message := &pb.Message{
		Id:        msgID,
		RoomId:    req.RoomId,
		Sender:    req.Sender,
		Content:   req.Content,
		Timestamp: time.Now().String(),
	}

	s.messages[req.RoomId] = append(s.messages[req.RoomId], message)

	return &pb.SendMessageResponse{
		Status:  "success",
		Message: message,
	}, nil
}

// GetMessages retrieves messages from a room
func (s *ChatServer) GetMessages(ctx context.Context, req *pb.GetMessagesRequest) (*pb.GetMessagesResponse, error) {
	roomID := req.RoomId
	messages, ok := s.messages[roomID]
	if !ok {
		return &pb.GetMessagesResponse{
			Messages: make([]*pb.Message, 0),
			Total:    0,
		}, nil
	}

	// Apply limit
	limit := int(req.Limit)
	if limit == 0 || limit > len(messages) {
		limit = len(messages)
	}

	paginatedMessages := messages[len(messages)-limit:]

	return &pb.GetMessagesResponse{
		Messages: paginatedMessages,
		Total:    int32(len(messages)),
	}, nil
}

// DeleteRoom deletes a room
func (s *ChatServer) DeleteRoom(ctx context.Context, req *pb.DeleteRoomRequest) (*pb.DeleteRoomResponse, error) {
	if _, ok := s.rooms[req.RoomId]; !ok {
		return &pb.DeleteRoomResponse{
			Status:  "error",
			Message: "room not found",
		}, nil
	}

	delete(s.rooms, req.RoomId)
	delete(s.messages, req.RoomId)

	return &pb.DeleteRoomResponse{
		Status:  "success",
		Message: "room deleted successfully",
	}, nil
}

func main() {
	// Listen on port 50051
	listener, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}

	// Create gRPC server
	grpcServer := grpc.NewServer()

	// Register chat service
	chatServer := NewChatServer()
	pb.RegisterChatServiceServer(grpcServer, chatServer)

	log.Println("Chat Service Server listening on :50051")

	// Start server
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}
