package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"sync"
	"time"

	pb "github.com/grpc-applications/chat-service/pkg"
	"google.golang.org/grpc"
)

// subscriber holds a channel for streaming messages to a connected client
type subscriber struct {
	username string
	ch       chan *pb.Message
}

// chatRoom holds the state for a single chat room
type chatRoom struct {
	mu          sync.Mutex
	info        *pb.Room
	users       map[string]int64 // username -> joined_at unix nano
	subscribers []*subscriber
}

func (r *chatRoom) broadcast(msg *pb.Message) {
	r.mu.Lock()
	defer r.mu.Unlock()
	for _, s := range r.subscribers {
		select {
		case s.ch <- msg:
		default:
		}
	}
}

// ChatServer implements the ChatService
type ChatServer struct {
	pb.UnimplementedChatServiceServer
	mu    sync.Mutex
	rooms map[string]*chatRoom
}

func NewChatServer() *ChatServer {
	return &ChatServer{rooms: make(map[string]*chatRoom)}
}

func (s *ChatServer) getOrCreate(roomID string) *chatRoom {
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.rooms[roomID]
	if !ok {
		r = &chatRoom{
			info:  &pb.Room{RoomId: roomID, Name: roomID},
			users: make(map[string]int64),
		}
		s.rooms[roomID] = r
	}
	return r
}

// JoinRoom — server-streaming: client joins and receives a live message stream
func (s *ChatServer) JoinRoom(req *pb.JoinRoomRequest, stream pb.ChatService_JoinRoomServer) error {
	r := s.getOrCreate(req.RoomId)

	sub := &subscriber{username: req.Username, ch: make(chan *pb.Message, 100)}

	r.mu.Lock()
	r.subscribers = append(r.subscribers, sub)
	r.users[req.Username] = time.Now().UnixNano()
	r.info.UserCount = int32(len(r.users))
	r.mu.Unlock()

	r.broadcast(&pb.Message{
		MessageId: fmt.Sprintf("sys_%d", time.Now().UnixNano()),
		RoomId:    req.RoomId,
		Username:  req.Username,
		Content:   req.Username + " joined the room",
		Timestamp: time.Now().Unix(),
		Type:      pb.MessageType_USER_JOINED,
	})

	defer func() {
		r.mu.Lock()
		filtered := r.subscribers[:0]
		for _, existing := range r.subscribers {
			if existing != sub {
				filtered = append(filtered, existing)
			}
		}
		r.subscribers = filtered
		delete(r.users, req.Username)
		r.info.UserCount = int32(len(r.users))
		r.mu.Unlock()
		close(sub.ch)

		r.broadcast(&pb.Message{
			MessageId: fmt.Sprintf("sys_%d", time.Now().UnixNano()),
			RoomId:    req.RoomId,
			Username:  req.Username,
			Content:   req.Username + " left the room",
			Timestamp: time.Now().Unix(),
			Type:      pb.MessageType_USER_LEFT,
		})
	}()

	for {
		select {
		case msg, ok := <-sub.ch:
			if !ok {
				return nil
			}
			if err := stream.Send(msg); err != nil {
				return err
			}
		case <-stream.Context().Done():
			return stream.Context().Err()
		}
	}
}

// SendMessage — unary: broadcast a message to all room subscribers
func (s *ChatServer) SendMessage(_ context.Context, req *pb.SendMessageRequest) (*pb.SendMessageResponse, error) {
	r := s.getOrCreate(req.RoomId)
	msgID := fmt.Sprintf("msg_%d", time.Now().UnixNano())
	r.broadcast(&pb.Message{
		MessageId: msgID,
		RoomId:    req.RoomId,
		Username:  req.Username,
		Content:   req.Content,
		Timestamp: time.Now().Unix(),
		Type:      pb.MessageType_USER_MESSAGE,
	})
	return &pb.SendMessageResponse{Success: true, MessageId: msgID}, nil
}

// LeaveRoom — unary: remove a user from a room
func (s *ChatServer) LeaveRoom(_ context.Context, req *pb.LeaveRoomRequest) (*pb.LeaveRoomResponse, error) {
	s.mu.Lock()
	r, ok := s.rooms[req.RoomId]
	s.mu.Unlock()
	if !ok {
		return &pb.LeaveRoomResponse{Success: false}, nil
	}
	r.mu.Lock()
	delete(r.users, req.Username)
	r.info.UserCount = int32(len(r.users))
	r.mu.Unlock()
	r.broadcast(&pb.Message{
		MessageId: fmt.Sprintf("sys_%d", time.Now().UnixNano()),
		RoomId:    req.RoomId,
		Username:  req.Username,
		Content:   req.Username + " left the room",
		Timestamp: time.Now().Unix(),
		Type:      pb.MessageType_USER_LEFT,
	})
	return &pb.LeaveRoomResponse{Success: true}, nil
}

// GetRooms — unary: return all active rooms
func (s *ChatServer) GetRooms(_ context.Context, _ *pb.GetRoomsRequest) (*pb.GetRoomsResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	rooms := make([]*pb.Room, 0, len(s.rooms))
	for _, r := range s.rooms {
		r.mu.Lock()
		rooms = append(rooms, r.info)
		r.mu.Unlock()
	}
	return &pb.GetRoomsResponse{Rooms: rooms}, nil
}

// GetRoomUsers — unary: return users in a room
func (s *ChatServer) GetRoomUsers(_ context.Context, req *pb.GetRoomUsersRequest) (*pb.GetRoomUsersResponse, error) {
	s.mu.Lock()
	r, ok := s.rooms[req.RoomId]
	s.mu.Unlock()
	if !ok {
		return &pb.GetRoomUsersResponse{Users: []*pb.User{}}, nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	users := make([]*pb.User, 0, len(r.users))
	for username, joinedAt := range r.users {
		users = append(users, &pb.User{Username: username, JoinedAt: joinedAt})
	}
	return &pb.GetRoomUsersResponse{Users: users}, nil
}

func main() {
	listener, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	grpcServer := grpc.NewServer()
	pb.RegisterChatServiceServer(grpcServer, NewChatServer())
	log.Println("Chat Service Server listening on :50051")
	if err := grpcServer.Serve(listener); err != nil {
		log.Fatalf("failed to serve: %v", err)
	}
}


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
