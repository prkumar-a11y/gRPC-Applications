# Chat Service - Unary gRPC Application

A simple chat service application built with Go and gRPC featuring unary RPCs for room and message management.

## Features

- **GetRoom**: Retrieve a specific chat room by ID
- **ListRooms**: Get all available chat rooms with pagination
- **CreateRoom**: Create a new chat room
- **SendMessage**: Send a message to a room
- **GetMessages**: Retrieve messages from a room
- **DeleteRoom**: Delete a chat room

## Project Structure

```
chat-service/
├── proto/
│   └── chat.proto              # Protocol Buffer definitions
├── pkg/
│   ├── chat.pb.go              # Generated protobuf code
│   └── chat_grpc.pb.go          # Generated gRPC code
├── cmd/
│   ├── server/
│   │   └── main.go             # Server implementation
│   └── client/
│       └── main.go             # Client implementation
├── go.mod                       # Go module file
├── Makefile                     # Build and run tasks
└── README.md                    # This file
```

## Prerequisites

- Go 1.21 or higher
- Protocol Buffer compiler (protoc) v3.21.0 or higher
- gRPC tools

## Installation

```bash
# Clone or download the project
cd chat-service

# Download dependencies
go mod download
```

## Building

```bash
# Build server
go build -o server ./cmd/server

# Build client
go build -o client ./cmd/client
```

Or use the Makefile:

```bash
make build-server
make build-client
make build  # Build both
```

## Running

### Start Server

```bash
go run ./cmd/server/main.go
```

The server will listen on `localhost:50051`

### Run Client

In a separate terminal:

```bash
# Run demo
go run ./cmd/client/main.go

# Or run specific commands
go run ./cmd/client/main.go create-room "General" "General discussion"
go run ./cmd/client/main.go list-rooms
go run ./cmd/client/main.go get-room room_123
go run ./cmd/client/main.go send-message room_123 Alice "Hello!"
go run ./cmd/client/main.go get-messages room_123 10
go run ./cmd/client/main.go delete-room room_123
```

## Protocol Buffers

To regenerate the protobuf files from `proto/chat.proto`:

```bash
protoc --go_out=pkg --go-grpc_out=pkg proto/chat.proto
```

## API Overview

### Messages

- `Room`: Represents a chat room with ID, name, description, member count, and creation time
- `Message`: Represents a chat message with ID, room ID, sender, content, and timestamp
- `User`: Represents a user profile (extensible for future use)

### Service Methods

All methods are unary RPC calls:

1. **GetRoom(GetRoomRequest) -> GetRoomResponse**
   - Retrieves a specific room by its ID

2. **ListRooms(ListRoomsRequest) -> ListRoomsResponse**
   - Retrieves all rooms with pagination support (limit and offset)

3. **CreateRoom(CreateRoomRequest) -> CreateRoomResponse**
   - Creates a new chat room with name and description

4. **SendMessage(SendMessageRequest) -> SendMessageResponse**
   - Sends a message to a room

5. **GetMessages(GetMessagesRequest) -> GetMessagesResponse**
   - Retrieves messages from a room with limit parameter

6. **DeleteRoom(DeleteRoomRequest) -> DeleteRoomResponse**
   - Deletes a room and its associated messages

## Example Usage

```go
package main

import (
    "context"
    pb "github.com/grpc-applications/chat-service/pkg"
    "google.golang.org/grpc"
)

func main() {
    conn, _ := grpc.Dial("localhost:50051")
    defer conn.Close()
    
    client := pb.NewChatServiceClient(conn)
    
    // Create a room
    resp, _ := client.CreateRoom(context.Background(), &pb.CreateRoomRequest{
        Name:        "My Room",
        Description: "A test room",
    })
    
    roomID := resp.Room.Id
    
    // Send a message
    client.SendMessage(context.Background(), &pb.SendMessageRequest{
        RoomId:  roomID,
        Sender:  "Alice",
        Content: "Hello World!",
    })
    
    // List rooms
    rooms, _ := client.ListRooms(context.Background(), &pb.ListRoomsRequest{
        Limit:  10,
        Offset: 0,
    })
}
```

## Testing

```bash
# In one terminal, run the server
go run ./cmd/server/main.go

# In another terminal, run the client demo
go run ./cmd/client/main.go
```

## Notes

- The server stores data in-memory, so data is lost when the server restarts
- This is a demonstration of unary gRPC calls; for production use, consider adding persistent storage
- The application uses insecure communication (no TLS); for production, enable TLS

## License

MIT
