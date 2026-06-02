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

const indexHTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gRPC Chat Service</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex; flex-direction: column; }

  header { background: #16213e; padding: 12px 20px; display: flex; align-items: center; gap: 12px; border-bottom: 1px solid #0f3460; }
  header h1 { font-size: 1.2rem; color: #e94560; }
  header span { font-size: 0.8rem; color: #888; }
  #status-dot { width: 10px; height: 10px; border-radius: 50%; background: #888; flex-shrink: 0; }
  #status-dot.connected { background: #4caf50; }

  .app { display: flex; flex: 1; overflow: hidden; }

  aside { width: 220px; background: #16213e; border-right: 1px solid #0f3460; display: flex; flex-direction: column; }
  aside h2 { padding: 12px 14px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; border-bottom: 1px solid #0f3460; }
  #room-list { flex: 1; overflow-y: auto; }
  .room-item { padding: 10px 14px; cursor: pointer; font-size: 0.9rem; border-left: 3px solid transparent; }
  .room-item:hover { background: #0f3460; }
  .room-item.active { border-left-color: #e94560; background: #0f3460; color: #fff; }
  .room-item .room-count { font-size: 0.75rem; color: #888; }
  #join-panel { padding: 12px; border-top: 1px solid #0f3460; }
  #join-panel input { width: 100%; padding: 6px 8px; background: #0f3460; border: 1px solid #1a5276; color: #e0e0e0; border-radius: 4px; font-size: 0.85rem; margin-bottom: 6px; }
  #join-panel button { width: 100%; padding: 7px; background: #e94560; border: none; color: #fff; border-radius: 4px; cursor: pointer; font-size: 0.85rem; }
  #join-panel button:hover { background: #c0392b; }

  main { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  #chat-header { padding: 12px 16px; background: #16213e; border-bottom: 1px solid #0f3460; display: flex; align-items: center; justify-content: space-between; }
  #chat-header h3 { font-size: 1rem; }
  #chat-header button { padding: 5px 12px; background: #c0392b; border: none; color: #fff; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }

  #messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
  .msg { max-width: 75%; padding: 8px 12px; border-radius: 8px; font-size: 0.9rem; line-height: 1.4; }
  .msg.self { align-self: flex-end; background: #e94560; color: #fff; }
  .msg.other { align-self: flex-start; background: #0f3460; }
  .msg.system { align-self: center; background: transparent; color: #888; font-style: italic; font-size: 0.8rem; }
  .msg .meta { font-size: 0.72rem; opacity: 0.7; margin-bottom: 2px; }

  #input-bar { padding: 12px 16px; background: #16213e; border-top: 1px solid #0f3460; display: flex; gap: 10px; }
  #input-bar input { flex: 1; padding: 9px 12px; background: #0f3460; border: 1px solid #1a5276; color: #e0e0e0; border-radius: 6px; font-size: 0.9rem; }
  #input-bar input:focus { outline: none; border-color: #e94560; }
  #input-bar button { padding: 9px 18px; background: #e94560; border: none; color: #fff; border-radius: 6px; cursor: pointer; font-weight: 600; }
  #input-bar button:hover { background: #c0392b; }
  #input-bar button:disabled { background: #555; cursor: not-allowed; }

  .users-panel { width: 180px; background: #16213e; border-left: 1px solid #0f3460; display: flex; flex-direction: column; }
  .users-panel h2 { padding: 12px 14px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px; color: #888; border-bottom: 1px solid #0f3460; }
  #user-list { flex: 1; overflow-y: auto; padding: 8px 0; }
  .user-item { padding: 6px 14px; font-size: 0.85rem; display: flex; align-items: center; gap: 8px; }
  .user-item::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: #4caf50; flex-shrink: 0; }
  .user-item.self::before { background: #e94560; }

  #login-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 100; }
  #login-box { background: #16213e; border: 1px solid #0f3460; border-radius: 10px; padding: 32px; width: 320px; }
  #login-box h2 { margin-bottom: 16px; color: #e94560; }
  #login-box input { width: 100%; padding: 9px 12px; background: #0f3460; border: 1px solid #1a5276; color: #e0e0e0; border-radius: 6px; font-size: 0.9rem; margin-bottom: 12px; }
  #login-box button { width: 100%; padding: 10px; background: #e94560; border: none; color: #fff; border-radius: 6px; cursor: pointer; font-size: 1rem; font-weight: 600; }
</style>
</head>
<body>

<div id="login-overlay">
  <div id="login-box">
    <h2>gRPC Chat</h2>
    <input id="username-input" type="text" placeholder="Enter your username" maxlength="30" autofocus>
    <button onclick="setUsername()">Enter Chat</button>
  </div>
</div>

<header>
  <div id="status-dot"></div>
  <h1>gRPC Chat Service</h1>
  <span id="header-user"></span>
</header>

<div class="app">
  <aside>
    <h2>Rooms</h2>
    <div id="room-list"><p style="padding:12px;color:#888;font-size:0.8rem">No rooms yet</p></div>
    <div id="join-panel">
      <input id="new-room-id" type="text" placeholder="Room ID (e.g. lobby)">
      <button onclick="joinRoom()">Join / Create Room</button>
    </div>
  </aside>

  <main>
    <div id="chat-header">
      <h3 id="current-room-name">Select a room</h3>
      <button onclick="leaveRoom()" id="leave-btn" style="display:none">Leave Room</button>
    </div>
    <div id="messages">
      <p class="msg system">Join a room to start chatting</p>
    </div>
    <div id="input-bar">
      <input id="msg-input" type="text" placeholder="Type a message..." disabled onkeydown="if(event.key==='Enter')sendMessage()">
      <button id="send-btn" onclick="sendMessage()" disabled>Send</button>
    </div>
  </main>

  <div class="users-panel">
    <h2>Users</h2>
    <div id="user-list"></div>
  </div>
</div>

<script>
  const BASE_PATH = window.location.pathname.startsWith('/chat-service') ? '/chat-service' : '';
  const API = BASE_PATH + '/api';
  let username = '';
  let currentRoom = '';
  let eventSource = null;

  function setUsername() {
    const val = document.getElementById('username-input').value.trim();
    if (!val) return;
    username = val;
    document.getElementById('login-overlay').style.display = 'none';
    document.getElementById('header-user').textContent = 'User: ' + username;
    loadRooms();
    setInterval(loadRooms, 10000);
  }

  async function loadRooms() {
    try {
      const res = await fetch(API + '/api/rooms');
      const data = await res.json();
      const list = document.getElementById('room-list');
      const rooms = data.rooms || [];
      if (rooms.length === 0) {
        list.innerHTML = '<p style="padding:12px;color:#888;font-size:0.8rem">No rooms yet</p>';
        return;
      }
      list.innerHTML = rooms.map(r =>
        '<div class="room-item ' + (r.room_id === currentRoom ? 'active' : '') + '" onclick="switchRoom(\'' + r.room_id + '\')">' +
        '<div>' + r.name + '</div>' +
        '<div class="room-count">' + (r.user_count || 0) + ' user(s)</div>' +
        '</div>'
      ).join('');
    } catch(e) { console.error('loadRooms:', e); }
  }

  function switchRoom(roomId) {
    if (roomId === currentRoom) return;
    if (currentRoom) leaveRoom(false);
    joinRoom(roomId);
  }

  async function joinRoom(roomId) {
    const id = roomId || document.getElementById('new-room-id').value.trim();
    if (!id || !username) return;
    document.getElementById('new-room-id').value = '';
    currentRoom = id;
    document.getElementById('current-room-name').textContent = '# ' + id;
    document.getElementById('leave-btn').style.display = '';
    document.getElementById('msg-input').disabled = false;
    document.getElementById('send-btn').disabled = false;
    document.getElementById('messages').innerHTML = '';

    if (eventSource) eventSource.close();
    const url = API + '/api/rooms/join?room_id=' + encodeURIComponent(id) + '&username=' + encodeURIComponent(username);
    eventSource = new EventSource(url);
    document.getElementById('status-dot').className = 'connected';
    eventSource.onmessage = function(e) {
      const msg = JSON.parse(e.data);
      appendMessage(msg);
      loadUsers();
    };
    eventSource.onerror = function() {
      document.getElementById('status-dot').className = '';
    };
    await loadRooms();
    await loadUsers();
  }

  async function leaveRoom(doLeave) {
    if (doLeave === undefined) doLeave = true;
    if (!currentRoom) return;
    if (doLeave) {
      try {
        await fetch(API + '/api/rooms/leave', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({room_id: currentRoom, username: username})
        });
      } catch(e) {}
    }
    if (eventSource) { eventSource.close(); eventSource = null; }
    document.getElementById('status-dot').className = '';
    currentRoom = '';
    document.getElementById('current-room-name').textContent = 'Select a room';
    document.getElementById('leave-btn').style.display = 'none';
    document.getElementById('msg-input').disabled = true;
    document.getElementById('send-btn').disabled = true;
    document.getElementById('user-list').innerHTML = '';
    document.getElementById('messages').innerHTML = '<p class="msg system">Join a room to start chatting</p>';
    await loadRooms();
  }

  async function sendMessage() {
    const input = document.getElementById('msg-input');
    const content = input.value.trim();
    if (!content || !currentRoom) return;
    input.value = '';
    try {
      await fetch(API + '/api/messages', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({room_id: currentRoom, username: username, content: content})
      });
    } catch(e) { console.error('sendMessage:', e); }
  }

  async function loadUsers() {
    if (!currentRoom) return;
    try {
      const res = await fetch(API + '/api/rooms/' + encodeURIComponent(currentRoom) + '/users');
      const data = await res.json();
      const ul = document.getElementById('user-list');
      const users = data.users || [];
      if (users.length === 0) {
        ul.innerHTML = '<p style="padding:8px 14px;color:#888;font-size:0.8rem">No users</p>';
        return;
      }
      ul.innerHTML = users.map(u =>
        '<div class="user-item ' + (u.username === username ? 'self' : '') + '">' + u.username + '</div>'
      ).join('');
    } catch(e) {}
  }

  function appendMessage(msg) {
    const box = document.getElementById('messages');
    const div = document.createElement('div');
    const isSystem = msg.type === 'USER_JOINED' || msg.type === 'USER_LEFT' || msg.type === 2 || msg.type === 3;
    const isSelf = msg.username === username;
    if (isSystem) {
      div.className = 'msg system';
      div.textContent = msg.content;
    } else {
      div.className = 'msg ' + (isSelf ? 'self' : 'other');
      const ts = msg.timestamp ? new Date(msg.timestamp * 1000).toLocaleTimeString() : '';
      div.innerHTML = '<div class="meta">' + (isSelf ? 'You' : msg.username) + ' \u00b7 ' + ts + '</div>' + escHtml(msg.content);
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
</script>
</body>
</html>`

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

const docsHTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>gRPC Chat Service - API Reference</title>
<style>
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0d1117;color:#c9d1d9;line-height:1.6}
  a{color:#58a6ff;text-decoration:none}a:hover{text-decoration:underline}
  header{background:#161b22;border-bottom:1px solid #30363d;padding:16px 32px;display:flex;align-items:center;justify-content:space-between}
  header h1{font-size:1.25rem;color:#f0f6fc}
  header nav a{margin-left:20px;font-size:0.9rem;color:#8b949e}
  .hero{background:#161b22;border-bottom:1px solid #30363d;padding:40px 32px}
  .hero h2{font-size:1.8rem;color:#f0f6fc;margin-bottom:8px}
  .hero p{color:#8b949e;max-width:640px}
  .badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:600;margin-right:6px}
  .badge.stream{background:#1f6feb;color:#fff}
  .badge.unary{background:#238636;color:#fff}
  .badge.get{background:#1a7f37;color:#fff}
  .badge.post{background:#9a6700;color:#fff}
  .container{max-width:1000px;margin:0 auto;padding:32px}
  .toc{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px 24px;margin-bottom:32px}
  .toc h3{font-size:0.85rem;text-transform:uppercase;letter-spacing:1px;color:#8b949e;margin-bottom:12px}
  .toc ul{list-style:none;display:flex;flex-wrap:wrap;gap:8px 24px}
  .toc li a{font-size:0.9rem}
  .rpc{background:#161b22;border:1px solid #30363d;border-radius:8px;margin-bottom:28px;overflow:hidden}
  .rpc-header{padding:16px 20px;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:10px}
  .rpc-header h2{font-size:1.1rem;color:#f0f6fc}
  .rpc-header p{color:#8b949e;font-size:0.875rem;margin-top:2px}
  .rpc-body{padding:20px}
  .section{margin-bottom:20px}
  .section h3{font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;color:#8b949e;margin-bottom:10px}
  .schema{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  table{width:100%;border-collapse:collapse;font-size:0.85rem}
  th{text-align:left;padding:7px 12px;background:#0d1117;color:#8b949e;font-weight:500;border-bottom:1px solid #30363d}
  td{padding:7px 12px;border-bottom:1px solid #21262d}
  td code{background:#0d1117;padding:2px 6px;border-radius:4px;font-size:0.8rem;color:#e6edf3}
  pre{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:14px 16px;overflow-x:auto;font-size:0.82rem;color:#e6edf3;position:relative}
  .copy-btn{position:absolute;top:8px;right:8px;background:#21262d;border:1px solid #30363d;color:#8b949e;padding:3px 10px;border-radius:4px;cursor:pointer;font-size:0.75rem}
  .copy-btn:hover{background:#30363d;color:#e6edf3}
  .tabs{display:flex;gap:2px;margin-bottom:8px}
  .tab{padding:5px 14px;background:#0d1117;border:1px solid #30363d;border-radius:4px 4px 0 0;cursor:pointer;font-size:0.82rem;color:#8b949e;border-bottom:none}
  .tab.active{background:#161b22;color:#f0f6fc;border-color:#30363d}
  .tab-panel{display:none}.tab-panel.active{display:block}
  .note{background:#161b22;border-left:3px solid #1f6feb;padding:10px 14px;border-radius:0 4px 4px 0;font-size:0.85rem;color:#8b949e;margin-top:10px}
  footer{border-top:1px solid #30363d;padding:24px 32px;text-align:center;color:#8b949e;font-size:0.85rem}
</style>
</head>
<body>
<header>
  <h1>gRPC Chat Service</h1>
  <nav>
    <a href="/chat-service/">Live Chat UI</a>
    <a href="/chat-service/docs">API Docs</a>
  </nav>
</header>
<div class="hero">
  <h2>API Reference</h2>
  <p>Full documentation for all gRPC RPCs and their equivalent REST endpoints exposed by the web bridge. Service: <code>chat.ChatService</code> &nbsp;|&nbsp; Port: <strong>50051</strong> (gRPC) &nbsp;|&nbsp; Port: <strong>8080</strong> (REST bridge)</p>
</div>
<div class="container">

<div class="toc">
  <h3>RPCs</h3>
  <ul>
    <li><a href="#GetRooms">GetRooms</a></li>
    <li><a href="#JoinRoom">JoinRoom</a></li>
    <li><a href="#SendMessage">SendMessage</a></li>
    <li><a href="#LeaveRoom">LeaveRoom</a></li>
    <li><a href="#GetRoomUsers">GetRoomUsers</a></li>
  </ul>
</div>

<!-- GetRooms -->
<div class="rpc" id="GetRooms">
  <div class="rpc-header">
    <div>
      <h2>GetRooms <span class="badge unary">unary</span></h2>
      <p>Returns a list of all active chat rooms with their user counts.</p>
    </div>
  </div>
  <div class="rpc-body">
    <div class="schema">
      <div class="section">
        <h3>Request &mdash; GetRoomsRequest</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody><tr><td colspan="3" style="color:#8b949e;font-style:italic">empty</td></tr></tbody></table>
      </div>
      <div class="section">
        <h3>Response &mdash; GetRoomsResponse</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>rooms</code></td><td>Room[]</td><td>list of rooms</td></tr>
          <tr><td>&nbsp;&nbsp;<code>room_id</code></td><td>string</td><td>unique room identifier</td></tr>
          <tr><td>&nbsp;&nbsp;<code>name</code></td><td>string</td><td>display name</td></tr>
          <tr><td>&nbsp;&nbsp;<code>user_count</code></td><td>int32</td><td>active users</td></tr>
        </tbody></table>
      </div>
    </div>
    <div class="section">
      <h3>Examples</h3>
      <div class="tabs">
        <div class="tab active" onclick="showTab(this,'gr1')">grpcurl</div>
        <div class="tab" onclick="showTab(this,'rest1')">REST</div>
        <div class="tab" onclick="showTab(this,'resp1')">Response</div>
      </div>
      <div class="tab-panel active" id="gr1"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>grpcurl -plaintext localhost:50051 chat.ChatService/GetRooms

# With TLS (self-signed):
grpcurl -insecure grpc-service-apache-origin.qa.akamai.com:443 chat.ChatService/GetRooms</pre></div>
  <div class="tab-panel" id="rest1"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>curl https://grpc-service-apache-origin.qa.akamai.com/chat-service/api/rooms</pre></div>
      <div class="tab-panel" id="resp1"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>{
  "rooms": [
    {
      "room_id": "lobby",
      "name": "lobby",
      "user_count": 3
    },
    {
      "room_id": "general",
      "name": "general",
      "user_count": 1
    }
  ]
}</pre></div>
    </div>
  </div>
</div>

<!-- JoinRoom -->
<div class="rpc" id="JoinRoom">
  <div class="rpc-header">
    <div>
      <h2>JoinRoom <span class="badge stream">server-streaming</span></h2>
      <p>Join a chat room and receive a continuous stream of messages. Creates the room if it does not exist.</p>
    </div>
  </div>
  <div class="rpc-body">
    <div class="schema">
      <div class="section">
        <h3>Request &mdash; JoinRoomRequest</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>room_id</code></td><td>string</td><td>required</td></tr>
          <tr><td><code>username</code></td><td>string</td><td>required</td></tr>
        </tbody></table>
      </div>
      <div class="section">
        <h3>Stream Response &mdash; Message</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>message_id</code></td><td>string</td><td>UUID</td></tr>
          <tr><td><code>room_id</code></td><td>string</td><td></td></tr>
          <tr><td><code>username</code></td><td>string</td><td>sender</td></tr>
          <tr><td><code>content</code></td><td>string</td><td>message text</td></tr>
          <tr><td><code>timestamp</code></td><td>int64</td><td>Unix epoch seconds</td></tr>
          <tr><td><code>type</code></td><td>MessageType</td><td>see enum below</td></tr>
        </tbody></table>
      </div>
    </div>
    <div class="section">
      <h3>MessageType enum</h3>
      <table><thead><tr><th>Value</th><th>Number</th><th>Description</th></tr></thead>
      <tbody>
        <tr><td><code>USER_MESSAGE</code></td><td>0</td><td>Regular chat message</td></tr>
        <tr><td><code>SYSTEM_MESSAGE</code></td><td>1</td><td>Server-generated notice</td></tr>
        <tr><td><code>USER_JOINED</code></td><td>2</td><td>User joined the room</td></tr>
        <tr><td><code>USER_LEFT</code></td><td>3</td><td>User left the room</td></tr>
      </tbody></table>
    </div>
    <div class="section">
      <h3>Examples</h3>
      <div class="tabs">
        <div class="tab active" onclick="showTab(this,'gr2')">grpcurl</div>
        <div class="tab" onclick="showTab(this,'rest2')">REST (SSE)</div>
        <div class="tab" onclick="showTab(this,'resp2')">Stream output</div>
      </div>
      <div class="tab-panel active" id="gr2"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>grpcurl -plaintext -d '{"room_id":"lobby","username":"alice"}' \
  localhost:50051 chat.ChatService/JoinRoom

# With TLS:
grpcurl -insecure -d '{"room_id":"lobby","username":"alice"}' \
  grpc-service-apache-origin.qa.akamai.com:443 chat.ChatService/JoinRoom</pre></div>
      <div class="tab-panel" id="rest2"><pre><button class="copy-btn" onclick="copy(this)">Copy</button># SSE stream — stays open until the client disconnects
curl -N "https://grpc-service-apache-origin.qa.akamai.com/chat-service/api/rooms/join?room_id=lobby&amp;username=alice"

# JavaScript EventSource:
const es = new EventSource('/chat-service/api/rooms/join?room_id=lobby&amp;username=alice');
es.onmessage = e =&gt; console.log(JSON.parse(e.data));</pre></div>
      <div class="tab-panel" id="resp2"><pre><button class="copy-btn" onclick="copy(this)">Copy</button># Each streamed message:
{
  "message_id": "a1b2c3d4-...",
  "room_id": "lobby",
  "username": "alice",
  "content": "alice joined the room",
  "timestamp": 1748390400,
  "type": "USER_JOINED"
}
{
  "message_id": "e5f6a7b8-...",
  "room_id": "lobby",
  "username": "bob",
  "content": "Hello everyone!",
  "timestamp": 1748390410,
  "type": "USER_MESSAGE"
}</pre></div>
    </div>
    <div class="note">This is a long-lived streaming RPC. The connection stays open until the client disconnects or the server shuts down. Use grpcurl's streaming output or SSE in a browser.</div>
  </div>
</div>

<!-- SendMessage -->
<div class="rpc" id="SendMessage">
  <div class="rpc-header">
    <div>
      <h2>SendMessage <span class="badge unary">unary</span></h2>
      <p>Send a message to a room. The message is broadcast to all users currently streaming via JoinRoom.</p>
    </div>
  </div>
  <div class="rpc-body">
    <div class="schema">
      <div class="section">
        <h3>Request &mdash; SendMessageRequest</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>room_id</code></td><td>string</td><td>required</td></tr>
          <tr><td><code>username</code></td><td>string</td><td>sender name</td></tr>
          <tr><td><code>content</code></td><td>string</td><td>message text</td></tr>
        </tbody></table>
      </div>
      <div class="section">
        <h3>Response &mdash; SendMessageResponse</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>success</code></td><td>bool</td><td>true if delivered</td></tr>
          <tr><td><code>message_id</code></td><td>string</td><td>UUID of the new message</td></tr>
        </tbody></table>
      </div>
    </div>
    <div class="section">
      <h3>Examples</h3>
      <div class="tabs">
        <div class="tab active" onclick="showTab(this,'gr3')">grpcurl</div>
        <div class="tab" onclick="showTab(this,'rest3')">REST</div>
        <div class="tab" onclick="showTab(this,'resp3')">Response</div>
      </div>
      <div class="tab-panel active" id="gr3"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>grpcurl -plaintext \
  -d '{"room_id":"lobby","username":"alice","content":"Hello!"}' \
  localhost:50051 chat.ChatService/SendMessage

# With TLS:
grpcurl -insecure \
  -d '{"room_id":"lobby","username":"alice","content":"Hello!"}' \
    grpc-service-apache-origin.qa.akamai.com:443 chat.ChatService/SendMessage</pre></div>
      <div class="tab-panel" id="rest3"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>curl -X POST https://grpc-service-apache-origin.qa.akamai.com/chat-service/api/messages \
  -H "Content-Type: application/json" \
  -d '{"room_id":"lobby","username":"alice","content":"Hello!"}'</pre></div>
      <div class="tab-panel" id="resp3"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>{
  "success": true,
  "message_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}</pre></div>
    </div>
  </div>
</div>

<!-- LeaveRoom -->
<div class="rpc" id="LeaveRoom">
  <div class="rpc-header">
    <div>
      <h2>LeaveRoom <span class="badge unary">unary</span></h2>
      <p>Remove a user from a room. Closes their stream and notifies remaining users.</p>
    </div>
  </div>
  <div class="rpc-body">
    <div class="schema">
      <div class="section">
        <h3>Request &mdash; LeaveRoomRequest</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>room_id</code></td><td>string</td><td>required</td></tr>
          <tr><td><code>username</code></td><td>string</td><td>required</td></tr>
        </tbody></table>
      </div>
      <div class="section">
        <h3>Response &mdash; LeaveRoomResponse</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>success</code></td><td>bool</td><td>true if removed</td></tr>
        </tbody></table>
      </div>
    </div>
    <div class="section">
      <h3>Examples</h3>
      <div class="tabs">
        <div class="tab active" onclick="showTab(this,'gr4')">grpcurl</div>
        <div class="tab" onclick="showTab(this,'rest4')">REST</div>
        <div class="tab" onclick="showTab(this,'resp4')">Response</div>
      </div>
      <div class="tab-panel active" id="gr4"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>grpcurl -plaintext \
  -d '{"room_id":"lobby","username":"alice"}' \
  localhost:50051 chat.ChatService/LeaveRoom

# With TLS:
grpcurl -insecure \
  -d '{"room_id":"lobby","username":"alice"}' \
    grpc-service-apache-origin.qa.akamai.com:443 chat.ChatService/LeaveRoom</pre></div>
      <div class="tab-panel" id="rest4"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>curl -X POST https://grpc-service-apache-origin.qa.akamai.com/chat-service/api/rooms/leave \
  -H "Content-Type: application/json" \
  -d '{"room_id":"lobby","username":"alice"}'</pre></div>
      <div class="tab-panel" id="resp4"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>{
  "success": true
}</pre></div>
    </div>
  </div>
</div>

<!-- GetRoomUsers -->
<div class="rpc" id="GetRoomUsers">
  <div class="rpc-header">
    <div>
      <h2>GetRoomUsers <span class="badge unary">unary</span></h2>
      <p>Returns all users currently active in a specific room.</p>
    </div>
  </div>
  <div class="rpc-body">
    <div class="schema">
      <div class="section">
        <h3>Request &mdash; GetRoomUsersRequest</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>room_id</code></td><td>string</td><td>required</td></tr>
        </tbody></table>
      </div>
      <div class="section">
        <h3>Response &mdash; GetRoomUsersResponse</h3>
        <table><thead><tr><th>Field</th><th>Type</th><th>Notes</th></tr></thead>
        <tbody>
          <tr><td><code>users</code></td><td>User[]</td><td>list of users</td></tr>
          <tr><td>&nbsp;&nbsp;<code>username</code></td><td>string</td><td>user name</td></tr>
          <tr><td>&nbsp;&nbsp;<code>joined_at</code></td><td>int64</td><td>Unix epoch seconds</td></tr>
        </tbody></table>
      </div>
    </div>
    <div class="section">
      <h3>Examples</h3>
      <div class="tabs">
        <div class="tab active" onclick="showTab(this,'gr5')">grpcurl</div>
        <div class="tab" onclick="showTab(this,'rest5')">REST</div>
        <div class="tab" onclick="showTab(this,'resp5')">Response</div>
      </div>
      <div class="tab-panel active" id="gr5"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>grpcurl -plaintext \
  -d '{"room_id":"lobby"}' \
  localhost:50051 chat.ChatService/GetRoomUsers

# With TLS:
grpcurl -insecure \
  -d '{"room_id":"lobby"}' \
    grpc-service-apache-origin.qa.akamai.com:443 chat.ChatService/GetRoomUsers</pre></div>
      <div class="tab-panel" id="rest5"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>curl https://grpc-service-apache-origin.qa.akamai.com/chat-service/api/rooms/lobby/users</pre></div>
      <div class="tab-panel" id="resp5"><pre><button class="copy-btn" onclick="copy(this)">Copy</button>{
  "users": [
    {
      "username": "alice",
      "joined_at": 1748390400
    },
    {
      "username": "bob",
      "joined_at": 1748390450
    }
  ]
}</pre></div>
    </div>
  </div>
</div>

</div><!-- /container -->
<footer>gRPC Chat Service &mdash; proto package <code>chat</code> &mdash; service <code>ChatService</code></footer>
<script>
  function showTab(btn, id) {
    const rpc = btn.closest('.rpc-body');
    rpc.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    rpc.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(id).classList.add('active');
  }
  function copy(btn) {
    const text = btn.parentElement.innerText.replace('Copy\n','');
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => btn.textContent = 'Copy', 1500);
    });
  }
</script>
</body>
</html>`

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/rooms", cors(getRooms))
	mux.HandleFunc("GET /chat-service/api/rooms", cors(getRooms))
	mux.HandleFunc("GET /api/rooms/join", cors(joinRoom))
	mux.HandleFunc("GET /chat-service/api/rooms/join", cors(joinRoom))
	mux.HandleFunc("GET /api/rooms/{id}/users", cors(getRoomUsers))
	mux.HandleFunc("GET /chat-service/api/rooms/{id}/users", cors(getRoomUsers))
	mux.HandleFunc("POST /api/messages", cors(sendMessage))
	mux.HandleFunc("POST /chat-service/api/messages", cors(sendMessage))
	mux.HandleFunc("POST /api/rooms/leave", cors(leaveRoom))
	mux.HandleFunc("POST /chat-service/api/rooms/leave", cors(leaveRoom))
	healthHandler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, `{"status":"ok"}`)
	}
	docsHandler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, docsHTML)
	}
	mux.HandleFunc("GET /docs", docsHandler)
	mux.HandleFunc("GET /docs/", docsHandler)
	mux.HandleFunc("GET /chat-service/docs", docsHandler)
	mux.HandleFunc("GET /chat-service/docs/", docsHandler)
	chatHandler := func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		fmt.Fprint(w, indexHTML)
	}
	mux.HandleFunc("GET /chat", chatHandler)
	mux.HandleFunc("GET /chat/", chatHandler)
	mux.HandleFunc("GET /chat-service", chatHandler)
	mux.HandleFunc("GET /chat-service/", chatHandler)
	mux.HandleFunc("GET /healthz", healthHandler)
	mux.HandleFunc("GET /chat-service/healthz", healthHandler)
	mux.HandleFunc("GET /", chatHandler)

	log.Println("Web bridge listening on :8080")
	if err := http.ListenAndServe(":8080", mux); err != nil {
		log.Fatal(err)
	}
}
