package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	pb "github.com/grpc-applications/chat-service/pkg"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

var grpcAddr = "localhost:50051"

func newClient() (pb.ChatServiceClient, *grpc.ClientConn, error) {
	conn, err := grpc.Dial(grpcAddr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, nil, err
	}
	return pb.NewChatServiceClient(conn), conn, nil
}

func cors(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next(w, r)
	}
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(v)
}

// GET /api/rooms
func getRooms(w http.ResponseWriter, r *http.Request) {
	client, conn, err := newClient()
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := client.GetRooms(ctx, &pb.GetRoomsRequest{})
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, 200, resp)
}

// GET /api/rooms/{id}/users
func getRoomUsers(w http.ResponseWriter, r *http.Request) {
	roomID := r.PathValue("id")
	client, conn, err := newClient()
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := client.GetRoomUsers(ctx, &pb.GetRoomUsersRequest{RoomId: roomID})
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, 200, resp)
}

// POST /api/messages  body: {room_id, username, content}
func sendMessage(w http.ResponseWriter, r *http.Request) {
	var req pb.SendMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, 400, map[string]string{"error": "invalid JSON"})
		return
	}
	client, conn, err := newClient()
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := client.SendMessage(ctx, &req)
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, 200, resp)
}

// POST /api/rooms/leave  body: {room_id, username}
func leaveRoom(w http.ResponseWriter, r *http.Request) {
	var req pb.LeaveRoomRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, 400, map[string]string{"error": "invalid JSON"})
		return
	}
	client, conn, err := newClient()
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	defer conn.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	resp, err := client.LeaveRoom(ctx, &req)
	if err != nil {
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, 200, resp)
}

// GET /api/rooms/join?room_id=x&username=y  — SSE stream
func joinRoom(w http.ResponseWriter, r *http.Request) {
	roomID := r.URL.Query().Get("room_id")
	username := r.URL.Query().Get("username")
	if roomID == "" || username == "" {
		writeJSON(w, 400, map[string]string{"error": "room_id and username required"})
		return
	}

	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", 500)
		return
	}

	client, conn, err := newClient()
	if err != nil {
		fmt.Fprintf(w, "event: error\ndata: %s\n\n", err.Error())
		flusher.Flush()
		return
	}
	defer conn.Close()

	stream, err := client.JoinRoom(r.Context(), &pb.JoinRoomRequest{
		RoomId:   roomID,
		Username: username,
	})
	if err != nil {
		fmt.Fprintf(w, "event: error\ndata: %s\n\n", err.Error())
		flusher.Flush()
		return
	}

	for {
		msg, err := stream.Recv()
		if err == io.EOF || r.Context().Err() != nil {
			break
		}
		if err != nil {
			fmt.Fprintf(w, "event: error\ndata: %s\n\n", err.Error())
			flusher.Flush()
			break
		}
		data, _ := json.Marshal(msg)
		fmt.Fprintf(w, "data: %s\n\n", data)
		flusher.Flush()
	}
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/rooms", cors(getRooms))
	mux.HandleFunc("GET /api/rooms/join", cors(joinRoom))
	mux.HandleFunc("GET /api/rooms/{id}/users", cors(getRoomUsers))
	mux.HandleFunc("POST /api/messages", cors(sendMessage))
	mux.HandleFunc("POST /api/rooms/leave", cors(leaveRoom))
	mux.Handle("/", http.FileServer(http.Dir("/opt/chat-service/web")))

	log.Println("Web bridge listening on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatal(err)
	}
}
