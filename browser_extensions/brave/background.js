// Background script for browser extension
let activeGmailTabs = {};
let scannedEmails = {};
let connectionStatus = 'disconnected';
let desktopAppUrl = 'http://localhost:9877';
let reconnectAttempts = 0;
let connectionCheckInterval = null;
let initialized = false;

// Initialize only once
if (!initialized) {
    initialized = true;
    
    console.log('🔌 Phishing Detector Extension loaded');

    // Initialize - try to connect to desktop app
    function initConnection() {
        console.log('🔌 Attempting to connect to desktop app...');
        checkConnection();
        
        // Send connection status every 30 seconds
        connectionCheckInterval = setInterval(checkConnection, 30000);
    }

    // Check connection to desktop app
    function checkConnection() {
        fetch(`${desktopAppUrl}/api/health`, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache'
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Connection failed');
        })
        .then(data => {
            if (data.status === 'running') {
                connectionStatus = 'connected';
                reconnectAttempts = 0;
                console.log('✅ Connected to desktop app');
                sendConnectionStatus('connected');
            }
        })
        .catch(error => {
            connectionStatus = 'disconnected';
            reconnectAttempts++;
            console.log(`❌ Disconnected from desktop app (attempt ${reconnectAttempts})`);
            sendConnectionStatus('disconnected');
            
            // Try to reconnect every 10 seconds
            setTimeout(checkConnection, 10000);
        });
    }

    // Send connection status to desktop app
    function sendConnectionStatus(status) {
        fetch(`${desktopAppUrl}/api/notification`, {
            method: 'POST',
            mode: 'cors',
            cache: 'no-cache',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'connection_status',
                status: status,
                timestamp: Date.now(),
                extension_version: '1.0.0',
                browser: navigator.userAgent
            })
        }).catch(() => {});
    }

    // Force reconnection
    function forceReconnect() {
        console.log('🔄 Force reconnecting...');
        connectionStatus = 'connecting';
        checkConnection();
    }

    // Listen for tab updates
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
        if (changeInfo.status === 'complete' && tab.url && tab.url.includes('mail.google.com')) {
            console.log('📧 Gmail tab detected:', tabId);
            activeGmailTabs[tabId] = {
                url: tab.url,
                lastScan: null
            };
            
            // Inject content script
            chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content.js']
            }).catch(err => console.log('Script injection error:', err));
            
            // Notify desktop app
            notifyDesktopApp({
                type: 'gmail_opened',
                tabId: tabId,
                url: tab.url
            });
        }
    });

    // Listen for messages from content script
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === 'email_opened') {
            console.log('📨 Email opened:', message.emailId);
            
            notifyDesktopApp({
                type: 'scan_email',
                emailId: message.emailId,
                emailContent: message.emailContent,
                sender: message.sender,
                subject: message.subject,
                links: message.links,
                tabId: sender.tab.id
            });
            
            scannedEmails[message.emailId] = {
                scanned: true,
                timestamp: Date.now()
            };
            
            sendResponse({ received: true });
        }
        
        if (message.type === 'get_connection_status') {
            sendResponse({ 
                status: connectionStatus,
                timestamp: Date.now()
            });
        }
        
        if (message.type === 'force_reconnect') {
            forceReconnect();
            sendResponse({ status: 'reconnecting' });
        }
        
        return true;
    });

    // Listen for tab removal
    chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
        if (activeGmailTabs[tabId]) {
            delete activeGmailTabs[tabId];
            notifyDesktopApp({
                type: 'gmail_closed',
                tabId: tabId
            });
        }
    });

    // Notify desktop app via HTTP. For scan_email requests, relays the
    // prediction result back to the originating tab once it arrives --
    // the desktop app responds synchronously with the scored result.
    function notifyDesktopApp(data) {
        console.log('📤 Sending to desktop app:', data.type);
        fetch(`${desktopAppUrl}/api/notification`, {
            method: 'POST',
            mode: 'cors',
            cache: 'no-cache',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                console.log('❌ Send failed:', response.status);
                return null;
            }
            console.log('✅ Sent successfully');
            return response.json();
        })
        .then(responseData => {
            if (responseData && responseData.result && data.type === 'scan_email' && data.tabId != null) {
                chrome.tabs.sendMessage(data.tabId, {
                    type: 'scan_result',
                    result: responseData.result
                }).catch(err => console.log('Could not relay scan result to tab:', err));
            }
        })
        .catch(error => {
            console.log('❌ Connection error:', error.message);
            if (connectionStatus === 'connected') {
                connectionStatus = 'disconnected';
                checkConnection();
            }
        });
    }

    // Listen for extension installation/update
    chrome.runtime.onInstalled.addListener((details) => {
        console.log('🔌 Extension installed/updated:', details.reason);
        initConnection();
    });

    // Start initialization
    initConnection();
}