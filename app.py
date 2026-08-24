import os
import re
import json
import base64
import asyncio
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, jsonify, session
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

# ==================== CONFIG ====================
API_ID = int(os.environ.get('API_ID', 33435112))
API_HASH = os.environ.get('API_HASH', '89b7361a12dc0d54dd1973c8a95647b6')
USER_PHONE = os.environ.get('USER_PHONE', '+917970462807')
TARGET_BOT = os.environ.get('TARGET_BOT', 'ff_accessXtoken_bot')
JWT_API = os.environ.get('JWT_API', 'https://ff-jwt-gen-api.lovable.app/api/public/token')

# ==================== FLASK APP ====================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ff-token-manager-secret-key-2024')

# ==================== IN-MEMORY STORAGE ====================
tokens_store = []
sessions_store = {}
pending_data = {}  # phone: {"client": client, "phone_code_hash": hash}

# ==================== HTML TEMPLATE ====================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 FF Token Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Poppins', sans-serif;
            background: #0a0a1a;
            min-height: 100vh;
            background: radial-gradient(ellipse at center, #1a1a3e 0%, #0a0a1a 100%);
            overflow-x: hidden;
            padding: 20px;
        }
        .bg-animation {
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 0;
            overflow: hidden;
        }
        .bg-animation span {
            position: absolute;
            width: 6px; height: 6px;
            background: rgba(255,107,53,0.3);
            border-radius: 50%;
            animation: float 20s infinite;
        }
        .bg-animation span:nth-child(1) { top: 10%; left: 10%; animation-delay: 0s; }
        .bg-animation span:nth-child(2) { top: 20%; right: 15%; animation-delay: 2s; width: 8px; height: 8px; }
        .bg-animation span:nth-child(3) { bottom: 30%; left: 20%; animation-delay: 4s; }
        .bg-animation span:nth-child(4) { bottom: 20%; right: 10%; animation-delay: 6s; width: 10px; height: 10px; }
        .bg-animation span:nth-child(5) { top: 50%; left: 50%; animation-delay: 8s; width: 12px; height: 12px; }
        .bg-animation span:nth-child(6) { top: 70%; left: 5%; animation-delay: 10s; }
        .bg-animation span:nth-child(7) { top: 5%; left: 50%; animation-delay: 12s; width: 8px; height: 8px; }
        .bg-animation span:nth-child(8) { bottom: 10%; left: 40%; animation-delay: 14s; }
        @keyframes float {
            0%,100% { transform: translateY(0) translateX(0) scale(1); opacity: 0.3; }
            25% { transform: translateY(-50px) translateX(30px) scale(1.5); opacity: 0.8; }
            50% { transform: translateY(-100px) translateX(-30px) scale(2); opacity: 0.5; }
            75% { transform: translateY(-50px) translateX(30px) scale(1.5); opacity: 0.8; }
        }
        .container {
            position: relative;
            z-index: 1;
            width: 100%;
            max-width: 600px;
            margin: 0 auto;
        }
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 30px 25px;
            border: 1px solid rgba(255,107,53,0.2);
            box-shadow: 0 0 60px rgba(255,107,53,0.1), inset 0 0 60px rgba(255,107,53,0.05);
            animation: glowPulse 4s ease-in-out infinite;
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: '';
            position: absolute;
            top: -50%; left: -50%;
            width: 200%; height: 200%;
            background: conic-gradient(from 0deg, transparent, rgba(255,107,53,0.1), transparent, rgba(255,107,53,0.1), transparent);
            animation: rotateGlow 10s linear infinite;
            z-index: 0;
        }
        @keyframes rotateGlow {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @keyframes glowPulse {
            0%,100% { border-color: rgba(255,107,53,0.2); }
            50% { border-color: rgba(255,107,53,0.6); }
        }
        .card > * { position: relative; z-index: 1; }
        .logo { text-align: center; margin-bottom: 25px; }
        .logo-icon {
            font-size: 50px;
            background: linear-gradient(135deg, #ff6b35, #ff4500);
            width: 70px; height: 70px;
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 15px;
            box-shadow: 0 0 40px rgba(255,107,53,0.3);
            animation: logoPulse 2s ease-in-out infinite;
        }
        @keyframes logoPulse {
            0%,100% { box-shadow: 0 0 40px rgba(255,107,53,0.3); }
            50% { box-shadow: 0 0 80px rgba(255,107,53,0.6); }
        }
        .logo h1 {
            font-family: 'Orbitron', sans-serif;
            font-size: 22px;
            font-weight: 900;
            background: linear-gradient(135deg, #ff6b35, #ff4500, #ff6b35);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientMove 3s ease-in-out infinite;
        }
        @keyframes gradientMove {
            0%,100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        .logo p {
            color: rgba(255,255,255,0.6);
            font-size: 12px;
            letter-spacing: 3px;
            text-transform: uppercase;
        }
        .login-section {
            background: rgba(0,200,255,0.05);
            border: 1px solid rgba(0,200,255,0.15);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 25px;
        }
        .login-section h3 {
            color: #fff;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .login-status {
            background: rgba(0,255,136,0.05);
            border: 1px solid rgba(0,255,136,0.1);
            border-radius: 12px;
            padding: 10px 15px;
            margin-bottom: 10px;
            display: none;
        }
        .login-status.active {
            display: block;
        }
        .login-status .user {
            color: #00ff88;
            font-weight: 600;
        }
        .login-status .logout-btn {
            background: rgba(255,68,68,0.1);
            border: 1px solid rgba(255,68,68,0.2);
            border-radius: 8px;
            color: #ff4444;
            padding: 4px 12px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        .login-status .logout-btn:hover {
            background: rgba(255,68,68,0.2);
        }
        .login-input {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .login-input input {
            flex: 1;
            padding: 12px 15px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 14px;
            font-family: 'Poppins', sans-serif;
            outline: none;
            transition: all 0.3s ease;
        }
        .login-input input:focus {
            border-color: #ff6b35;
            box-shadow: 0 0 20px rgba(255,107,53,0.1);
        }
        .login-input input::placeholder {
            color: rgba(255,255,255,0.3);
        }
        .login-btn {
            padding: 12px 25px;
            background: linear-gradient(135deg, #ff6b35, #ff4500);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }
        .login-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(255,107,53,0.3);
        }
        .otp-section {
            display: none;
            margin-top: 10px;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            border: 1px solid rgba(255,107,53,0.15);
        }
        .otp-section.active {
            display: block;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(-10px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        .otp-input {
            display: flex;
            gap: 10px;
        }
        .otp-input input {
            flex: 1;
            padding: 12px 15px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #fff;
            font-size: 18px;
            font-family: 'Orbitron', sans-serif;
            text-align: center;
            letter-spacing: 5px;
            outline: none;
            transition: all 0.3s ease;
        }
        .otp-input input:focus {
            border-color: #ff6b35;
            box-shadow: 0 0 20px rgba(255,107,53,0.1);
        }
        .otp-input .verify-btn {
            padding: 12px 25px;
            background: linear-gradient(135deg, #00ff88, #00cc66);
            border: none;
            border-radius: 12px;
            color: #fff;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
        }
        .otp-input .verify-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 30px rgba(0,255,136,0.3);
        }
        .otp-info {
            color: rgba(255,255,255,0.5);
            font-size: 12px;
            margin-top: 8px;
            text-align: center;
        }
        .status-text {
            color: rgba(255,255,255,0.6);
            font-size: 13px;
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.05);
            min-height: 40px;
            margin-top: 10px;
        }
        .status-text.success { color: #00ff88; border-color: rgba(0,255,136,0.2); }
        .status-text.error { color: #ff4444; border-color: rgba(255,68,68,0.2); }
        .status-text.info { color: #ff6b35; border-color: rgba(255,107,53,0.2); }
        .auto-check-section {
            background: rgba(255,107,53,0.05);
            border: 1px solid rgba(255,107,53,0.15);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 25px;
        }
        .auto-check-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .auto-check-header h3 {
            color: #fff;
            font-size: 16px;
        }
        .auto-check-controls {
            display: flex;
            gap: 10px;
        }
        .auto-check-btn {
            padding: 8px 15px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 10px;
            color: #fff;
            font-family: 'Poppins', sans-serif;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 12px;
        }
        .auto-check-btn:hover {
            border-color: #ff6b35;
        }
        .auto-check-btn.active {
            background: rgba(255,107,53,0.2);
            border-color: #ff6b35;
        }
        .auto-check-btn.running {
            background: rgba(0,255,136,0.1);
            border-color: #00ff88;
            color: #00ff88;
        }
        .timer-display {
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            color: #ff6b35;
            text-align: center;
            margin: 10px 0;
        }
        .tokens-section { margin-top: 20px; }
        .tokens-section h3 {
            color: #fff;
            font-size: 16px;
            margin-bottom: 15px;
        }
        .token-item {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 15px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .token-item:hover {
            border-color: rgba(255,107,53,0.3);
            transform: translateX(5px);
        }
        .token-item .uid {
            font-family: 'Orbitron', sans-serif;
            font-size: 16px;
            color: #ff6b35;
            font-weight: 700;
        }
        .token-item .name {
            color: rgba(255,255,255,0.7);
            font-size: 14px;
        }
        .token-item .time {
            color: rgba(255,255,255,0.3);
            font-size: 11px;
        }
        .token-item .badge {
            background: rgba(255,107,53,0.2);
            color: #ff6b35;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 600;
        }
        .jwt-display {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 10px;
            border: 1px solid rgba(255,107,53,0.1);
            word-break: break-all;
            font-size: 12px;
            color: rgba(255,255,255,0.7);
            font-family: 'Courier New', monospace;
            max-height: 200px;
            overflow-y: auto;
            display: none;
        }
        .jwt-display.active { display: block; }
        .toast {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.9);
            backdrop-filter: blur(10px);
            padding: 15px 25px;
            border-radius: 15px;
            border: 1px solid rgba(255,107,53,0.3);
            color: #fff;
            font-size: 14px;
            display: none;
            z-index: 2000;
            animation: toastIn 0.5s ease;
            max-width: 90%;
            text-align: center;
        }
        @keyframes toastIn {
            0% { transform: translateX(-50%) translateY(30px); opacity: 0; }
            100% { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
        .toast.show { display: block; }
        .toast.success { border-color: #00ff88; }
        .toast.error { border-color: #ff4444; }
        .spinner {
            width: 20px; height: 20px;
            border: 2px solid rgba(255,107,53,0.1);
            border-top: 2px solid #ff6b35;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 10px;
            vertical-align: middle;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .resend-btn {
            background: none;
            border: none;
            color: #ff6b35;
            cursor: pointer;
            text-decoration: underline;
            font-size: 12px;
            margin-top: 5px;
        }
        .resend-btn:hover {
            color: #ff4500;
        }
        @media (max-width: 480px) {
            .container { padding: 10px; }
            .card { padding: 20px 15px; }
            .login-input { flex-direction: column; }
            .login-btn { width: 100%; }
            .otp-input { flex-direction: column; }
            .otp-input .verify-btn { width: 100%; }
            .auto-check-controls { flex-wrap: wrap; }
            .auto-check-btn { flex: 1; min-width: 60px; }
        }
    </style>
</head>
<body>
    <div class="bg-animation"><span></span><span></span><span></span><span></span><span></span><span></span><span></span><span></span></div>
    <div class="toast" id="toast"></div>
    <div class="container">
        <div class="card">
            <div class="logo">
                <div class="logo-icon">🔑</div>
                <h1>FF TOKEN MANAGER</h1>
                <p>JWT Token Generator & Manager</p>
            </div>

            <div class="login-section">
                <h3>🔐 Login to Telegram</h3>
                
                <div class="login-status" id="loginStatus">
                    <span>✅ Logged in as: <span class="user" id="loggedUser">Loading...</span></span>
                    <button class="logout-btn" onclick="logout()">Logout</button>
                </div>
                
                <div class="login-input" id="loginInput">
                    <input type="text" id="phoneInput" placeholder="+917970462807" value="+917970462807">
                    <button class="login-btn" onclick="sendOTP()">📤 Send OTP</button>
                </div>
                
                <div class="otp-section" id="otpSection">
                    <div class="otp-input">
                        <input type="text" id="otpInput" placeholder="Enter OTP" maxlength="6" autocomplete="one-time-code">
                        <button class="verify-btn" onclick="verifyOTP()">✅ Verify</button>
                    </div>
                    <div class="otp-info">
                        📱 Check your Telegram app for verification code
                        <br>
                        <button class="resend-btn" onclick="sendOTP()">🔄 Resend OTP</button>
                    </div>
                </div>
                
                <div class="status-text" id="statusText">💡 Enter phone number and click Send OTP</div>
            </div>

            <div class="auto-check-section">
                <div class="auto-check-header">
                    <h3>⏱️ Auto Token Check</h3>
                    <div class="auto-check-controls">
                        <button class="auto-check-btn" onclick="startAutoCheck()">▶️ Start</button>
                        <button class="auto-check-btn" onclick="stopAutoCheck()">⏹️ Stop</button>
                        <button class="auto-check-btn" onclick="checkNow()">🔄 Check Now</button>
                    </div>
                </div>
                <div class="timer-display" id="timerDisplay">⏳ Not Running</div>
                <div style="text-align:center;color:rgba(255,255,255,0.3);font-size:12px;">
                    <span id="checkCount">Checks: 0</span> | 
                    <span id="lastCheck">Last: Never</span>
                </div>
            </div>

            <div class="tokens-section">
                <h3>📋 Captured Tokens</h3>
                <div id="tokensList">
                    <div style="color:rgba(255,255,255,0.3);text-align:center;padding:20px;">
                        No tokens captured yet. Login to start capturing.
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = '';
        let checkInterval = null;
        let isRunning = false;
        let checkCount = 0;
        let pendingPhone = null;
        let pendingPhoneCodeHash = null;

        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast show ' + type;
            setTimeout(() => { toast.className = 'toast'; }, 5000);
        }

        async function checkLoginStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                if (data.logged_in && data.username) {
                    document.getElementById('loginStatus').classList.add('active');
                    document.getElementById('loggedUser').textContent = data.username || data.phone;
                    document.getElementById('loginInput').style.display = 'none';
                    document.getElementById('otpSection').classList.remove('active');
                    showToast('✅ Already logged in!', 'success');
                    loadTokens();
                } else {
                    document.getElementById('loginStatus').classList.remove('active');
                    document.getElementById('loginInput').style.display = 'flex';
                }
            } catch (error) {
                console.error('Status check error:', error);
            }
        }

        async function logout() {
            try {
                await fetch('/api/logout', { method: 'POST' });
                document.getElementById('loginStatus').classList.remove('active');
                document.getElementById('loginInput').style.display = 'flex';
                document.getElementById('tokensList').innerHTML = '<div style="color:rgba(255,255,255,0.3);text-align:center;padding:20px;">Logged out. Login to start capturing.</div>';
                showToast('✅ Logged out successfully', 'success');
            } catch (error) {
                showToast('❌ Logout failed', 'error');
            }
        }

        async function sendOTP() {
            const phone = document.getElementById('phoneInput').value.trim();
            const status = document.getElementById('statusText');
            
            if (!phone) {
                showToast('❌ Please enter phone number', 'error');
                return;
            }
            
            status.innerHTML = '<div class="spinner"></div> Sending OTP...';
            status.className = 'status-text info';
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ phone: phone })
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '✅ ' + data.message;
                    status.className = 'status-text success';
                    showToast('✅ Already logged in!', 'success');
                    document.getElementById('otpSection').classList.remove('active');
                    document.getElementById('loginStatus').classList.add('active');
                    document.getElementById('loggedUser').textContent = data.username || phone;
                    document.getElementById('loginInput').style.display = 'none';
                    loadTokens();
                } else if (data.need_code) {
                    pendingPhone = phone;
                    pendingPhoneCodeHash = data.phone_code_hash;
                    status.innerHTML = '✅ ' + data.message + ' - Enter OTP below';
                    status.className = 'status-text success';
                    document.getElementById('otpSection').classList.add('active');
                    document.getElementById('otpInput').focus();
                    showToast('📱 OTP sent to your Telegram!', 'success');
                } else {
                    status.innerHTML = '❌ ' + data.message;
                    status.className = 'status-text error';
                    showToast('❌ ' + data.message, 'error');
                }
            } catch (error) {
                status.innerHTML = '❌ Connection error';
                status.className = 'status-text error';
                showToast('❌ Connection error', 'error');
            }
        }

        async function verifyOTP() {
            const code = document.getElementById('otpInput').value.trim();
            const status = document.getElementById('statusText');
            
            if (!code) {
                showToast('❌ Please enter OTP', 'error');
                return;
            }
            
            if (!pendingPhone || !pendingPhoneCodeHash) {
                showToast('❌ Please send OTP first', 'error');
                return;
            }
            
            status.innerHTML = '<div class="spinner"></div> Verifying OTP...';
            status.className = 'status-text info';
            
            try {
                const response = await fetch('/api/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        phone: pendingPhone, 
                        code: code,
                        phone_code_hash: pendingPhoneCodeHash 
                    })
                });
                const data = await response.json();
                
                if (data.success) {
                    status.innerHTML = '✅ ' + data.message;
                    status.className = 'status-text success';
                    showToast('✅ Login successful!', 'success');
                    document.getElementById('otpSection').classList.remove('active');
                    document.getElementById('otpInput').value = '';
                    document.getElementById('loginStatus').classList.add('active');
                    document.getElementById('loggedUser').textContent = data.username || pendingPhone;
                    document.getElementById('loginInput').style.display = 'none';
                    loadTokens();
                } else {
                    status.innerHTML = '❌ ' + data.message;
                    status.className = 'status-text error';
                    showToast('❌ ' + data.message, 'error');
                    if (data.message.includes('expired')) {
                        document.getElementById('otpSection').classList.remove('active');
                        setTimeout(() => {
                            sendOTP();
                        }, 2000);
                    }
                }
            } catch (error) {
                status.innerHTML = '❌ Connection error';
                status.className = 'status-text error';
                showToast('❌ Connection error', 'error');
            }
        }

        async function loadTokens() {
            try {
                const response = await fetch('/api/tokens');
                const data = await response.json();
                const container = document.getElementById('tokensList');
                if (!data.tokens || data.tokens.length === 0) {
                    container.innerHTML = '<div style="color:rgba(255,255,255,0.3);text-align:center;padding:20px;">No tokens captured yet.</div>';
                    return;
                }
                let html = '';
                data.tokens.forEach((token, index) => {
                    html += `<div class="token-item" onclick="toggleJWT(${index})">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <div class="uid">🆔 ${token.uid || 'N/A'}</div>
                                <div class="name">👤 ${token.name || 'Unknown'}</div>
                                <div class="time">📅 ${token.captured_at || 'N/A'}</div>
                            </div>
                            <span class="badge">JWT ✓</span>
                        </div>
                        <div class="jwt-display" id="jwt_${index}">
                            <strong>JWT Token:</strong><br>
                            ${token.jwt || 'No JWT'}
                            <br><br>
                            <button onclick="event.stopPropagation();copyJWT('${token.jwt || ''}')" style="padding:5px 15px;background:rgba(255,107,53,0.2);border:1px solid #ff6b35;border-radius:8px;color:#fff;cursor:pointer;">📋 Copy</button>
                        </div>
                    </div>`;
                });
                container.innerHTML = html;
            } catch (error) { console.error('Load tokens error:', error); }
        }

        function toggleJWT(index) {
            const el = document.getElementById(`jwt_${index}`);
            el.classList.toggle('active');
        }

        function copyJWT(jwt) {
            navigator.clipboard.writeText(jwt).then(() => {
                showToast('✅ JWT copied to clipboard!', 'success');
            }).catch(() => {
                showToast('❌ Failed to copy', 'error');
            });
        }

        async function startAutoCheck() {
            if (isRunning) { showToast('⚠️ Already running', 'error'); return; }
            const minutes = parseInt(prompt('Enter check interval in minutes (e.g., 10):', '10'));
            if (!minutes || minutes < 1) { showToast('❌ Invalid minutes', 'error'); return; }
            
            const response = await fetch('/api/start-check', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                isRunning = true;
                document.getElementById('timerDisplay').textContent = `⏱️ Running (${minutes} min interval)`;
                document.querySelector('.auto-check-btn.running')?.classList.remove('running');
                document.querySelectorAll('.auto-check-btn')[0].classList.add('running');
                showToast(`✅ Auto check started (${minutes} min interval)`, 'success');
                checkNow();
                
                if (checkInterval) clearInterval(checkInterval);
                checkInterval = setInterval(() => { checkNow(); }, minutes * 60 * 1000);
            }
        }

        function stopAutoCheck() {
            fetch('/api/stop-check', { method: 'POST' });
            if (checkInterval) { clearInterval(checkInterval); checkInterval = null; }
            isRunning = false;
            document.getElementById('timerDisplay').textContent = '⏳ Stopped';
            document.querySelector('.auto-check-btn.running')?.classList.remove('running');
            showToast('⏹️ Auto check stopped', 'info');
        }

        async function checkNow() {
            checkCount++;
            document.getElementById('checkCount').textContent = `Checks: ${checkCount}`;
            document.getElementById('lastCheck').textContent = `Last: ${new Date().toLocaleTimeString()}`;
            try {
                const response = await fetch('/api/check-token');
                const data = await response.json();
                if (data.new_token) {
                    showToast('🔑 New token captured!', 'success');
                    loadTokens();
                }
            } catch (error) { console.error('Check error:', error); }
        }

        // Enter key support
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                const phoneInput = document.getElementById('phoneInput');
                const otpInput = document.getElementById('otpInput');
                if (document.activeElement === phoneInput) sendOTP();
                else if (document.activeElement === otpInput) verifyOTP();
            }
        });

        document.addEventListener('DOMContentLoaded', function() {
            checkLoginStatus();
            showToast('🔥 Welcome! Enter phone and click Send OTP', 'success');
        });
    </script>
</body>
</html>
'''

# ==================== FIXED TELEGRAM FUNCTIONS ====================
async def do_login(phone, code=None, phone_code_hash=None):
    try:
        # Check if we have a pending client
        client = None
        phone_code_hash_to_use = phone_code_hash
        
        if phone in pending_data:
            client = pending_data[phone].get('client')
            phone_code_hash_to_use = pending_data[phone].get('phone_code_hash')
        
        if client is None:
            session_str = sessions_store.get(phone)
            if session_str:
                client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
            else:
                client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
        
        # Check if already authorized
        if await client.is_user_authorized():
            me = await client.get_me()
            sessions_store[phone] = client.session.save()
            if phone in pending_data:
                del pending_data[phone]
            return {"success": True, "message": f"Already logged in as {me.first_name}", "username": me.username}
        
        # If code provided, verify
        if code and phone_code_hash_to_use:
            try:
                await client.sign_in(phone, code, phone_code_hash=phone_code_hash_to_use)
                me = await client.get_me()
                sessions_store[phone] = client.session.save()
                if phone in pending_data:
                    del pending_data[phone]
                return {"success": True, "message": f"Logged in as {me.first_name}", "username": me.username}
            except errors.rpcerrorlist.PhoneCodeInvalidError:
                return {"success": False, "message": "Invalid verification code"}
            except errors.rpcerrorlist.PhoneCodeExpiredError:
                return {"success": False, "message": "Verification code expired. Please request new OTP."}
            except errors.rpcerrorlist.SessionPasswordNeededError:
                return {"success": False, "message": "2FA is enabled. Please enter your password."}
            except Exception as e:
                return {"success": False, "message": str(e)}
        else:
            # Send code request
            try:
                send_code_result = await client.send_code_request(phone)
                phone_code_hash = send_code_result.phone_code_hash
                pending_data[phone] = {"client": client, "phone_code_hash": phone_code_hash}
                return {"success": False, "need_code": True, "message": "OTP sent to Telegram", "phone_code_hash": phone_code_hash}
            except errors.rpcerrorlist.PhoneNumberInvalidError:
                return {"success": False, "message": "Invalid phone number"}
            except errors.rpcerrorlist.FloodWaitError as e:
                return {"success": False, "message": f"Too many attempts. Please wait {e.seconds} seconds."}
            except Exception as e:
                return {"success": False, "message": str(e)}
            
    except errors.rpcerrorlist.PhoneNumberInvalidError:
        return {"success": False, "message": "Invalid phone number"}
    except errors.rpcerrorlist.PhoneCodeInvalidError:
        return {"success": False, "message": "Invalid verification code"}
    except errors.rpcerrorlist.PhoneCodeExpiredError:
        return {"success": False, "message": "Verification code expired. Please request new OTP."}
    except Exception as e:
        return {"success": False, "message": str(e)}

async def do_capture_token():
    try:
        if not sessions_store:
            return {"success": False, "message": "Not logged in"}
        
        phone = list(sessions_store.keys())[0]
        session_str = sessions_store[phone]
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        
        await client.connect()
        
        if not await client.is_user_authorized():
            return {"success": False, "message": "Session expired"}
        
        await client.send_message(f"@{TARGET_BOT}", "/start")
        await asyncio.sleep(2)
        
        async for message in client.iter_messages(f"@{TARGET_BOT}", limit=10):
            if message.text and "ɴᴇᴡ ʟᴏɢɪɴ ᴄᴀᴘᴛᴜʀᴇᴅ" in message.text:
                token_match = re.search(r'ᴀᴄᴄᴇss ᴛᴏᴋᴇɴ\s*`([a-f0-9]+)`', message.text, re.I)
                open_id_match = re.search(r'ᴏᴘᴇɴ ɪᴅ\s*`([a-f0-9]+)`', message.text, re.I)
                
                if token_match:
                    access_token = token_match.group(1)
                    open_id = open_id_match.group(1) if open_id_match else None
                    
                    for token in tokens_store:
                        if token.get('access_token') == access_token:
                            return {"success": True, "message": "Token already captured", "new": False}
                    
                    jwt = None
                    uid = None
                    name = None
                    
                    try:
                        response = requests.get(f"{JWT_API}?access_token={access_token}", timeout=30)
                        if response.status_code == 200:
                            data = response.json()
                            jwt = data.get('token')
                            uid = data.get('account_uid') or data.get('Uid')
                            payload = data.get('jwt_decoded', {}).get('payload', {})
                            name = payload.get('nickname')
                            if name:
                                try:
                                    name = base64.b64decode(name).decode('utf-8')
                                except:
                                    pass
                    except Exception as e:
                        print(f"JWT API error: {e}")
                    
                    token_data = {
                        "open_id": open_id,
                        "access_token": access_token,
                        "uid": uid,
                        "name": name,
                        "jwt": jwt,
                        "captured_at": datetime.now().isoformat()
                    }
                    tokens_store.append(token_data)
                    
                    return {"success": True, "message": "Token captured!", "new": True, "token": token_data}
        
        return {"success": True, "message": "No new token found", "new": False}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

# ==================== FLASK ROUTES ====================
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    phone = list(sessions_store.keys())[0] if sessions_store else None
    return jsonify({
        "status": "ok",
        "logged_in": len(sessions_store) > 0,
        "phone": phone,
        "username": "Logged In" if sessions_store else None,
        "tokens_count": len(tokens_store),
        "sessions_count": len(sessions_store),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/logout', methods=['POST'])
def api_logout():
    sessions_store.clear()
    pending_data.clear()
    return jsonify({"success": True, "message": "Logged out"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "message": "Phone required"}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_login(phone))
    return jsonify(result)

@app.route('/api/verify', methods=['POST'])
def api_verify():
    data = request.json
    phone = data.get('phone')
    code = data.get('code')
    phone_code_hash = data.get('phone_code_hash')
    
    if not phone or not code:
        return jsonify({"success": False, "message": "Phone and code required"}), 400
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_login(phone, code, phone_code_hash))
    return jsonify(result)

@app.route('/api/check-token')
def api_check_token():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(do_capture_token())
    return jsonify(result)

@app.route('/api/tokens')
def api_tokens():
    return jsonify({"success": True, "tokens": tokens_store})

@app.route('/api/start-check', methods=['POST'])
def api_start_check():
    return jsonify({"success": True, "message": "Auto-check started"})

@app.route('/api/stop-check', methods=['POST'])
def api_stop_check():
    return jsonify({"success": True, "message": "Auto-check stopped"})

# ==================== FOR VERCEL ====================
def handler(request, context):
    return app(request, context)

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("🔥 FF TOKEN MANAGER - Vercel Compatible")
    print("=" * 60)
    print(f"📱 Phone: {USER_PHONE}")
    print(f"🤖 Target Bot: @{TARGET_BOT}")
    print(f"🔑 JWT API: {JWT_API}")
    print("=" * 60)
    print("🌐 Server running at http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)