"""TUI (Terminal User Interface) for Job Orchestrator using Textual"""
import asyncio
import time
from datetime import datetime

import grpc
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Input, Button, DataTable, Log
from textual.binding import Binding

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc


class JobOrchestratorTUI(App):
    """Textual TUI for Job Orchestrator"""
    
    CSS = """
    #jobs-table {
        height: 40%;
        border: solid green;
    }
    
    #status-panel {
        height: 30%;
        border: solid blue;
    }
    
    #logs-panel {
        height: 20%;
        border: solid yellow;
    }
    
    #command-input {
        height: 3;
        border: solid white;
    }
    
    .status-text {
        padding: 1;
    }
    
    .log-text {
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]
    
    def __init__(self, server_addr: str = "localhost:50055"):
        super().__init__()
        self.server_addr = server_addr
        self.channel = None
        self.stub = None
        self.current_job_id = None
        self.watch_task = None
        self.session_task = None
        self.jobs = {}
    
    def compose(self) -> ComposeResult:
        """Create UI layout"""
        yield Header()
        
        # Jobs table
        jobs_table = DataTable(id="jobs-table")
        jobs_table.add_columns("Job ID", "Name", "State", "Progress", "Message")
        jobs_table.cursor_type = "row"
        yield jobs_table
        
        # Status panel
        yield Container(
            Static("No job selected", id="status-display", classes="status-text"),
            id="status-panel"
        )
        
        # Logs panel
        yield Container(
            Log(id="logs-display", classes="log-text"),
            id="logs-panel"
        )
        
        # Command input
        yield Container(
            Input(placeholder="Commands: submit <name>, watch <id>, pause, resume, cancel, quit", id="command-input"),
            id="command-input"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Called when app starts"""
        # Connect to gRPC server
        self.channel = grpc.aio.insecure_channel(self.server_addr)
        self.stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(self.channel)
        
        # Update title
        self.title = f"Job Orchestrator TUI - {self.server_addr}"
        
        # Log welcome message
        log_widget = self.query_one("#logs-display", Log)
        log_widget.write_line(f"Connected to {self.server_addr}")
        log_widget.write_line("Type commands in the input box below")
        log_widget.write_line("Examples: submit smoke-tests env=qa, watch <job-id>, pause, resume")
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input"""
        command = event.value.strip()
        if not command:
            return
        
        # Clear input
        event.input.value = ""
        
        # Log command
        log_widget = self.query_one("#logs-display", Log)
        log_widget.write_line(f"> {command}")
        
        # Parse and execute command
        await self.execute_command(command)
    
    async def execute_command(self, command: str):
        """Execute a command"""
        log_widget = self.query_one("#logs-display", Log)
        parts = command.split()
        
        if not parts:
            return
        
        cmd = parts[0].lower()
        
        try:
            if cmd == "submit":
                # Parse: submit <name> [key=value ...]
                if len(parts) < 2:
                    log_widget.write_line("Usage: submit <name> [key=value ...]")
                    return
                
                name = parts[1]
                params = {}
                for param in parts[2:]:
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
                
                # Submit job
                request = job_orchestrator_pb2.JobSpec(name=name, params=params)
                response = await self.stub.SubmitJob(request)
                
                log_widget.write_line(f"✓ Job submitted: {response.job_id}")
                
                # Add to table
                await self.refresh_jobs()
            
            elif cmd == "watch":
                # Parse: watch <job-id>
                if len(parts) < 2:
                    log_widget.write_line("Usage: watch <job-id>")
                    return
                
                job_id = parts[1]
                await self.start_watching(job_id)
            
            elif cmd == "status":
                # Get status of current job
                if not self.current_job_id:
                    log_widget.write_line("No job selected")
                    return
                
                request = job_orchestrator_pb2.JobId(id=self.current_job_id)
                response = await self.stub.GetJobStatus(request)
                
                log_widget.write_line(f"Status: {response.state} - {response.message}")
            
            elif cmd in ["pause", "resume", "cancel"]:
                # Send control message
                if not self.current_job_id:
                    log_widget.write_line("No job selected")
                    return
                
                if not self.session_task:
                    log_widget.write_line("No active session. Use 'watch <job-id>' first")
                    return
                
                # This would require session message queue
                log_widget.write_line(f"Command '{cmd}' - feature requires active session")
            
            elif cmd == "quit":
                await self.action_quit()
            
            else:
                log_widget.write_line(f"Unknown command: {cmd}")
        
        except grpc.RpcError as e:
            log_widget.write_line(f"✗ Error: {e.details()}")
        except Exception as e:
            log_widget.write_line(f"✗ Error: {str(e)}")
    
    async def start_watching(self, job_id: str):
        """Start watching a job"""
        # Stop previous watch
        if self.watch_task:
            self.watch_task.cancel()
        
        self.current_job_id = job_id
        
        # Start watch task
        self.watch_task = asyncio.create_task(self.watch_job_updates(job_id))
        
        log_widget = self.query_one("#logs-display", Log)
        log_widget.write_line(f"Watching job {job_id}...")
    
    async def watch_job_updates(self, job_id: str):
        """Watch job updates stream"""
        try:
            request = job_orchestrator_pb2.JobId(id=job_id)
            
            async for update in self.stub.WatchJob(request):
                # Update status display
                status_widget = self.query_one("#status-display", Static)
                timestamp = datetime.fromtimestamp(update.timestamp_ms / 1000).strftime('%H:%M:%S')
                status_text = (
                    f"Job: {update.job_id}\n"
                    f"State: {update.state}\n"
                    f"Progress: {update.progress_percent}%\n"
                    f"Detail: {update.detail}\n"
                    f"Updated: {timestamp}"
                )
                status_widget.update(status_text)
                
                # Update logs
                if "[Heartbeat]" not in update.detail:
                    log_widget = self.query_one("#logs-display", Log)
                    log_widget.write_line(f"[{timestamp}] {update.state}: {update.detail}")
                
                # Update jobs table
                await self.refresh_jobs()
                
                # Stop if terminal state
                if update.state in ['COMPLETED', 'FAILED']:
                    break
        
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log_widget = self.query_one("#logs-display", Log)
            log_widget.write_line(f"Watch error: {str(e)}")
    
    async def refresh_jobs(self):
        """Refresh jobs table (simplified - would need ListJobs RPC)"""
        # In a real implementation, we'd call a ListJobs RPC
        # For now, just update if we have the current job
        if self.current_job_id:
            try:
                request = job_orchestrator_pb2.JobId(id=self.current_job_id)
                response = await self.stub.GetJobStatus(request)
                
                # Update table
                table = self.query_one("#jobs-table", DataTable)
                
                # Check if row exists
                row_key = response.job_id
                try:
                    table.update_cell(row_key, "State", response.state)
                    table.update_cell(row_key, "Message", response.message[:30])
                except:
                    # Add new row
                    table.add_row(
                        response.job_id,
                        response.params.get('name', 'unknown'),
                        response.state,
                        "N/A",
                        response.message[:30],
                        key=row_key
                    )
            except:
                pass
    
    async def action_refresh(self) -> None:
        """Refresh action"""
        await self.refresh_jobs()
        log_widget = self.query_one("#logs-display", Log)
        log_widget.write_line("Refreshed")
    
    async def action_quit(self) -> None:
        """Quit action"""
        # Cleanup
        if self.watch_task:
            self.watch_task.cancel()
        if self.session_task:
            self.session_task.cancel()
        if self.channel:
            await self.channel.close()
        
        self.exit()


def main():
    """Main entry point"""
    import sys
    
    server_addr = sys.argv[1] if len(sys.argv) > 1 else "localhost:50055"
    app = JobOrchestratorTUI(server_addr)
    app.run()


if __name__ == '__main__':
    main()
