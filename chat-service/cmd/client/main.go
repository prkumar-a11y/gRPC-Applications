package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"time"

	pb "github.com/grpc-applications/chat-service/pkg"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

func main() {
	// Connect to server
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatalf("failed to connect: %v", err)
	}
	defer conn.Close()

	client := pb.NewChatServiceClient(conn)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	// Parse command line arguments
	flag.Parse()
	args := flag.Args()

	if len(args) == 0 {
		runDemo(client, ctx)
		return
	}

	command := args[0]

	switch command {
	case "create-room":
		if len(args) < 3 {
			fmt.Println("Usage: client create-room <name> <description>")
			return
		}
		createRoom(client, ctx, args[1], args[2])

	case "list-rooms":
		listRooms(client, ctx)

	case "get-room":
		if len(args) < 2 {
			fmt.Println("Usage: client get-room <room-id>")
			return
		}
		getRoom(client, ctx, args[1])

	case "send-message":
		if len(args) < 4 {
			fmt.Println("Usage: client send-message <room-id> <sender> <content>")
			return
		}
		sendMessage(client, ctx, args[1], args[2], args[3])

	case "get-messages":
		if len(args) < 2 {
			fmt.Println("Usage: client get-messages <room-id> [limit]")
			return
		}
		limit := int32(10)
		if len(args) > 2 {
			fmt.Sscanf(args[2], "%d", &limit)
		}
		getMessages(client, ctx, args[1], limit)

	case "delete-room":
		if len(args) < 2 {
			fmt.Println("Usage: client delete-room <room-id>")
			return
		}
		deleteRoom(client, ctx, args[1])

	default:
		fmt.Println("Unknown command:", command)
		fmt.Println("Available commands: create-room, list-rooms, get-room, send-message, get-messages, delete-room")
	}
}

func runDemo(client pb.ChatServiceClient, ctx context.Context) {
	fmt.Println("=== Chat Service Demo ===\n")

	// Create rooms
	fmt.Println("1. Creating rooms...")
	room1 := createRoom(client, ctx, "General", "General discussion room")
	room2 := createRoom(client, ctx, "Random", "Random topics")

	// List rooms
	fmt.Println("\n2. Listing rooms...")
	listRooms(client, ctx)

	// Send messages
	fmt.Println("\n3. Sending messages...")
	if room1 != nil {
		sendMessage(client, ctx, room1.Id, "Alice", "Hello everyone!")
		sendMessage(client, ctx, room1.Id, "Bob", "Hi Alice!")
		sendMessage(client, ctx, room1.Id, "Charlie", "Hey guys, what's up?")
	}

	// Get messages
	fmt.Println("\n4. Getting messages from room...")
	if room1 != nil {
		getMessages(client, ctx, room1.Id, 10)
	}

	// Get specific room
	fmt.Println("\n5. Getting specific room...")
	if room1 != nil {
		getRoom(client, ctx, room1.Id)
	}

	// Delete room
	fmt.Println("\n6. Deleting room...")
	if room1 != nil {
		deleteRoom(client, ctx, room1.Id)
	}

	// List rooms again
	fmt.Println("\n7. Listing rooms again...")
	listRooms(client, ctx)
}

func createRoom(client pb.ChatServiceClient, ctx context.Context, name, description string) *pb.Room {
	resp, err := client.CreateRoom(ctx, &pb.CreateRoomRequest{
		Name:        name,
		Description: description,
	})
	if err != nil {
		log.Printf("CreateRoom error: %v\n", err)
		return nil
	}

	fmt.Printf("Room created: ID=%s, Name=%s, Description=%s\n", resp.Room.Id, resp.Room.Name, resp.Room.Description)
	return resp.Room
}

func listRooms(client pb.ChatServiceClient, ctx context.Context) {
	resp, err := client.ListRooms(ctx, &pb.ListRoomsRequest{
		Limit:  10,
		Offset: 0,
	})
	if err != nil {
		log.Printf("ListRooms error: %v\n", err)
		return
	}

	fmt.Printf("Total rooms: %d\n", resp.Total)
	for _, room := range resp.Rooms {
		fmt.Printf("  - ID: %s, Name: %s, Description: %s, Members: %d\n",
			room.Id, room.Name, room.Description, room.MemberCount)
	}
}

func getRoom(client pb.ChatServiceClient, ctx context.Context, roomID string) {
	resp, err := client.GetRoom(ctx, &pb.GetRoomRequest{
		RoomId: roomID,
	})
	if err != nil {
		log.Printf("GetRoom error: %v\n", err)
		return
	}

	if resp.Room == nil {
		fmt.Printf("Room not found: %s\n", roomID)
		return
	}

	fmt.Printf("Room: ID=%s, Name=%s, Description=%s, Members=%d, Created=%s\n",
		resp.Room.Id, resp.Room.Name, resp.Room.Description, resp.Room.MemberCount, resp.Room.CreatedAt)
}

func sendMessage(client pb.ChatServiceClient, ctx context.Context, roomID, sender, content string) {
	resp, err := client.SendMessage(ctx, &pb.SendMessageRequest{
		RoomId:  roomID,
		Sender:  sender,
		Content: content,
	})
	if err != nil {
		log.Printf("SendMessage error: %v\n", err)
		return
	}

	fmt.Printf("Message sent: ID=%s, From=%s, Content=%s\n", resp.Message.Id, resp.Message.Sender, resp.Message.Content)
}

func getMessages(client pb.ChatServiceClient, ctx context.Context, roomID string, limit int32) {
	resp, err := client.GetMessages(ctx, &pb.GetMessagesRequest{
		RoomId: 0, // Note: In the proto, RoomId is int32, but in practice it's used as string via formatting
		Limit:  limit,
	})
	if err != nil {
		log.Printf("GetMessages error: %v\n", err)
		return
	}

	fmt.Printf("Total messages: %d\n", resp.Total)
	for _, msg := range resp.Messages {
		fmt.Printf("  [%s] %s: %s\n", msg.Timestamp, msg.Sender, msg.Content)
	}
}

func deleteRoom(client pb.ChatServiceClient, ctx context.Context, roomID string) {
	resp, err := client.DeleteRoom(ctx, &pb.DeleteRoomRequest{
		RoomId: roomID,
	})
	if err != nil {
		log.Printf("DeleteRoom error: %v\n", err)
		return
	}

	fmt.Printf("Room deleted: Status=%s, Message=%s\n", resp.Status, resp.Message)
}
