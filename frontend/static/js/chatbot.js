// Chatbot frontend logic
class AdeonaChatbot {
    constructor() {
        this.apiBase = window.location.origin + '/api/v1';
        this.sessionId = this.generateSessionId();
        this.isOpen = false;
        this.isTyping = false;
        this.currentAudio = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeChat();
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeElements() {
        this.chatToggle = document.getElementById('chat-toggle');
        this.chatWindow = document.getElementById('chat-window');
        this.chatClose = document.getElementById('chat-close');
        this.chatMinimize = document.getElementById('chat-minimize');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.chatSend = document.getElementById('chat-send');
        this.typingIndicator = document.getElementById('typing-indicator');
    }
    
    attachEventListeners() {
        // Toggle chat window
        this.chatToggle.addEventListener('click', () => this.toggleChat());
        
        // Close chat
        this.chatClose.addEventListener('click', () => this.closeChat());
        
        // Minimize chat
        this.chatMinimize.addEventListener('click', () => this.minimizeChat());
        
        // Send message
        this.chatSend.addEventListener('click', () => this.sendMessage());
        
        // Enter key to send
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Input validation
        this.chatInput.addEventListener('input', () => {
            const message = this.chatInput.value.trim();
            this.chatSend.disabled = !message || this.isTyping;
        });
        
        // Click outside to close (optional)
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.chatbot-container') && this.isOpen) {
                // Uncomment to enable click-outside-to-close
                // this.closeChat();
            }
        });
    }
    
    initializeChat() {
        // Set initial state
        this.chatSend.disabled = true;
        
        // Add welcome message with delay for better UX
        setTimeout(() => {
            this.addWelcomeMessage();
        }, 500);
    }
    
    addWelcomeMessage() {
        // The welcome message is already in HTML, so we can skip adding it again
        // Just scroll to bottom in case there are multiple messages
        this.scrollToBottom();
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        this.chatWindow.classList.add('active');
        this.chatToggle.style.transform = 'scale(0.8)';
        this.isOpen = true;
        
        // Focus on input
        setTimeout(() => {
            this.chatInput.focus();
        }, 300);
        
        // Update icon to close icon
        this.updateToggleIcon(true);
    }
    
    closeChat() {
        this.chatWindow.classList.remove('active');
        this.chatToggle.style.transform = 'scale(1)';
        this.isOpen = false;
        
        // Update icon to chat icon
        this.updateToggleIcon(false);
        
        // Stop any playing audio
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
    }
    
    minimizeChat() {
        this.closeChat();
    }
    
    updateToggleIcon(isOpen) {
        const icon = this.chatToggle.querySelector('.chat-icon');
        if (isOpen) {
            icon.innerHTML = `
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            `;
        } else {
            icon.innerHTML = `
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            `;
        }
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;
        
        // Clear input immediately
        this.chatInput.value = '';
        this.chatSend.disabled = true;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Show typing indicator
        this.showTyping();
        
        try {
            // Send message to API
            const response = await this.callChatAPI(message);
            
            // Hide typing indicator
            this.hideTyping();
            
            // Add bot response
            this.addMessage(response.response, 'bot');
            
            // Play audio if available
            if (response.audio_url) {
                this.playAudio(response.audio_url);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTyping();
            this.addMessage('I apologize, but I\'m experiencing technical difficulties. Please try again or contact our support team at (+94) 117 433 3333.', 'bot');
        }
        
        // Re-enable input
        this.chatSend.disabled = false;
        this.chatInput.focus();
    }
    
    async callChatAPI(message) {
        const response = await fetch(`${this.apiBase}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: this.sessionId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    }
    
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? 'U' : 'AI';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textP = document.createElement('p');
        textP.textContent = text;
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.getCurrentTime();
        
        contentDiv.appendChild(textP);
        contentDiv.appendChild(timeSpan);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    showTyping() {
        this.isTyping = true;
        this.typingIndicator.classList.add('active');
        this.scrollToBottom();
    }
    
    hideTyping() {
        this.isTyping = false;
        this.typingIndicator.classList.remove('active');
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }
    
    getCurrentTime() {
        const now = new Date();
        const hours = now.getHours().toString().padStart(2, '0');
        const minutes = now.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    
    playAudio(audioUrl) {
        try {
            // Stop current audio if playing
            if (this.currentAudio) {
                this.currentAudio.pause();
            }
            
            // Create new audio element
            this.currentAudio = new Audio(audioUrl);
            this.currentAudio.volume = 0.8;
            
            // Play the audio
            this.currentAudio.play().catch(error => {
                console.log('Audio playback failed:', error);
                // Silently fail - audio is optional
            });
            
        } catch (error) {
            console.log('Audio error:', error);
            // Silently fail - audio is optional
        }
    }
    
    // Utility methods for better user experience
    handleNetworkError() {
        this.addMessage('Connection error. Please check your internet connection and try again.', 'bot');
    }
    
    handleTimeout() {
        this.addMessage('Request timeout. Please try again.', 'bot');
    }
    
    // Add loading states and better error handling
    setLoadingState(isLoading) {
        if (isLoading) {
            this.chatSend.disabled = true;
            this.chatInput.disabled = true;
            this.showTyping();
        } else {
            this.chatSend.disabled = false;
            this.chatInput.disabled = false;
            this.hideTyping();
        }
    }
    
    // Enhanced message formatting for better readability
    formatMessage(text) {
        // Convert URLs to clickable links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        text = text.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
        
        // Convert phone numbers to clickable links
        const phoneRegex = /(\+\d{1,3}\s?\d{10,}|\(\+\d{1,3}\)\s?\d{3}\s?\d{3}\s?\d{3,4})/g;
        text = text.replace(phoneRegex, '<a href="tel:$1">$1</a>');
        
        // Convert email addresses to clickable links
        const emailRegex = /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g;
        text = text.replace(emailRegex, '<a href="mailto:$1">$1</a>');
        
        return text;
    }
    
    // Add enhanced message with formatting
    addFormattedMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? 'U' : 'AI';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textP = document.createElement('p');
        textP.innerHTML = this.formatMessage(text);
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.getCurrentTime();
        
        contentDiv.appendChild(textP);
        contentDiv.appendChild(timeSpan);
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    // Override the addMessage method to use formatted version
    addMessage(text, sender) {
        this.addFormattedMessage(text, sender);
    }
    
    // Add method to handle special message types
    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.style.textAlign = 'center';
        messageDiv.style.fontSize = '12px';
        messageDiv.style.color = '#666';
        messageDiv.style.fontStyle = 'italic';
        messageDiv.style.margin = '10px 0';
        
        const textP = document.createElement('p');
        textP.textContent = text;
        
        messageDiv.appendChild(textP);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    // Add connection status monitoring
    monitorConnection() {
        window.addEventListener('online', () => {
            this.addSystemMessage('Connection restored');
        });
        
        window.addEventListener('offline', () => {
            this.addSystemMessage('Connection lost - please check your internet connection');
        });
    }
    
    // Initialize connection monitoring
    init() {
        this.monitorConnection();
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // ESC to close chat
            if (e.key === 'Escape' && this.isOpen) {
                this.closeChat();
            }
            
            // Ctrl/Cmd + K to open chat
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.toggleChat();
            }
        });
        
        // Add smooth animations
        this.addCustomStyles();
    }
    
    addCustomStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .system-message {
                opacity: 0;
                animation: fadeIn 0.5s ease forwards;
            }
            
            @keyframes fadeIn {
                to {
                    opacity: 1;
                }
            }
            
            .message-content a {
                color: inherit;
                text-decoration: underline;
            }
            
            .message-content a:hover {
                text-decoration: none;
            }
            
            .user-message .message-content a {
                color: rgba(255, 255, 255, 0.9);
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const chatbot = new AdeonaChatbot();
    chatbot.init();
    
    // Make chatbot globally accessible for debugging
    window.chatbot = chatbot;
});

// Add smooth scrolling for navigation links
document.addEventListener('DOMContentLoaded', () => {
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Add hero indicators functionality
document.addEventListener('DOMContentLoaded', () => {
    const indicators = document.querySelectorAll('.indicator');
    let currentIndex = 0;
    
    // Auto-rotate indicators (optional visual enhancement)
    setInterval(() => {
        indicators.forEach(indicator => indicator.classList.remove('active'));
        indicators[currentIndex].classList.add('active');
        currentIndex = (currentIndex + 1) % indicators.length;
    }, 4000);
    
    // Click handler for indicators
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            indicators.forEach(ind => ind.classList.remove('active'));
            indicator.classList.add('active');
            currentIndex = index;
        });
    });
});