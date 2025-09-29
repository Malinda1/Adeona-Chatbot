// Enhanced Chatbot frontend logic with typewriter effect
class AdeonaChatbot {
    constructor() {
        this.apiBase = window.location.origin + '/api/v1';
        this.sessionId = this.generateSessionId();
        this.isOpen = false;
        this.isTyping = false;
        this.currentAudio = null;
        this.typewriterSpeed = 50; // Milliseconds between each letter
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeChat();
        this.addCustomStyles();
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
            
            // Add bot response with typewriter effect
            await this.addMessageWithTypewriter(response.response, 'bot');
            
            // Play audio if available
            if (response.audio_url) {
                this.playAudio(response.audio_url);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideTyping();
            await this.addMessageWithTypewriter('I apologize, but I\'m experiencing technical difficulties. Please try again or contact our support team at (+94) 117 433 3333.', 'bot');
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
    
    // NEW: Typewriter effect for bot messages
    async addMessageWithTypewriter(text, sender) {
        if (sender !== 'bot') {
            this.addMessage(text, sender);
            return;
        }
        
        // Create message structure
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = 'AI';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.getCurrentTime();
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        // Format the text for display
        const formattedHTML = this.formatBotMessage(text);
        
        // Create a temporary div to parse the HTML
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = formattedHTML;
        
        // If the message contains special formatting (contact info, confirmations, etc.)
        if (this.hasSpecialFormatting(text)) {
            // For formatted content, show it all at once but with a delay
            await this.sleep(800);
            contentDiv.innerHTML = formattedHTML;
            contentDiv.appendChild(timeSpan);
        } else {
            // For regular text, use typewriter effect
            await this.typewriterEffect(contentDiv, text);
            contentDiv.appendChild(timeSpan);
        }
        
        this.scrollToBottom();
    }
    
    // Check if message has special formatting
    hasSpecialFormatting(text) {
        return this.isContactInfo(text) || 
               this.isConfirmationDetails(text) || 
               text.includes('•') ||
               text.includes('Phone:') ||
               text.includes('Email:') ||
               text.includes('User ID:');
    }
    
    // Typewriter effect implementation - LETTER BY LETTER
    async typewriterEffect(container, text) {
        const characters = text.split('');
        let currentText = '';
        
        // Create paragraph for typewriter text
        const paragraph = document.createElement('p');
        paragraph.className = 'chat-paragraph typewriter-text';
        container.appendChild(paragraph);
        
        for (let i = 0; i < characters.length; i++) {
            currentText += characters[i];
            paragraph.textContent = currentText;
            
            // Scroll to bottom as text appears
            this.scrollToBottom();
            
            // Wait between characters
            if (i < characters.length - 1) {
                await this.sleep(this.typewriterSpeed);
            }
        }
        
        // Remove typewriter class after completion
        setTimeout(() => {
            paragraph.classList.remove('typewriter-text');
        }, 100);
    }
    
    // Sleep function for delays
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Enhanced message formatting for better readability
    formatBotMessage(text) {
        // Clean up the text first
        let formattedText = text.replace(/\*\*\*/g, ''); // Remove triple asterisks
        formattedText = formattedText.replace(/\*\*/g, ''); // Remove double asterisks
        formattedText = formattedText.replace(/\* /g, '• '); // Convert * to bullet points
        
        // Split into sections for better formatting
        const sections = formattedText.split(/\n\n|\n(?=[A-Z])/);
        let htmlContent = '';
        
        for (let section of sections) {
            section = section.trim();
            if (!section) continue;
            
            // Check if it's a contact information section
            if (this.isContactInfo(section)) {
                htmlContent += this.formatContactInfo(section);
            }
            // Check if it's a confirmation details section
            else if (this.isConfirmationDetails(section)) {
                htmlContent += this.formatConfirmationDetails(section);
            }
            // Check if it's a bullet list
            else if (section.includes('•')) {
                htmlContent += this.formatBulletList(section);
            }
            // Regular paragraph
            else {
                htmlContent += `<p class="chat-paragraph">${this.formatInlineElements(section)}</p>`;
            }
        }
        
        return htmlContent || `<p class="chat-paragraph">${this.formatInlineElements(formattedText)}</p>`;
    }
    
    isContactInfo(text) {
        return text.includes('Phone:') && text.includes('Email:') || text.includes('(+94)') && text.includes('@');
    }
    
    isConfirmationDetails(text) {
        return text.includes('User ID:') || text.includes('Details Confirmed:') || text.includes('Name:') && text.includes('Email:') && text.includes('Phone:');
    }
    
    formatContactInfo(text) {
        let html = '<div class="contact-info-section">';
        html += '<div class="contact-info-title">Contact Information</div>';
        html += '<div class="contact-details">';
        
        // Extract phone
        const phoneMatch = text.match(/Phone:\s*([^*\n]+)/);
        if (phoneMatch) {
            const phone = phoneMatch[1].trim();
            html += `<div class="contact-item">
                <span class="contact-label">📞 Phone:</span>
                <a href="tel:${phone}" class="contact-value">${phone}</a>
            </div>`;
        }
        
        // Extract email
        const emailMatch = text.match(/Email:\s*([^*\n]+)/);
        if (emailMatch) {
            const email = emailMatch[1].trim();
            html += `<div class="contact-item">
                <span class="contact-label">✉️ Email:</span>
                <a href="mailto:${email}" class="contact-value">${email}</a>
            </div>`;
        }
        
        // Extract website
        const websiteMatch = text.match(/(https?:\/\/[^\s,]+)/);
        if (websiteMatch) {
            const website = websiteMatch[1];
            html += `<div class="contact-item">
                <span class="contact-label">🌐 Website:</span>
                <a href="${website}" target="_blank" class="contact-value">${website}</a>
            </div>`;
        }
        
        html += '</div></div>';
        return html;
    }
    
    formatConfirmationDetails(text) {
        let html = '<div class="confirmation-section">';
        html += '<div class="confirmation-title">✅ Confirmation Details</div>';
        html += '<div class="confirmation-details">';
        
        // Split by lines and format each detail
        const lines = text.split(/\n|-/).filter(line => line.trim());
        
        for (let line of lines) {
            line = line.trim();
            if (line.includes(':')) {
                const [label, ...valueParts] = line.split(':');
                const value = valueParts.join(':').trim();
                
                if (label.toLowerCase().includes('user id')) {
                    html += `<div class="detail-item important">
                        <span class="detail-label">${label.trim()}:</span>
                        <span class="detail-value user-id">${value}</span>
                    </div>`;
                } else if (value) {
                    html += `<div class="detail-item">
                        <span class="detail-label">${label.trim()}:</span>
                        <span class="detail-value">${value}</span>
                    </div>`;
                }
            } else if (line.includes('IMPORTANT')) {
                html += `<div class="important-note">⚠️ ${line}</div>`;
            } else if (line.trim().length > 0) {
                html += `<div class="detail-note">${line}</div>`;
            }
        }
        
        html += '</div></div>';
        return html;
    }
    
    formatBulletList(text) {
        const lines = text.split('\n');
        let html = '<div class="bullet-list">';
        
        for (let line of lines) {
            line = line.trim();
            if (line.startsWith('•')) {
                html += `<div class="bullet-item">
                    <span class="bullet">•</span>
                    <span class="bullet-text">${line.substring(1).trim()}</span>
                </div>`;
            } else if (line && !line.startsWith('•')) {
                html += `<p class="list-intro">${this.formatInlineElements(line)}</p>`;
            }
        }
        
        html += '</div>';
        return html;
    }
    
    formatInlineElements(text) {
        // Convert URLs to clickable links
        text = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="inline-link">$1</a>');
        
        // Convert phone numbers to clickable links
        text = text.replace(/(\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{3,4})/g, '<a href="tel:$1" class="inline-phone">$1</a>');
        
        // Convert email addresses to clickable links
        text = text.replace(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, '<a href="mailto:$1" class="inline-email">$1</a>');
        
        return text;
    }
    
    // Regular addMessage method for user messages and fallback
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        avatarDiv.innerHTML = sender === 'user' ? 'U' : 'AI';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        if (sender === 'bot') {
            // Use enhanced formatting for bot messages
            contentDiv.innerHTML = this.formatBotMessage(text);
        } else {
            // Simple formatting for user messages
            const textP = document.createElement('p');
            textP.textContent = text;
            contentDiv.appendChild(textP);
        }
        
        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.getCurrentTime();
        
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
    
    // Add custom styles for enhanced formatting
    addCustomStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Enhanced message formatting styles */
            .chat-paragraph {
                margin: 0 0 12px 0;
                line-height: 1.5;
                color: inherit;
            }
            
            .contact-info-section {
                background: rgba(0, 123, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                border-left: 3px solid var(--primary-blue);
            }
            
            .contact-info-title {
                font-weight: 600;
                color: var(--primary-blue);
                margin-bottom: 8px;
                font-size: 14px;
            }
            
            .contact-details {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .contact-item {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13px;
            }
            
            .contact-label {
                font-weight: 500;
                min-width: 60px;
                font-size: 12px;
            }
            
            .contact-value {
                color: var(--primary-blue);
                text-decoration: none;
                font-weight: 500;
            }
            
            .contact-value:hover {
                text-decoration: underline;
            }
            
            .confirmation-section {
                background: rgba(40, 167, 69, 0.1);
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                border-left: 3px solid #28a745;
            }
            
            .confirmation-title {
                font-weight: 600;
                color: #28a745;
                margin-bottom: 10px;
                font-size: 14px;
            }
            
            .confirmation-details {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .detail-item {
                display: flex;
                justify-content: space-between;
                padding: 4px 0;
                font-size: 13px;
                border-bottom: 1px solid rgba(0,0,0,0.05);
            }
            
            .detail-item:last-child {
                border-bottom: none;
            }
            
            .detail-item.important {
                background: rgba(255, 193, 7, 0.15);
                padding: 6px 8px;
                border-radius: 4px;
                border-bottom: none;
                margin: 4px 0;
            }
            
            .detail-label {
                font-weight: 500;
                color: #666;
                min-width: 80px;
            }
            
            .detail-value {
                font-weight: 500;
                text-align: right;
                flex: 1;
                word-break: break-word;
            }
            
            .user-id {
                background: #ffc107;
                color: #000;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: monospace;
                font-size: 12px;
            }
            
            .important-note {
                background: rgba(255, 193, 7, 0.2);
                padding: 8px;
                border-radius: 4px;
                margin: 6px 0;
                font-size: 13px;
                font-weight: 500;
                color: #856404;
            }
            
            .detail-note {
                font-size: 13px;
                color: #666;
                font-style: italic;
                margin: 4px 0;
            }
            
            .bullet-list {
                margin: 8px 0;
            }
            
            .list-intro {
                margin-bottom: 8px;
                font-weight: 500;
            }
            
            .bullet-item {
                display: flex;
                align-items: flex-start;
                gap: 8px;
                margin: 6px 0;
                padding-left: 4px;
            }
            
            .bullet {
                color: var(--primary-blue);
                font-weight: bold;
                font-size: 16px;
                line-height: 1.2;
                margin-top: 1px;
            }
            
            .bullet-text {
                flex: 1;
                line-height: 1.4;
                font-size: 14px;
            }
            
            .inline-link {
                color: var(--primary-blue);
                text-decoration: underline;
                font-weight: 500;
            }
            
            .inline-phone {
                color: #28a745;
                text-decoration: none;
                font-weight: 500;
            }
            
            .inline-phone:hover {
                text-decoration: underline;
            }
            
            .inline-email {
                color: var(--primary-purple);
                text-decoration: none;
                font-weight: 500;
            }
            
            .inline-email:hover {
                text-decoration: underline;
            }
            
            /* User message styles adjustment */
            .user-message .message-content {
                color: white;
            }
            
            .user-message .contact-value,
            .user-message .inline-link,
            .user-message .inline-phone,
            .user-message .inline-email {
                color: rgba(255, 255, 255, 0.9);
            }
            
            /* Typewriter effect cursor */
            .typewriter-text::after {
                content: '|';
                animation: blink 1s infinite;
            }
            
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
            
            /* Responsive adjustments */
            @media (max-width: 480px) {
                .contact-item,
                .detail-item {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 2px;
                }
                
                .detail-value {
                    text-align: left;
                }
                
                .contact-label,
                .detail-label {
                    min-width: unset;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // System message for connection status
    addSystemMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.style.textAlign = 'center';
        messageDiv.style.fontSize = '12px';
        messageDiv.style.color = '#666';
        messageDiv.style.fontStyle = 'italic';
        messageDiv.style.margin = '10px 0';
        messageDiv.style.opacity = '0';
        messageDiv.style.animation = 'fadeIn 0.5s ease forwards';
        
        const textP = document.createElement('p');
        textP.textContent = text;
        
        messageDiv.appendChild(textP);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    // Connection monitoring
    monitorConnection() {
        window.addEventListener('online', () => {
            this.addSystemMessage('Connection restored');
        });
        
        window.addEventListener('offline', () => {
            this.addSystemMessage('Connection lost - please check your internet connection');
        });
    }
    
    // Initialize with enhanced features
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

