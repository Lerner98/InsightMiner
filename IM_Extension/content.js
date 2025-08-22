// content.js - Injects "Mine" buttons into pages (HTTP Communication Version)

class InsightMinerInjector {
    constructor() {
        this.processedElements = new WeakSet();
        this.init();
    }

    init() {
        const observer = new MutationObserver(() => this.injectButtons());
        observer.observe(document.body, { childList: true, subtree: true });
        setTimeout(() => this.injectButtons(), 2000);
        console.log("InsightMiner: Content script active.");
    }

    injectButtons() {
        document.querySelectorAll('article').forEach(article => {
            if (this.processedElements.has(article)) return;
            if (this.isInstagramPost(article)) {
                this.createButton(article);
                this.processedElements.add(article);
            }
        });
    }

    isInstagramPost(article) {
        const video = article.querySelector('video');
        const img = article.querySelector('div[role="img"] img');
        return !!(video || img);
    }

    createButton(article) {
        const btn = document.createElement('button');
        btn.className = 'insightminer-btn';
        btn.innerHTML = '⛏️ Mine';

        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            btn.textContent = 'Mining...';
            btn.disabled = true;

            // Send only the Instagram post URL to background script
            chrome.runtime.sendMessage({ 
                action: 'downloadContent', 
                data: { postUrl: window.location.href }
            }, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('InsightMiner Error: Extension communication failed:', chrome.runtime.lastError.message);
                    this.setButtonState(btn, 'error', '❌ Failed');
                } else if (!response) {
                    console.error('InsightMiner Error: No response from background script');
                    this.setButtonState(btn, 'error', '❌ Failed');
                } else if (!response.success) {
                    console.error('InsightMiner Error:', response.error);
                    if (response.error.includes('Python app not running')) {
                        this.setButtonState(btn, 'error', '❌ App Offline');
                    } else {
                        this.setButtonState(btn, 'error', '❌ Failed');
                    }
                } else {
                    console.log('InsightMiner Success:', response.message);
                    this.setButtonState(btn, 'success', '✅ Mined');
                    if (response.folder) {
                        console.log('Saved to:', response.folder);
                    }
                }
            });
        });

        const target = article.querySelector('section span button');
        if (target) {
            const container = target.parentElement.parentElement;
            if (container) {
                 container.style.display = 'flex';
                 container.prepend(btn);
            }
        }
    }

    setButtonState(btn, state, text) {
        btn.textContent = text;
        btn.classList.remove('success', 'error');
        if (state !== 'default') {
            btn.classList.add(state);
        }
        
        // Reset button after 3 seconds for failed states
        if (state === 'error') {
            setTimeout(() => {
                btn.textContent = '⛏️ Mine';
                btn.classList.remove('error');
                btn.disabled = false;
            }, 3000);
        }
    }
}

window.addEventListener('load', () => { new InsightMinerInjector(); });