// background.js - InsightMiner Service Worker (HTTP Communication Version)

// --- Initialization ---
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({ stats: { mined: 0, failed: 0 } });
});

// --- Message Listener ---
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'downloadContent') {
        handleDownload(request.data, sendResponse);
        return true;
    }
    // Handle popup requests
    handlePopupRequests(request, sendResponse);
    return true;
});

async function handlePopupRequests(request, sendResponse) {
    switch (request.action) {
        case 'getData':
            const statsData = await chrome.storage.local.get({ stats: { mined: 0, failed: 0 } });
            const connectionStatus = await checkPythonAppConnection();
            sendResponse({ stats: statsData.stats, connectionStatus: connectionStatus });
            break;
        case 'resetStats':
            await chrome.storage.local.set({ stats: { mined: 0, failed: 0 } });
            const newStats = await chrome.storage.local.get({ stats: { mined: 0, failed: 0 } });
            sendResponse({ success: true, stats: newStats.stats });
            break;
        case 'checkConnection':
            const status = await checkPythonAppConnection();
            sendResponse({ connectionStatus: status });
            break;
    }
}

// --- Core HTTP Communication Logic ---
async function handleDownload(data, sendResponse) {
    // Add comprehensive logging for debugging
    console.log('🔍 InsightMiner: handleDownload called with data:', data);
    
    // Validate input data
    if (!data || !data.postUrl) {
        console.error('❌ InsightMiner: Invalid data received - missing postUrl:', data);
        await updateStats('failed');
        sendResponse({ 
            success: false, 
            error: 'Invalid request data - missing Instagram URL' 
        });
        return;
    }

    // Prepare request payload
    const requestPayload = {
        url: data.postUrl,
        type: 'auto'
    };
    
    console.log('📤 InsightMiner: Sending HTTP request to localhost:8502/download');
    console.log('📤 Request payload:', requestPayload);

    try {
        const response = await fetch('http://localhost:8502/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload)
        });

        console.log('📥 InsightMiner: Response received');
        console.log('📥 Response status:', response.status, response.statusText);
        console.log('📥 Response headers:', Object.fromEntries(response.headers.entries()));

        if (!response.ok) {
            console.error('❌ InsightMiner: HTTP error response');
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('📥 InsightMiner: Response body parsed:', result);
        
        if (result.success) {
            console.log('✅ InsightMiner: Download successful');
            await updateStats('mined');
            sendResponse({ success: true, message: result.message, folder: result.folder });
        } else {
            console.error('❌ InsightMiner: Download failed according to response:', result.message);
            await updateStats('failed');
            sendResponse({ success: false, error: result.message || 'Download failed' });
        }
    } catch (error) {
        console.error('❌ InsightMiner: Exception during HTTP request:', error);
        console.error('❌ Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack
        });
        
        await updateStats('failed');
        
        if (error.name === 'TypeError' || error.message.includes('fetch')) {
            console.error('❌ InsightMiner: Network/connection error detected');
            sendResponse({ 
                success: false, 
                error: 'Python app not running. Please start InsightMiner application.' 
            });
        } else {
            sendResponse({ 
                success: false, 
                error: `Connection error: ${error.message}` 
            });
        }
    }
}

async function checkPythonAppConnection() {
    try {
        const response = await fetch('http://localhost:8502/health', {
            method: 'GET',
            signal: AbortSignal.timeout(3000) // 3 second timeout
        });
        
        if (response.ok) {
            return { connected: true, message: 'Python app is running' };
        } else {
            return { connected: false, message: `HTTP ${response.status}` };
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            return { connected: false, message: 'Connection timeout' };
        }
        return { connected: false, message: 'Python app not running' };
    }
}

async function updateStats(type) {
    const data = await chrome.storage.local.get({ stats: { mined: 0, failed: 0 } });
    const stats = data.stats;
    if (type === 'mined') stats.mined++;
    if (type === 'failed') stats.failed++;
    await chrome.storage.local.set({ stats });
}