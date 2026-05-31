import json
import os
import sys
import uuid
from pathlib import Path

import grpc
from flask import Flask, Response, jsonify, request, send_from_directory, stream_with_context


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc


app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path='')


def grpc_target() -> str:
    return os.getenv('JOB_ORCHESTRATOR_GRPC_ADDR', '127.0.0.1:50055')


def get_channel() -> grpc.Channel:
    return grpc.insecure_channel(grpc_target())


def serialize_status(status: job_orchestrator_pb2.JobStatus) -> dict:
    return {
        'job_id': status.job_id,
        'state': status.state,
        'message': status.message,
        'created_at': status.created_at,
        'updated_at': status.updated_at,
        'params': dict(status.params),
    }


def serialize_update(update: job_orchestrator_pb2.JobUpdate) -> dict:
    return {
        'job_id': update.job_id,
        'state': update.state,
        'detail': update.detail,
        'timestamp_ms': update.timestamp_ms,
        'progress_percent': update.progress_percent,
    }


def rpc_error_response(exc: grpc.RpcError, fallback_code: int = 500):
    status_code = fallback_code
    if exc.code() == grpc.StatusCode.NOT_FOUND:
        status_code = 404
    elif exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
        status_code = 400
    elif exc.code() == grpc.StatusCode.UNAVAILABLE:
        status_code = 503

    return jsonify({
        'ok': False,
        'code': exc.code().name if exc.code() else 'UNKNOWN',
        'details': exc.details() or 'gRPC request failed',
    }), status_code


@app.get('/')
def index() -> Response:
    return send_from_directory(BASE_DIR, 'index.html')


@app.get('/healthz')
def healthz() -> Response:
    return jsonify({'ok': True, 'grpc_target': grpc_target()})


@app.get('/api/overview')
def overview() -> Response:
    return jsonify({
        'service': 'joborchestrator.JobOrchestrator',
        'grpc_target': grpc_target(),
        'rpc_methods': [
            'SubmitJob',
            'GetJobStatus',
            'PushLogs',
            'WatchJob',
            'InteractiveSession',
            'SizedInteractiveSession',
            'GetSizedResponse',
            'UnarySizedResponse',
            'JustTrailers',
        ],
        'commands': ['PAUSE', 'RESUME', 'CANCEL', 'SET_LOG_LEVEL', 'GET_STATUS'],
    })


@app.post('/api/jobs')
def submit_job() -> Response:
    payload = request.get_json(silent=True) or {}
    name = str(payload.get('name', '')).strip()
    params = payload.get('params', {}) or {}

    if not name:
        return jsonify({'ok': False, 'details': 'name is required'}), 400

    if not isinstance(params, dict):
        return jsonify({'ok': False, 'details': 'params must be an object'}), 400

    request_message = job_orchestrator_pb2.JobSpec(
        name=name,
        params={str(key): str(value) for key, value in params.items()},
    )

    with get_channel() as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        try:
            response = stub.SubmitJob(request_message)
        except grpc.RpcError as exc:
            return rpc_error_response(exc)

    return jsonify({
        'ok': True,
        'job_id': response.job_id,
        'message': response.message,
    })


@app.get('/api/jobs/<job_id>')
def get_status(job_id: str) -> Response:
    with get_channel() as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        try:
            response = stub.GetJobStatus(job_orchestrator_pb2.JobId(id=job_id))
        except grpc.RpcError as exc:
            return rpc_error_response(exc)

    return jsonify({'ok': True, 'status': serialize_status(response)})


@app.get('/api/jobs/<job_id>/watch')
def watch_job(job_id: str) -> Response:
    def generate():
        with get_channel() as channel:
            stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
            try:
                for update in stub.WatchJob(job_orchestrator_pb2.JobId(id=job_id)):
                    yield f"data: {json.dumps(serialize_update(update))}\n\n"
            except grpc.RpcError as exc:
                payload = {
                    'code': exc.code().name if exc.code() else 'UNKNOWN',
                    'details': exc.details() or 'stream failed',
                }
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
    }
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)


@app.post('/api/jobs/<job_id>/control')
def control_job(job_id: str) -> Response:
    payload = request.get_json(silent=True) or {}
    command = str(payload.get('command', '')).strip().upper()
    arg = str(payload.get('arg', '')).strip()

    if not command:
        return jsonify({'ok': False, 'details': 'command is required'}), 400

    request_message = job_orchestrator_pb2.ControlMessage(job_id=job_id, command=command, arg=arg)

    def command_stream():
        yield request_message

    with get_channel() as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        try:
            response_stream = stub.InteractiveSession(command_stream())
            first_event = next(response_stream, None)
            result_event = next(response_stream, None)
        except grpc.RpcError as exc:
            return rpc_error_response(exc)

    event = result_event or first_event
    if event is None:
        return jsonify({'ok': False, 'details': 'no response event received'}), 502

    return jsonify({
        'ok': event.event_type != 'ERROR',
        'event': {
            'job_id': event.job_id,
            'event_type': event.event_type,
            'payload': event.payload,
            'timestamp_ms': event.timestamp_ms,
        },
    }), 200 if event.event_type != 'ERROR' else 400


@app.post('/api/jobs/<job_id>/logs')
def push_logs(job_id: str) -> Response:
    payload = request.get_json(silent=True) or {}
    lines = payload.get('lines', [])

    if not isinstance(lines, list) or not lines:
        return jsonify({'ok': False, 'details': 'lines must be a non-empty array'}), 400

    def log_stream():
        for raw_line in lines:
            line = str(raw_line).strip()
            if not line:
                continue
            upper_line = line.upper()
            level = 'INFO'
            if 'ERROR' in upper_line:
                level = 'ERROR'
            elif 'WARN' in upper_line:
                level = 'WARN'
            elif 'DEBUG' in upper_line:
                level = 'DEBUG'

            yield job_orchestrator_pb2.LogLine(
                job_id=job_id,
                line=line,
                timestamp_ms=0,
                level=level,
            )

    with get_channel() as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        try:
            response = stub.PushLogs(log_stream())
        except grpc.RpcError as exc:
            return rpc_error_response(exc)

    return jsonify({
        'ok': True,
        'summary': {
            'job_id': response.job_id,
            'total_lines': response.total_lines,
            'error_lines': response.error_lines,
            'warn_lines': response.warn_lines,
            'message': response.message,
        },
    })


if __name__ == '__main__':
    host = os.getenv('JOB_ORCHESTRATOR_WEB_HOST', '127.0.0.1')
    port = int(os.getenv('JOB_ORCHESTRATOR_WEB_PORT', '8082'))
    app.run(host=host, port=port, debug=False, threaded=True)