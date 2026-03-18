// Content script for Gmail page - Fixed for multiple injection issues

// Check if script is already running to prevent duplicate execution
if (typeof window.phishingDetectorLoaded === 'undefined') {
    window.phishingDetectorLoaded = true;
    
    let currentEmailId = null;
    let connectionChecked = false;

    // Check connection on load
    function checkConnection() {
        chrome.runtime.sendMessage({ type: 'get_connection_status' }, (response) => {
            if (response && response.status === 'connected') {
                showConnectionStatus('connected');
            } else {
                showConnectionStatus('disconnected');
            }
            connectionChecked = true;
        });
    }

    // Show connection status in Gmail
    function showConnectionStatus(status) {
        const existing = document.getElementById('phishing-connection-status');
        if (existing) existing.remove();
        
        const statusDiv = document.createElement('div');
        statusDiv.id = 'phishing-connection-status';
        
        if (status === 'connected') {
            statusDiv.innerHTML = '🟢 Phishing Detector Connected';
            statusDiv.style.cssText = `
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: #4caf50;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-family: Arial, sans-serif;
                font-size: 12px;
                z-index: 9999;
                opacity: 0.9;
                cursor: pointer;
            `;
            
            // Auto-hide after 10 seconds if connected
            setTimeout(() => {
                if (statusDiv.parentNode) statusDiv.remove();
            }, 10000);
        } else {
            statusDiv.innerHTML = '🔴 Phishing Detector Disconnected - Click to reconnect';
            statusDiv.style.cssText = `
                position: fixed;
                bottom: 10px;
                right: 10px;
                background: #f44336;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-family: Arial, sans-serif;
                font-size: 12px;
                z-index: 9999;
                opacity: 0.9;
                cursor: pointer;
                animation: pulse 2s infinite;
            `;
            
            // Add pulse animation if not already added
            if (!document.getElementById('phishing-pulse-style')) {
                const style = document.createElement('style');
                style.id = 'phishing-pulse-style';
                style.textContent = `
                    @keyframes pulse {
                        0% { opacity: 0.9; }
                        50% { opacity: 0.5; }
                        100% { opacity: 0.9; }
                    }
                `;
                document.head.appendChild(style);
            }
            
            // Click to reconnect
            statusDiv.onclick = () => {
                chrome.runtime.sendMessage({ type: 'force_reconnect' });
                statusDiv.innerHTML = '⏳ Reconnecting...';
                setTimeout(() => checkConnection(), 2000);
            };
        }
        
        document.body.appendChild(statusDiv);
    }

    // Listen for scan results
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'scan_result') {
            showScanResult(message.result);
        }
        if (message.type === 'connection_status') {
            showConnectionStatus(message.status);
        }
    });

    function watchEmailOpens() {
        const observer = new MutationObserver((mutations) => {
            const emailArea = document.querySelector('[role="main"]');
            if (emailArea) {
                const emailId = getEmailId();
                if (emailId && emailId !== currentEmailId) {
                    currentEmailId = emailId;
                    extractAndScanEmail();
                }
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    function getEmailId() {
        const emailContainer = document.querySelector('[data-legacy-thread-id]') ||
                              document.querySelector('[data-message-id]') ||
                              document.querySelector('[data-thread-id]');
        
        if (emailContainer) {
            return emailContainer.getAttribute('data-legacy-thread-id') ||
                   emailContainer.getAttribute('data-message-id') ||
                   emailContainer.getAttribute('data-thread-id');
        }
        
        const hash = window.location.hash;
        if (hash && hash.includes('#inbox/')) {
            return hash.split('#inbox/')[1];
        }
        
        return null;
    }

    function extractEmailContent() {
        const email = {
            sender: '',
            subject: '',
            body: '',
            links: []
        };
        
        const senderElement = document.querySelector('[email]') ||
                             document.querySelector('.gD') ||
                             document.querySelector('[data-hovercard-id]');
        if (senderElement) {
            email.sender = senderElement.getAttribute('email') ||
                          senderElement.getAttribute('data-hovercard-id') ||
                          senderElement.textContent;
        }
        
        const subjectElement = document.querySelector('h2[data-thread-perm-id]') ||
                              document.querySelector('.ha') ||
                              document.querySelector('[data-subject]');
        if (subjectElement) {
            email.subject = subjectElement.textContent;
        }
        
        const bodyElement = document.querySelector('.a3s') ||
                           document.querySelector('[role="listitem"]') ||
                           document.querySelector('.ii');
        if (bodyElement) {
            email.body = bodyElement.innerText || bodyElement.textContent;
            
            const links = bodyElement.querySelectorAll('a');
            links.forEach(link => {
                if (link.href && !link.href.startsWith('#')) {
                    email.links.push({
                        text: link.textContent,
                        url: link.href
                    });
                }
            });
        }
        
        return email;
    }

    function extractAndScanEmail() {
        const email = extractEmailContent();
        if (!email.body) return;
        
        console.log('📧 Email detected:', email.subject);
        
        const emailContent = `From: ${email.sender}
Subject: ${email.subject}

${email.body}

Links:
${email.links.map(l => `- ${l.url}`).join('\n')}`;
        
        chrome.runtime.sendMessage({
            type: 'email_opened',
            emailId: currentEmailId,
            emailContent: emailContent,
            sender: email.sender,
            subject: email.subject,
            links: email.links
        }, (response) => {
            if (response && response.received) {
                showScanningIndicator();
            } else {
                showConnectionStatus('disconnected');
            }
        });
    }

    function showScanningIndicator() {
        const existing = document.getElementById('phishing-scanner-indicator');
        if (existing) existing.remove();
        
        const indicator = document.createElement('div');
        indicator.id = 'phishing-scanner-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 50px;
            font-family: Arial, sans-serif;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 10px;
            animation: slideIn 0.3s ease-out;
        `;
        
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        `;
        
        const text = document.createElement('span');
        text.textContent = '🔍 Phishing Detector scanning...';
        
        // Add animations if not already added
        if (!document.getElementById('phishing-animation-style')) {
            const style = document.createElement('style');
            style.id = 'phishing-animation-style';
            style.textContent = `
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        
        indicator.appendChild(spinner);
        indicator.appendChild(text);
        document.body.appendChild(indicator);
    }

    function showScanResult(result) {
        const indicator = document.getElementById('phishing-scanner-indicator');
        if (indicator) indicator.remove();
        
        const popup = document.createElement('div');
        popup.id = 'phishing-scan-result';
        
        let color, icon, message;
        if (result.is_phishing) {
            color = '#f44336';
            icon = '🔴';
            message = '⚠️ PHISHING DETECTED';
        } else if (result.total_confidence > 50) {
            color = '#ff9800';
            icon = '🟡';
            message = '⚠️ SUSPICIOUS EMAIL';
        } else {
            color = '#4caf50';
            icon = '🟢';
            message = '✅ SAFE EMAIL';
        }
        
        popup.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: ${color};
            color: white;
            padding: 16px 24px;
            border-radius: 12px;
            font-family: Arial, sans-serif;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            z-index: 9999;
            max-width: 350px;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Header
        const header = document.createElement('div');
        header.style.cssText = `
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        header.innerHTML = `${icon} ${message}`;
        
        // Confidence
        const confidence = document.createElement('div');
        confidence.style.cssText = `
            font-size: 14px;
            margin-bottom: 10px;
            opacity: 0.9;
        `;
        confidence.textContent = `Confidence: ${result.total_confidence.toFixed(1)}%`;
        
        // Reasons
        const reasons = document.createElement('div');
        reasons.style.cssText = `
            font-size: 13px;
            margin-bottom: 15px;
            padding-left: 20px;
        `;
        
        if (result.reasons && result.reasons.length > 0) {
            const list = document.createElement('ul');
            list.style.margin = '5px 0';
            result.reasons.slice(0, 3).forEach(reason => {
                const li = document.createElement('li');
                li.textContent = reason;
                list.appendChild(li);
            });
            reasons.appendChild(list);
        }
        
        // Buttons
        const buttons = document.createElement('div');
        buttons.style.cssText = `
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        `;
        
        const detailsBtn = document.createElement('button');
        detailsBtn.textContent = '📊 Details';
        detailsBtn.style.cssText = `
            background: rgba(255,255,255,0.2);
            border: 1px solid white;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 13px;
            transition: background 0.2s;
        `;
        detailsBtn.onmouseover = () => detailsBtn.style.background = 'rgba(255,255,255,0.3)';
        detailsBtn.onmouseout = () => detailsBtn.style.background = 'rgba(255,255,255,0.2)';
        detailsBtn.onclick = () => {
            chrome.runtime.sendMessage({
                type: 'open_desktop_app',
                view: 'details',
                emailId: currentEmailId
            });
        };
        
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = `
            background: transparent;
            border: 1px solid white;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        `;
        closeBtn.onmouseover = () => closeBtn.style.background = 'rgba(255,255,255,0.2)';
        closeBtn.onmouseout = () => closeBtn.style.background = 'transparent';
        closeBtn.onclick = () => popup.remove();
        
        buttons.appendChild(detailsBtn);
        buttons.appendChild(closeBtn);
        
        popup.appendChild(header);
        popup.appendChild(confidence);
        popup.appendChild(reasons);
        popup.appendChild(buttons);
        
        document.body.appendChild(popup);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (popup.parentNode) popup.remove();
        }, 10000);
    }

    // Check connection on load
    checkConnection();

    // Initialize
    watchEmailOpens();
    
    console.log('✅ Phishing Detector content script loaded');
}