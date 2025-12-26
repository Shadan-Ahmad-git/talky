// Initialize Socket.IO connection
const socket = io();

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const voiceBtn = document.getElementById('voiceBtn');
const imageBtn = document.getElementById('imageBtn');
const imageInput = document.getElementById('imageInput');
const imagePreview = document.getElementById('imagePreview');
const previewImage = document.getElementById('previewImage');
const removeImageBtn = document.getElementById('removeImage');
const voiceRecording = document.getElementById('voiceRecording');
const stopRecordingBtn = document.getElementById('stopRecording');
const cancelRecordingBtn = document.getElementById('cancelRecording');
const endAudioBtn = document.getElementById('endAudioBtn');
const processingIndicator = document.getElementById('processingIndicator');
const processingText = document.getElementById('processingText');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const newChatBtn = document.getElementById('newChatBtn');
const historyList = document.getElementById('historyList');
const toggleSidebarBtn = document.getElementById('toggleSidebar');

// State
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let currentChatId = Date.now().toString();
let chatHistory = {};
let selectedImage = null;
let currentTypingMessage = null;
let currentSessionId = null; // For Supabase storage

// Initialize
initChat();

function initChat() {
    currentChatId = Date.now().toString();
    chatHistory[currentChatId] = [];
    // Generate session ID for Supabase (use browser fingerprint or generate UUID)
    if (!currentSessionId) {
        currentSessionId = 'web_' + Date.now().toString() + '_' + Math.random().toString(36).substr(2, 9);
    }
    loadChatHistory();
}

// Show welcome message with typing animation
function showWelcomeMessage() {
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-content">
                <div class="welcome-logo">
                    <img src="/static/images/logo.png" alt="Talky" class="welcome-logo-img" onerror="this.style.display='none';">
                </div>
                <h1 id="welcomeText"></h1>
            </div>
        </div>
    `;
    
    // Type the welcome message
    const welcomeTextElement = document.getElementById('welcomeText');
    if (welcomeTextElement) {
        const welcomeText = "How can I help you today?";
        typeMessage(welcomeTextElement, welcomeText, false);
    }
}

// Socket Events
socket.on('connect', () => {
    console.log('Connected to server');
    statusDot.classList.add('connected');
    statusText.textContent = 'Connected';
    // Don't auto-load history - show welcome message by default
    // socket.emit('get_history');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    statusDot.classList.remove('connected');
    statusText.textContent = 'Disconnected';
});

socket.on('connected', (data) => {
    console.log('Connection confirmed:', data);
});

socket.on('message_response', (data) => {
    hideTyping();
    hideProcessing();
    hideSpeakingIndicator();
    
    // Show typing animation while message streams in (ChatGPT-style)
    const messageDiv = addMessage('bot', data.message, true, true);
    
    // Save to history
    chatHistory[currentChatId].push({
        type: 'bot',
        text: data.message,
        timestamp: data.timestamp
    });
    saveChatHistory();
});

socket.on('image_response', (data) => {
    hideTyping();
    hideProcessing();
    
    // Show typing animation
    const messageDiv = addMessage('bot', `**Image Analysis:**\n\n${data.description}`, true, true);
    
    chatHistory[currentChatId].push({
        type: 'bot',
        text: `Image Analysis: ${data.description}`,
        timestamp: data.timestamp
    });
    saveChatHistory();
});

socket.on('error', (data) => {
    hideTyping();
    hideProcessing();
    addMessage('bot', `Error: ${data.message}`, true);
});

// Store current audio for pause/resume functionality
let currentAudio = null;
let isAudioPaused = false;

socket.on('voice_response', (data) => {
    // Show speaking indicator while audio plays
    showSpeakingIndicator();
    
    // Stop any previous audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
    }
    
    // Play voice response automatically
    currentAudio = new Audio(`data:audio/${data.format};base64,${data.audio}`);
    isAudioPaused = false;
    
    // Update end button state
    updateEndButtonState();
    
    currentAudio.play().catch(e => {
        console.error('Error playing voice response:', e);
        hideSpeakingIndicator();
        currentAudio = null;
        updateEndButtonState();
    });
    
    // Hide indicator when audio finishes
    currentAudio.addEventListener('ended', () => {
        hideSpeakingIndicator();
        currentAudio = null;
        isAudioPaused = false;
        updateEndButtonState();
    });
    
    currentAudio.addEventListener('error', () => {
        hideSpeakingIndicator();
        currentAudio = null;
        isAudioPaused = false;
        updateEndButtonState();
    });
});

function endAudioPlayback() {
    if (!currentAudio) return;
    
    // Stop the audio completely
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
    isAudioPaused = false;
    hideSpeakingIndicator();
    updateEndButtonState();
}

function updateEndButtonState() {
    const endBtn = document.getElementById('endAudioBtn');
    if (endBtn) {
        if (currentAudio) {
            endBtn.style.display = 'flex';
        } else {
            endBtn.style.display = 'none';
        }
    }
}

socket.on('typing', (data) => {
    if (data.is_typing) {
        showTyping();
        // Don't show speaking indicator for typing - only for actual voice
    } else {
        hideTyping();
    }
});

socket.on('processing', (data) => {
    if (data.message) {
        showProcessing(data.message);
        // Don't show speaking indicator for processing - only for actual voice
    } else {
        hideProcessing();
    }
});

socket.on('history', (data) => {
    if (data.history && data.history.length > 0) {
        // Clear welcome message only if there's history
        const welcomeMsg = chatMessages.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        // Add history messages
        data.history.forEach(msg => {
            if (msg.type === 'bot' || msg.type === 'image') {
                addMessage('bot', msg.text, false);
            } else if (msg.type === 'user') {
                addMessage('user', msg.text.replace('[Voice] ', ''), false);
            }
        });
    }
    // If no history, keep welcome message visible
});

// Message Functions
function addMessage(type, text, scroll = true, isStreaming = false) {
    // Remove welcome message if present (only when actually adding a message)
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg && (type === 'user' || type === 'bot')) {
        welcomeMsg.remove();
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (type === 'user') {
        avatar.innerHTML = '<i class="fas fa-user"></i>';
    } else {
        // Use logo for bot messages
        avatar.innerHTML = '<img src="/static/images/logo.png" alt="Talky" class="message-avatar-logo" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'<i class=\\\'fas fa-comments\\\'></i>\';">';
    }
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    if (isStreaming) {
        content.innerHTML = '<span class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>';
        typeMessage(content, text, scroll);
    } else {
        // Use marked to render markdown
        if (typeof marked !== 'undefined') {
            content.innerHTML = marked.parse(text);
        } else {
            content.textContent = text;
        }
    }
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    chatMessages.appendChild(messageDiv);
    
    if (scroll) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    return messageDiv;
}

function typeMessage(element, text, scroll) {
    currentTypingMessage = element;
    
    let index = 0;
    let currentText = '';
    let lastRenderTime = performance.now();
    let animationFrameId = null;
    
    // Variable typing speeds for natural feel (smooth and realistic)
    function getTypingDelay(char, prevChar) {
        // Very fast for spaces
        if (char === ' ') return 8;
        if (char === '\n') return 20;
        // Slight pause after punctuation for natural flow
        if (/[.,!?;:]/.test(prevChar)) return 35;
        // Slight pause for punctuation itself
        if (/[.,!?;:]/.test(char)) return 30;
        // Slightly slower for capital letters (more emphasis)
        if (/[A-Z]/.test(char)) return 15;
        // Fast speed for regular characters
        return 12;
    }
    
    function typeChar(currentTime) {
        if (index < text.length) {
            const char = text[index];
            const prevChar = index > 0 ? text[index - 1] : '';
            const delay = getTypingDelay(char, prevChar);
            
            if (currentTime - lastRenderTime >= delay) {
                currentText += char;
                index++;
                
                // Remove typing indicator once we start typing
                if (element.innerHTML.includes('typing-indicator')) {
                    element.innerHTML = '';
                }
                
                // Render every character for smooth, natural typing effect
                try {
                    if (typeof marked !== 'undefined') {
                        // Use markdown parsing for better formatting
                        element.innerHTML = marked.parse(currentText);
                    } else {
                        element.textContent = currentText;
                    }
                } catch (e) {
                    element.textContent = currentText;
                }
                
                // Auto-scroll smoothly every few characters
                if (scroll && index % 3 === 0) {
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
                
                lastRenderTime = currentTime;
            }
            
            animationFrameId = requestAnimationFrame(typeChar);
        } else {
            // Finished typing - final render with markdown
            if (typeof marked !== 'undefined') {
                try {
                    element.innerHTML = marked.parse(text);
                } catch (e) {
                    element.textContent = text;
                }
            } else {
                element.textContent = text;
            }
            
            if (scroll) {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            currentTypingMessage = null;
        }
    }
    
    // Start the animation
    animationFrameId = requestAnimationFrame(typeChar);
    
    // Store animation frame ID for potential cancellation
    if (!element._animationFrameId) {
        element._animationFrameId = animationFrameId;
    }
}

function showTyping() {
    // Remove any existing typing indicator first to prevent duplicates
    hideTyping();
    
    const welcomeMsg = chatMessages.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot';
    typingDiv.id = 'typingIndicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<img src="/static/images/logo.png" alt="Talky" class="message-avatar-logo" onerror="this.style.display=\'none\'; this.parentElement.innerHTML=\'<i class=\\\'fas fa-comments\\\'></i>\';">';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = '<span class="typing-indicator"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>';
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(content);
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTyping() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function showProcessing(message) {
    processingIndicator.classList.add('active');
    processingText.textContent = message;
}

function hideProcessing() {
    processingIndicator.classList.remove('active');
    processingText.textContent = '';
}

// Speaking Indicator
function showSpeakingIndicator() {
    const header = document.querySelector('.chat-header');
    if (header && !header.querySelector('.speaking-indicator')) {
        const indicator = document.createElement('div');
        indicator.className = 'speaking-indicator';
        indicator.innerHTML = '<i class="fas fa-volume-up"></i><span>AI is speaking...</span>';
        header.appendChild(indicator);
    }
}

function hideSpeakingIndicator() {
    const indicator = document.querySelector('.speaking-indicator');
    if (indicator) {
        indicator.remove();
    }
}

// Send Message
function sendMessage() {
    const text = messageInput.value.trim();
    if (!text && !selectedImage) return;
    
    // Send image if selected
    if (selectedImage) {
        const reader = new FileReader();
        reader.onloadend = () => {
            addMessage('user', 'Image uploaded');
            socket.emit('send_image', { image: reader.result });
            clearImagePreview();
            
            chatHistory[currentChatId].push({
                type: 'user',
                text: 'Image uploaded',
                timestamp: new Date().toISOString()
            });
            saveChatHistory();
        };
        reader.readAsDataURL(selectedImage);
    }
    
    // Send text message
    if (text) {
        addMessage('user', text);
        socket.emit('send_message', { message: text });
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        chatHistory[currentChatId].push({
            type: 'user',
            text: text,
            timestamp: new Date().toISOString()
        });
        saveChatHistory();
    }
}

// Voice Response
async function generateVoiceResponse(text) {
    // This would call a voice generation endpoint
    // For now, we'll just show a visual indicator
    // You can add actual TTS integration later
}

// Event Listeners
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Voice Recording
voiceBtn.addEventListener('click', startRecording);
stopRecordingBtn.addEventListener('click', stopRecording);
cancelRecordingBtn.addEventListener('click', cancelRecording);
if (endAudioBtn) {
    endAudioBtn.addEventListener('click', endAudioPlayback);
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };
        
        // Store stream reference for cancel
        mediaRecorder.stream = stream;
        
        mediaRecorder.onstop = () => {
            // Only send if recording wasn't cancelled
            if (mediaRecorder && audioChunks.length > 0) {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onloadend = () => {
                    const base64Audio = reader.result;
                    socket.emit('send_voice', { audio: base64Audio });
                    
                    chatHistory[currentChatId].push({
                        type: 'user',
                        text: '[Voice message]',
                        timestamp: new Date().toISOString()
                    });
                    saveChatHistory();
                };
                reader.readAsDataURL(audioBlob);
            }
            
            // Stop all tracks
            if (mediaRecorder.stream) {
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        };
        
        mediaRecorder.start();
        isRecording = true;
        voiceRecording.style.display = 'flex';
        voiceBtn.style.display = 'none';
    } catch (error) {
        console.error('Error accessing microphone:', error);
        alert('Could not access microphone. Please check permissions.');
    }
}

function cancelRecording() {
    if (mediaRecorder && isRecording) {
        // Stop the media recorder
        mediaRecorder.stop();
        isRecording = false;
        
        // Clear audio chunks so nothing gets sent
        audioChunks = [];
        
        // Stop all tracks to release microphone
        if (mediaRecorder.stream) {
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        
        // Reset media recorder
        mediaRecorder = null;
        
        // Hide recording UI and show voice button
        voiceRecording.style.display = 'none';
        voiceBtn.style.display = 'block';
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        voiceRecording.style.display = 'none';
        voiceBtn.style.display = 'block';
    }
}

// Image Upload
imageBtn.addEventListener('click', () => {
    imageInput.click();
});

imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        selectedImage = file;
        const reader = new FileReader();
        reader.onloadend = () => {
            previewImage.src = reader.result;
            imagePreview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    }
});

removeImageBtn.addEventListener('click', clearImagePreview);

function clearImagePreview() {
    selectedImage = null;
    imagePreview.style.display = 'none';
    previewImage.src = '';
    imageInput.value = '';
}

// New Chat
newChatBtn.addEventListener('click', () => {
    initChat();
    showWelcomeMessage();
    updateHistoryList();
});

// Chat History
async function saveChatHistory() {
    // Ensure chatHistory[currentChatId] exists
    if (!chatHistory[currentChatId]) {
        chatHistory[currentChatId] = [];
    }
    
    // Save to localStorage as backup
    localStorage.setItem('talky_chat_history', JSON.stringify(chatHistory));
    
    // Save to Supabase - send entire chatHistory object
    if (currentSessionId) {
        try {
            // Make sure we're sending the complete, current state
            const historyToSave = JSON.parse(JSON.stringify(chatHistory));
            
            const response = await fetch('/api/chat-history', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    history: historyToSave
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Failed to save chat history to Supabase:', errorData);
            } else {
                console.log('Chat history saved successfully. Total chats:', Object.keys(chatHistory).length);
            }
        } catch (e) {
            console.error('Error saving chat history to Supabase:', e);
            // Fallback to localStorage only
        }
    }
    
    updateHistoryList();
}

async function loadChatHistory() {
    // Try to load from Supabase first
    if (currentSessionId) {
        try {
            const response = await fetch(`/api/chat-history?session_id=${currentSessionId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.history && Object.keys(data.history).length > 0) {
                    // Merge with existing chatHistory to preserve any in-memory chats
                    chatHistory = { ...chatHistory, ...data.history };
                    console.log('Loaded chat history from Supabase:', Object.keys(chatHistory).length, 'chat sessions');
                    updateHistoryList();
                    return;
                } else {
                    console.log('No history found in Supabase for session:', currentSessionId);
                }
            } else {
                console.error('Failed to load chat history from Supabase:', response.status);
            }
        } catch (e) {
            console.error('Error loading chat history from Supabase:', e);
        }
    }
    
    // Fallback to localStorage
    const saved = localStorage.getItem('talky_chat_history');
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            // Merge with existing chatHistory
            chatHistory = { ...chatHistory, ...parsed };
            console.log('Loaded chat history from localStorage:', Object.keys(chatHistory).length, 'chat sessions');
            updateHistoryList();
        } catch (e) {
            console.error('Error loading chat history:', e);
        }
    }
}

function updateHistoryList() {
    historyList.innerHTML = '';
    Object.keys(chatHistory).forEach(chatId => {
        const messages = chatHistory[chatId];
        if (messages.length > 0) {
            const firstMessage = messages[0].text.substring(0, 30);
            const item = document.createElement('div');
            item.className = 'history-item';
            if (chatId === currentChatId) {
                item.classList.add('active');
            }
            item.innerHTML = `<i class="fas fa-comment"></i><span>${firstMessage}...</span>`;
            item.addEventListener('click', () => {
                loadChat(chatId);
            });
            historyList.appendChild(item);
        }
    });
}

function loadChat(chatId) {
    currentChatId = chatId;
    chatMessages.innerHTML = '';
    
    if (chatHistory[chatId] && chatHistory[chatId].length > 0) {
        chatHistory[chatId].forEach(msg => {
            addMessage(msg.type === 'user' ? 'user' : 'bot', msg.text, false);
        });
    } else {
        showWelcomeMessage();
    }
    
    updateHistoryList();
}

// Toggle Sidebar
const sidebar = document.getElementById('sidebar');
const closeSidebarBtn = document.getElementById('closeSidebarBtn');

if (toggleSidebarBtn && sidebar) {
    toggleSidebarBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.toggle('open');
        console.log('Sidebar toggled, open:', sidebar.classList.contains('open'));
    });
}

if (closeSidebarBtn && sidebar) {
    closeSidebarBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        sidebar.classList.remove('open');
    });
}

// Close sidebar when clicking outside (on mobile)
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar) {
        if (sidebar.classList.contains('open') && 
            !sidebar.contains(e.target) && 
            toggleSidebarBtn && !toggleSidebarBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    }
});

// Show welcome message with typing animation on page load
document.addEventListener('DOMContentLoaded', () => {
    // Small delay to ensure everything is loaded
    setTimeout(() => {
        const welcomeH1 = document.querySelector('.welcome-message h1');
        if (welcomeH1 && welcomeH1.textContent.trim() === "How can I help you today?") {
            const welcomeText = welcomeH1.textContent;
            welcomeH1.textContent = '';
            welcomeH1.id = 'welcomeText';
            typeMessage(welcomeH1, welcomeText, false);
        }
    }, 300);
});

// Initialize
console.log('Talky Web UI initialized');
