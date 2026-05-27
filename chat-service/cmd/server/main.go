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
