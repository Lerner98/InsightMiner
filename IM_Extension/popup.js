// popup.js - Logic for the extension's popup (HTTP Communication Version)

document.addEventListener('DOMContentLoaded', () => {
    const connectionStatusEl = document.getElementById('connectionStatus');
    const checkConnectionBtn = document.getElementById('checkConnection');
    const statusEl = document.getElementById('status');
    const minedEl = document.getElementById('minedCount');
    const failedEl = document.getElementById('failedCount');
    const resetStatsBtn = document.getElementById('resetStats');

    async function loadData() {
        try {
            const data = await chrome.runtime.sendMessage({ action: 'getData' });
            if (data && data.stats) {
                minedEl.textContent = data.stats.mined;
                failedEl.textContent = data.stats.failed;
            }
            if (data && data.connectionStatus) {
                updateConnectionStatus(data.connectionStatus);
            }
        } catch (error) {
            console.error("Error loading data:", error);
            statusEl.textContent = "Error loading data.";
            statusEl.style.color = "#dc3545";
        }
    }

    async function checkConnection() {
        checkConnectionBtn.disabled = true;
        checkConnectionBtn.textContent = 'Checking...';
        connectionStatusEl.textContent = 'Checking...';
        connectionStatusEl.className = 'status-indicator checking';

        try {
            const data = await chrome.runtime.sendMessage({ action: 'checkConnection' });
            if (data && data.connectionStatus) {
                updateConnectionStatus(data.connectionStatus);
            }
        } catch (error) {
            console.error("Error checking connection:", error);
            updateConnectionStatus({ connected: false, message: 'Error checking connection' });
        } finally {
            checkConnectionBtn.disabled = false;
            checkConnectionBtn.textContent = 'Check Connection';
        }
    }

    function updateConnectionStatus(status) {
        if (status.connected) {
            connectionStatusEl.textContent = '✅ Connected';
            connectionStatusEl.className = 'status-indicator connected';
        } else {
            connectionStatusEl.textContent = `❌ ${status.message}`;
            connectionStatusEl.className = 'status-indicator disconnected';
        }
    }
    
    async function resetStats() {
        try {
            const response = await chrome.runtime.sendMessage({ action: 'resetStats' });
            if (response && response.stats) {
                minedEl.textContent = response.stats.mined;
                failedEl.textContent = response.stats.failed;
                statusEl.textContent = 'Stats reset successfully!';
                statusEl.style.color = "#2c974b";
                setTimeout(() => statusEl.textContent = '', 2000);
            }
        } catch (error) {
            console.error("Error resetting stats:", error);
            statusEl.textContent = 'Failed to reset stats.';
            statusEl.style.color = "#dc3545";
            setTimeout(() => statusEl.textContent = '', 2000);
        }
    }

    checkConnectionBtn.addEventListener('click', checkConnection);
    resetStatsBtn.addEventListener('click', resetStats);

    loadData();
});