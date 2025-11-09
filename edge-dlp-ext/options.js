// options.js - Extension Options Page
// Manages extension settings stored in chrome.storage

console.log('[EdgeDLP] Options page loaded');

// Default settings
const DEFAULT_SETTINGS = {
    enableObfuscation: true,
    useConsensus: false,
    consensusMode: 'any_two',
    confidenceThreshold: 50,
    riskyDomains: [
        'chat.openai.com',
        'chatgpt.com',
        'claude.ai',
        'gemini.google.com',
        'copilot.microsoft.com',
        'bard.google.com',
        'pastebin.com',
        'paste.ee',
        'dpaste.com',
        'hastebin.com',
        'github.com',
        'gist.github.com',
        'stackoverflow.com',
        'discord.com',
        'slack.com',
        'reddit.com',
        'twitter.com',
        'x.com',
        'facebook.com',
        'linkedin.com',
        'medium.com',
        'notion.so'
    ],
    fileTypes: {
        code: true,
        pdf: true,
        docx: true,
        text: true
    },
    notifications: {
        enabled: true,
        timeout: 5
    }
};

// Load settings from chrome.storage
async function loadSettings() {
    try {
        const result = await chrome.storage.sync.get(['edgeDLPSettings']);
        const settings = result.edgeDLPSettings || DEFAULT_SETTINGS;
        
        // Apply settings to UI
        document.getElementById('enableObfuscation').checked = settings.enableObfuscation !== false;
        document.getElementById('useConsensus').checked = settings.useConsensus === true;
        document.getElementById('consensusMode').value = settings.consensusMode || 'any_two';
        document.getElementById('confidenceThreshold').value = settings.confidenceThreshold || 50;
        document.getElementById('confidenceValue').textContent = (settings.confidenceThreshold || 50) + '%';
        
        // Update consensus mode visibility
        updateConsensusModeVisibility();
        
        // File types
        document.getElementById('protectCode').checked = settings.fileTypes?.code !== false;
        document.getElementById('protectPDF').checked = settings.fileTypes?.pdf !== false;
        document.getElementById('protectDOCX').checked = settings.fileTypes?.docx !== false;
        document.getElementById('protectText').checked = settings.fileTypes?.text !== false;
        
        // Notifications
        document.getElementById('enableNotifications').checked = settings.notifications?.enabled !== false;
        document.getElementById('notificationTimeout').value = settings.notifications?.timeout || 5;
        document.getElementById('timeoutValue').textContent = (settings.notifications?.timeout || 5) + 's';
        
        // Load domains
        loadDomains(settings.riskyDomains || DEFAULT_SETTINGS.riskyDomains);
        
        console.log('[EdgeDLP] Settings loaded:', settings);
    } catch (error) {
        console.error('[EdgeDLP] Error loading settings:', error);
        showStatus('Error loading settings', 'error');
    }
}

// Save settings to chrome.storage
async function saveSettings() {
    try {
        const settings = {
            enableObfuscation: document.getElementById('enableObfuscation').checked,
            useConsensus: document.getElementById('useConsensus').checked,
            consensusMode: document.getElementById('consensusMode').value,
            confidenceThreshold: parseInt(document.getElementById('confidenceThreshold').value),
            riskyDomains: getDomains(),
            fileTypes: {
                code: document.getElementById('protectCode').checked,
                pdf: document.getElementById('protectPDF').checked,
                docx: document.getElementById('protectDOCX').checked,
                text: document.getElementById('protectText').checked
            },
            notifications: {
                enabled: document.getElementById('enableNotifications').checked,
                timeout: parseInt(document.getElementById('notificationTimeout').value)
            }
        };
        
        await chrome.storage.sync.set({ edgeDLPSettings: settings });
        
        // Also update risky_domains.json for content scripts
        await updateRiskyDomainsFile(settings.riskyDomains);
        
        // Notify content scripts of settings change
        chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, {
                    type: 'settings-updated',
                    settings: settings
                }).catch(() => {
                    // Ignore errors for tabs that don't have content script
                });
            });
        });
        
        showStatus('Settings saved successfully!', 'success');
        console.log('[EdgeDLP] Settings saved:', settings);
    } catch (error) {
        console.error('[EdgeDLP] Error saving settings:', error);
        showStatus('Error saving settings', 'error');
    }
}

// Update risky_domains.json file
async function updateRiskyDomainsFile(domains) {
    try {
        // Read current risky_domains.json
        const response = await fetch(chrome.runtime.getURL('risky_domains.json'));
        const currentData = await response.json();
        
        // Update with new domains
        const updatedData = {
            ...currentData,
            high_risk_domains: domains
        };
        
        // Note: We can't directly write to extension files from options page
        // Instead, we'll store in chrome.storage and content scripts will read from there
        // The risky_domains.json will be updated when extension is reloaded
        console.log('[EdgeDLP] Domains updated (will take effect after extension reload):', domains);
    } catch (error) {
        console.error('[EdgeDLP] Error updating risky domains file:', error);
    }
}

// Load domains into UI
function loadDomains(domains) {
    const domainList = document.getElementById('domainList');
    domainList.innerHTML = '';
    
    domains.forEach((domain, index) => {
        addDomainInput(domain, index);
    });
}

// Add domain input field
function addDomainInput(domain = '', index = null) {
    const domainList = document.getElementById('domainList');
    const domainItem = document.createElement('div');
    domainItem.className = 'domain-item';
    
    const input = document.createElement('input');
    input.type = 'text';
    input.value = domain;
    input.placeholder = 'example.com';
    
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn-remove';
    removeBtn.textContent = 'Remove';
    removeBtn.onclick = () => {
        domainItem.remove();
    };
    
    domainItem.appendChild(input);
    domainItem.appendChild(removeBtn);
    domainList.appendChild(domainItem);
}

// Get domains from UI
function getDomains() {
    const domainItems = document.querySelectorAll('.domain-item input');
    const domains = [];
    domainItems.forEach(input => {
        const domain = input.value.trim();
        if (domain) {
            domains.push(domain);
        }
    });
    return domains;
}

// Update consensus mode visibility
function updateConsensusModeVisibility() {
    const useConsensus = document.getElementById('useConsensus').checked;
    const consensusModeGroup = document.getElementById('consensusModeGroup');
    consensusModeGroup.style.display = useConsensus ? 'block' : 'none';
}

// Show status message
function showStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    statusEl.style.display = 'block';
    
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 3000);
}

// Reset to defaults
function resetToDefaults() {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
        chrome.storage.sync.set({ edgeDLPSettings: DEFAULT_SETTINGS }, () => {
            loadSettings();
            showStatus('Settings reset to defaults', 'success');
        });
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    console.log('[EdgeDLP] DOM loaded, initializing options page');
    
    // Load settings
    loadSettings();
    
    // Save button
    document.getElementById('saveBtn').addEventListener('click', saveSettings);
    
    // Reset button
    document.getElementById('resetBtn').addEventListener('click', resetToDefaults);
    
    // Add domain button
    document.getElementById('addDomain').addEventListener('click', () => {
        addDomainInput();
    });
    
    // Consensus mode toggle
    document.getElementById('useConsensus').addEventListener('change', updateConsensusModeVisibility);
    
    // Confidence threshold slider
    document.getElementById('confidenceThreshold').addEventListener('input', (e) => {
        document.getElementById('confidenceValue').textContent = e.target.value + '%';
    });
    
    // Notification timeout slider
    document.getElementById('notificationTimeout').addEventListener('input', (e) => {
        document.getElementById('timeoutValue').textContent = e.target.value + 's';
    });
    
    console.log('[EdgeDLP] Options page initialized');
});

