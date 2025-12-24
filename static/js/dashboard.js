// State Management
const AppState = {
    searchHistory: JSON.parse(localStorage.getItem('searchHistory') || '[]'),
    userSearchHistory: JSON.parse(localStorage.getItem('userSearchHistory') || '[]'),
    heroCollapsed: localStorage.getItem('heroCollapsed') === 'true'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
});

function initializeDashboard() {
    if (AppState.heroCollapsed) {
        document.getElementById('heroSection').classList.add('collapsed');
        document.getElementById('heroToggle').innerHTML = '<span id="heroToggleIcon">▼</span> Expand';
    }
    fetchDashboardStats();
}

async function fetchDashboardStats() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        if (res.ok) {
            document.getElementById('statTotalDevices').textContent = data.total_devices.toLocaleString();
            document.getElementById('statActiveDevices').textContent = data.active.toLocaleString();
            document.getElementById('statDisabledDevices').textContent = data.disabled.toLocaleString();
            document.getElementById('statDeprovisionedDevices').textContent = data.deprovisioned.toLocaleString();
        } else {
            document.getElementById('statTotalDevices').textContent = 'Error';
            document.getElementById('statActiveDevices').textContent = '—';
            document.getElementById('statDisabledDevices').textContent = '—';
            document.getElementById('statDeprovisionedDevices').textContent = '—';
        }
    } catch (e) {
        console.error('Failed to fetch dashboard stats:', e);
        document.getElementById('statTotalDevices').textContent = 'Error';
    }
}

function toggleHero() {
    const hero = document.getElementById('heroSection');
    const toggle = document.getElementById('heroToggle');
    const isCollapsed = hero.classList.toggle('collapsed');
    AppState.heroCollapsed = isCollapsed;
    localStorage.setItem('heroCollapsed', isCollapsed);
    if (isCollapsed) {
        toggle.innerHTML = '<span id="heroToggleIcon">▼</span> Expand';
    } else {
        toggle.innerHTML = '<span id="heroToggleIcon">▲</span> Collapse';
    }
}

function quickAction(action) {
    switch(action) {
        case 'device':
            switchTab('search');
            document.getElementById('searchInput').focus();
            break;
        case 'user':
            switchTab('users');
            document.getElementById('userSearchInput').focus();
            break;
        case 'reports':
            switchTab('reports');
            break;
        case 'recent':
            showRecentSearches();
            break;
    }
}

function showRecentSearches() {
    const panel = document.getElementById('recentSearchesPanel');
    const list = document.getElementById('recentSearchesList');
    const allSearches = [
        ...AppState.searchHistory.map(s => ({...s, type: 'device'})),
        ...AppState.userSearchHistory.map(s => ({...s, type: 'user'}))
    ].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, 10);
    if (allSearches.length === 0) {
        list.innerHTML = '<div style="color: rgba(255,255,255,0.6); text-align:center; padding:20px;">No recent searches</div>';
    } else {
        list.innerHTML = allSearches.map(s => `
            <div class="recent-item" onclick="executeRecentSearch('${s.query}', '${s.type}')">
                <span class="recent-item-text">${s.query}</span>
                <span class="recent-item-type">${s.type === 'device' ? '💻' : '👤'}</span>
            </div>
        `).join('');
    }
    panel.style.display = 'block';
}

function closeRecentSearches() {
    document.getElementById('recentSearchesPanel').style.display = 'none';
}

function executeRecentSearch(query, type) {
    closeRecentSearches();
    if (type === 'device') {
        switchTab('search');
        document.getElementById('searchInput').value = query;
        searchDevices();
    } else {
        switchTab('users');
        document.getElementById('userSearchInput').value = query;
        searchUsers();
    }
}

function addToSearchHistory(query, type) {
    const history = type === 'device' ? AppState.searchHistory : AppState.userSearchHistory;
    const storageKey = type === 'device' ? 'searchHistory' : 'userSearchHistory';
    const filtered = history.filter(s => s.query !== query);
    filtered.unshift({
        query: query,
        timestamp: new Date().toISOString()
    });
    const trimmed = filtered.slice(0, 20);
    if (type === 'device') {
        AppState.searchHistory = trimmed;
    } else {
        AppState.userSearchHistory = trimmed;
    }
    localStorage.setItem(storageKey, JSON.stringify(trimmed));
}

async function refreshStats() {
    const refreshIcon = document.getElementById('refreshIcon');
    refreshIcon.classList.add('loading-spinner');
    refreshIcon.style.fontSize = '1em';
    try {
        await fetchDashboardStats();
        showToast('Device statistics refreshed', 'success');
        refreshIcon.classList.remove('loading-spinner');
        refreshIcon.textContent = '✅';
        setTimeout(() => {
            refreshIcon.textContent = '🔄';
            refreshIcon.style.fontSize = '';
        }, 2000);
    } catch (e) {
        showToast('Failed to refresh statistics', 'error');
        refreshIcon.classList.remove('loading-spinner');
        refreshIcon.textContent = '❌';
        setTimeout(() => {
            refreshIcon.textContent = '🔄';
            refreshIcon.style.fontSize = '';
        }, 2000);
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function switchTab(t){
    document.querySelectorAll('.tab').forEach(b => {
        b.classList.remove('active');
        if (b.getAttribute('data-tab') === t) {
            b.classList.add('active');
        }
    });
    document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
    document.getElementById(t+'Tab').classList.add('active');
}

async function searchDevices(){
    const q=document.getElementById('searchInput').value.trim();
    if(!q){alert('Enter search term');return}
    addToSearchHistory(q, 'device');
    const r=document.getElementById('resultsContainer');
    r.innerHTML='<div style="text-align:center;padding:40px"><div class="loading-spinner"></div><div style="margin-top:15px;color:var(--text-secondary)">Searching devices...</div></div>';
    try{
        const res=await fetch(`/api/combined/search?query=${encodeURIComponent(q)}`);
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'Search failed');
        displayResults(data.devices);
        document.getElementById('searchInfo').innerHTML=`Found ${data.count} device(s)`;
        showToast(`Found ${data.count} device(s)`, 'success');
    }catch(e){
        r.innerHTML=`<div style="background:#ffebee;color:#c62828;padding:15px;border-radius:8px">Error: ${e.message}</div>`;
        showToast(`Search failed: ${e.message}`, 'error');
    }
}

// ============================================================
// ENHANCED DISPLAY RESULTS - PREVIEW VERSION
// ============================================================

function displayResults(devices) {
    const c = document.getElementById('resultsContainer');

    if (!devices || devices.length === 0) {
        c.innerHTML = '<div class="no-results">No devices found</div>';
        return;
    }

    let html = '';

    devices.forEach(device => {
        // Determine device characteristics
        const status = device.googleStatus || 'N/A';
        const badgeClass = status === 'ACTIVE' ? 'badge-active' : 'badge-disabled';
        const deviceType = device.deviceType || 'Unknown';
        const isChromebook = deviceType === 'Chromebooks';
        const typeClass = isChromebook ? 'type-chromebook' : 'type-ipad';
        const statusClass = status === 'ACTIVE' ? 'status-active' : 'status-disabled';
        const typeIcon = isChromebook ? '💻' : '📱';

        // URLs
        const iiqLink = `https://crsd.incidentiq.com/agent/assets/${device.assetId || ''}?asset-details-tab=details`;
        const googleLink = `https://admin.google.com/ac/chrome/devices/${device.deviceId || device.serialNumber}?journey=217`;

        // User information
        const userEmail = device.iiqOwnerEmail || device.assignedUser || 'Not assigned';
        const hasIiqUser = !!device.iiqOwnerEmail;
        const hasGoogleUser = device.assignedUser && device.assignedUser !== 'Not assigned';
        const userSource = hasIiqUser
            ? '<span class="field-badge badge-iiq">IIQ Official</span>'
            : (hasGoogleUser ? '<span class="field-badge badge-google">Google</span>' : '');
        const userName = device.iiqOwnerName && device.iiqOwnerEmail
            ? `<div class="field-value-secondary">${escapeHtml(device.iiqOwnerName)}</div>`
            : '';

        // Build card
        html += `
            <div class="device-card ${typeClass} ${statusClass}">
                ${generateCardHeader(device, isChromebook, typeIcon, badgeClass, status, iiqLink)}
                ${generateCardContent(device, isChromebook, googleLink, userEmail, userSource, userName)}
            </div>
        `;
    });

    c.innerHTML = html;
}

function generateCardHeader(device, isChromebook, typeIcon, badgeClass, status, iiqLink) {
    return `
        <div class="device-header">
            <div class="device-primary-info">
                <div class="device-asset-tag">
                    <a href="${iiqLink}" target="_blank" title="View in IncidentIQ">
                        <span class="asset-icon">🏷️</span>
                        <span>${escapeHtml(device.assetTag)}</span>
                    </a>
                </div>
                <div class="device-subtitle">Serial: ${escapeHtml(device.serialNumber)}</div>
            </div>
            <div class="device-status-badges">
                <span class="device-badge ${badgeClass}">
                    <span class="status-indicator"></span>
                    <span>${status}</span>
                </span>
                ${device.iiqStatus ? `<span class="device-badge badge-iiq-status">IIQ: ${escapeHtml(device.iiqStatus)}</span>` : ''}
            </div>
        </div>
    `;
}

function generateCardContent(device, isChromebook, googleLink, userEmail, userSource, userName) {
    return `
        <div class="device-content">
            <div class="device-grid">
                ${generatePriorityFields(device, isChromebook, googleLink, userEmail, userSource, userName)}
                ${isChromebook ? generateChromebookFields(device) : ''}
                ${generateMerakiFields(device)}
            </div>
            ${generateRecentUsers(device)}
            ${generateQuickActionsPanel(device)}
        </div>
    `;
}

function generatePriorityFields(device, isChromebook, googleLink, userEmail, userSource, userName) {
    return `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🔢</span>
                <span>Serial Number</span>
            </div>
            <div class="field-value">
                ${isChromebook
                    ? `<a href="${googleLink}" target="_blank" title="View in Google Admin Console">${escapeHtml(device.serialNumber)}</a>`
                    : escapeHtml(device.serialNumber)}
            </div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">👤</span>
                <span>Assigned User</span>
                ${userSource}
            </div>
            <div class="field-value">
                ${escapeHtml(userEmail)}
                ${userName}
            </div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">💻</span>
                <span>Model</span>
            </div>
            <div class="field-value">${escapeHtml(device.model || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">📍</span>
                <span>Location</span>
            </div>
            <div class="field-value">${escapeHtml(device.location || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🌐</span>
                <span>MAC Address</span>
            </div>
            <div class="field-value">${escapeHtml(device.macAddress || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🌍</span>
                <span>LAN IP</span>
            </div>
            <div class="field-value">${escapeHtml(device.ipAddress || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🌐</span>
                <span>WAN IP</span>
            </div>
            <div class="field-value">${escapeHtml(device.wanIpAddress || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">💿</span>
                <span>OS Version</span>
            </div>
            <div class="field-value">${escapeHtml(device.osVersion || 'N/A')}</div>
        </div>
    `;
}

function generateChromebookFields(device) {
    return `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🔄</span>
                <span>Last Sync</span>
            </div>
            <div class="field-value">${fmt(device.lastSync)}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">👤</span>
                <span>Last Known User</span>
            </div>
            <div class="field-value">${escapeHtml(device.lastKnownUser || 'N/A')}</div>
        </div>

        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">📁</span>
                <span>Org Unit Path</span>
            </div>
            <div class="field-value">${escapeHtml(device.orgUnitPath || 'N/A')}</div>
        </div>
    `;
}

function generateMerakiFields(device) {
    let merakiHtml = '';

    if (device.merakiApName) {
        merakiHtml += `
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">📡</span>
                    <span>Last Known AP</span>
                </div>
                <div class="field-value">
                    ${escapeHtml(device.merakiApName)}
                    ${device.merakiNetwork ? `<div class="field-value-secondary">${escapeHtml(device.merakiNetwork)}</div>` : ''}
                </div>
            </div>
        `;
    }

    if (device.merakiLastSeen) {
        const noteColor = device.merakiNewer ? 'var(--success-color)' : 'var(--warning-color)';
        merakiHtml += `
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🕐</span>
                    <span>Meraki Last Seen</span>
                </div>
                <div class="field-value">
                    ${fmt(device.merakiLastSeen)}
                    ${device.merakiNote ? `<div class="field-value-secondary" style="color: ${noteColor}">${escapeHtml(device.merakiNote)}</div>` : ''}
                </div>
            </div>
        `;
    }

    return merakiHtml;
}

function generateRecentUsers(device) {
    if (!device.recentUsers || device.recentUsers.length === 0) {
        return '';
    }

    return `
        <div class="recent-users-section">
            <div class="section-header">
                <span>📋</span>
                <span>Recent Users</span>
            </div>
            <div>
                ${device.recentUsers.map(user =>
                    `<span class="user-chip">👤 ${escapeHtml(user)}</span>`
                ).join('')}
            </div>
        </div>
    `;
}

function clearSearch(){document.getElementById('searchInput').value='';document.getElementById('searchInfo').innerHTML='';document.getElementById('resultsContainer').innerHTML='<div class="no-results">Enter search term</div>'}
function fmt(d){if(!d||d==='N/A')return'N/A';try{return new Date(d).toLocaleString()}catch{return d}}

async function searchUsers(){
    const q=document.getElementById('userSearchInput').value.trim();
    if(!q){alert('Enter search term');return}
    addToSearchHistory(q, 'user');
    const r=document.getElementById('userResultsContainer');
    r.innerHTML='<div style="text-align:center;padding:40px"><div class="loading-spinner"></div><div style="margin-top:15px;color:var(--text-secondary)">Searching users...</div></div>';
    try{
        const res=await fetch(`/api/user/search?query=${encodeURIComponent(q)}`);
        const data=await res.json();
        if(!res.ok)throw new Error(data.detail||'Search failed');
        displayUserResults(data.users);
        document.getElementById('userSearchInfo').innerHTML=`Found ${data.count} user(s)`;
        showToast(`Found ${data.count} user(s)`, 'success');
    }catch(e){
        r.innerHTML=`<div style="background:#ffebee;color:#c62828;padding:15px;border-radius:8px">Error: ${e.message}</div>`;
        showToast(`User search failed: ${e.message}`, 'error');
    }
}

function displayUserResults(users) {
    const container = document.getElementById('userResultsContainer');
    if (!users || users.length === 0) {
        container.innerHTML = '<div class="no-results">No users found</div>';
        return;
    }

    let html = '';
    users.forEach((u, userIndex) => {
        const status = u.isActive ? 'ACTIVE' : 'INACTIVE';
        const badgeClass = u.isActive ? 'badge-active' : 'badge-disabled';
        const userId = u.userId || '';

        // Generate IIQ and Google links
        const googleAdminLink = userId ? `https://admin.google.com/ac/users/${userId}` : '#';
        // IIQ doesn't have a direct user URL, so we'll search for the user
        const iiqSearchLink = `https://crsd.incidentiq.com/agent/search?query=${encodeURIComponent(u.email)}`;

        html += `
            <div class="device-card user-card">
                <!-- User Header -->
                <div class="device-header">
                    <div class="device-primary-info">
                        <div class="device-asset-tag">
                            <span class="asset-icon">👤</span>
                            <span>${escapeHtml(u.fullName)}${u.isStudent && u.studentId ? ` <span style="color: rgba(255,255,255,0.6); font-weight: 400;">(ID: ${escapeHtml(u.studentId)})</span>` : ''}</span>
                        </div>
                        <div class="device-subtitle">${escapeHtml(u.email)}</div>
                    </div>
                    <div class="device-status-badges">
                        <span class="device-badge ${badgeClass}">
                            <span class="status-indicator"></span>
                            <span>${status}</span>
                        </span>
                        <span class="device-badge badge-iiq" style="background: linear-gradient(135deg, #00A3FF 0%, #0077cc 100%); border: none;">
                            <span>📊 IIQ</span>
                        </span>
                    </div>
                </div>

                <!-- User Info Grid -->
                <div class="device-content">
                    <div class="device-grid">
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">📁</span>
                                <span>Org Unit</span>
                            </div>
                            <div class="field-value">${escapeHtml(u.googleOrgUnit || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">💻</span>
                                <span>Total Devices</span>
                            </div>
                            <div class="field-value">${u.totalDeviceCount || 0}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">📦</span>
                                <span>IIQ Assigned</span>
                            </div>
                            <div class="field-value">${u.iiqAssignedCount || 0}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">🔐</span>
                                <span>Recent Logins</span>
                            </div>
                            <div class="field-value">${u.googleRecentCount || 0}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">🏫</span>
                                <span>Location</span>
                            </div>
                            <div class="field-value">${escapeHtml(u.location || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">🎓</span>
                                <span>Grade</span>
                            </div>
                            <div class="field-value">${escapeHtml(u.grade || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label">
                                <span class="field-icon">🆔</span>
                                <span>Username</span>
                            </div>
                            <div class="field-value">${escapeHtml(u.username || 'N/A')}</div>
                        </div>
                    </div>

                    <!-- User Quick Actions -->
                    <div class="quick-actions-panel">
                        <div class="quick-actions-header">⚡ Quick Actions</div>
                        <div class="quick-actions-buttons">
                            <button class="quick-action-btn" onclick="window.open('${googleAdminLink}', '_blank')" ${!userId ? 'disabled' : ''}>
                                <span class="quick-action-icon">⚙️</span>
                                <span class="quick-action-text">View in Google</span>
                            </button>
                            <button class="quick-action-btn" onclick="window.open('${iiqSearchLink}', '_blank')">
                                <span class="quick-action-icon">📊</span>
                                <span class="quick-action-text">Search in IIQ</span>
                            </button>
                            <button class="quick-action-btn" onclick="copyToClipboard('Email', '${escapeHtml(u.email)}', this)">
                                <span class="quick-action-icon">📋</span>
                                <span class="quick-action-text">Copy Email</span>
                            </button>
                        </div>
                    </div>

                    <!-- IIQ Assigned Devices -->
                    ${generateUserDeviceSection(u.iiqAssignedDevices, 'IIQ Assigned Devices', '📦', 'iiq', userIndex)}

                    <!-- Google Recent Logins -->
                    ${generateUserDeviceSection(u.googleRecentDevices, 'Recent Logins (Last 5, Most Recent First)', '🔐', 'google', userIndex)}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function generateUserDeviceSection(devices, title, icon, type, userIndex) {
    if (!devices || devices.length === 0) {
        return '';
    }

    const sectionId = `user-${userIndex}-${type}-devices`;

    let html = `
        <div class="user-devices-section">
            <div class="user-devices-header">
                <span class="field-icon">${icon}</span>
                <span>${title} (${devices.length})</span>
            </div>
            <div class="user-devices-list">
    `;

    devices.forEach((device, deviceIndex) => {
        const deviceId = `${sectionId}-${deviceIndex}`;
        const googleLink = device.deviceId ? `https://admin.google.com/ac/chrome/devices/${device.deviceId}?journey=217` : '#';
        const iiqLink = device.iiqAssetId ? `https://crsd.incidentiq.com/agent/assets/${device.iiqAssetId}?asset-details-tab=details` : '#';

        html += `
            <div class="user-device-item">
                <div class="user-device-summary" onclick="toggleDeviceDetails('${deviceId}')">
                    <div class="user-device-info">
                        <span class="user-device-asset">${escapeHtml(device.assetTag)}</span>
                        <span class="user-device-serial">SN: ${escapeHtml(device.serialNumber)}</span>
                        <span class="user-device-model">${escapeHtml(device.model)}</span>
                    </div>
                    <div class="user-device-expand">
                        <span id="${deviceId}-icon">▶</span>
                    </div>
                </div>

                <div id="${deviceId}-details" class="user-device-details" style="display: none;">
                    <div class="device-grid" style="margin-top: 12px;">
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📊</span><span>Status</span></div>
                            <div class="field-value">${escapeHtml(device.googleStatus)}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📍</span><span>IIQ Status</span></div>
                            <div class="field-value">${escapeHtml(device.iiqStatus)}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📍</span><span>Location</span></div>
                            <div class="field-value">${escapeHtml(device.location || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🚪</span><span>Room</span></div>
                            <div class="field-value">${escapeHtml(device.room || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌐</span><span>MAC</span></div>
                            <div class="field-value">${escapeHtml(device.macAddress)}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌍</span><span>LAN IP</span></div>
                            <div class="field-value">${escapeHtml(device.ipAddress)}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌐</span><span>WAN IP</span></div>
                            <div class="field-value">${escapeHtml(device.wanIpAddress)}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">💿</span><span>OS Version</span></div>
                            <div class="field-value">${escapeHtml(device.osVersion)}</div>
                        </div>
                        ${device.batteryHealth ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🔋</span><span>Battery</span></div>
                            <div class="field-value">${device.batteryHealth}%</div>
                        </div>
                        ` : ''}
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🕐</span><span>Last Activity</span></div>
                            <div class="field-value">${fmt(device.lastSync)}</div>
                            <div class="field-value-secondary">Most recent device usage</div>
                        </div>
                    </div>

                    <div class="quick-actions-panel" style="margin-top: 12px;">
                        <div class="quick-actions-buttons">
                            <button class="quick-action-btn" onclick="copyToClipboard('Serial', '${escapeHtml(device.serialNumber)}', this)">
                                <span class="quick-action-icon">📋</span>
                                <span class="quick-action-text">Copy Serial</span>
                            </button>
                            <button class="quick-action-btn" onclick="copyToClipboard('Asset Tag', '${escapeHtml(device.assetTag)}', this)">
                                <span class="quick-action-icon">🏷️</span>
                                <span class="quick-action-text">Copy Asset Tag</span>
                            </button>
                            ${device.deviceId ? `
                            <button class="quick-action-btn" onclick="window.open('${googleLink}', '_blank')">
                                <span class="quick-action-icon">⚙️</span>
                                <span class="quick-action-text">Google Admin</span>
                            </button>
                            ` : ''}
                            ${device.iiqAssetId ? `
                            <button class="quick-action-btn" onclick="window.open('${iiqLink}', '_blank')">
                                <span class="quick-action-icon">📊</span>
                                <span class="quick-action-text">IncidentIQ</span>
                            </button>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;

    return html;
}

function toggleDeviceDetails(deviceId) {
    const details = document.getElementById(`${deviceId}-details`);
    const icon = document.getElementById(`${deviceId}-icon`);

    if (details.style.display === 'none') {
        details.style.display = 'block';
        icon.textContent = '▼';
    } else {
        details.style.display = 'none';
        icon.textContent = '▶';
    }
}

function clearUserSearch(){document.getElementById('userSearchInput').value='';document.getElementById('searchInfo').innerHTML='';document.getElementById('userResultsContainer').innerHTML='<div class="no-results">Enter user name or email</div>'}
function searchDeviceFromUser(assetTag){switchTab('search');document.getElementById('searchInput').value=assetTag;searchDevices()}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        quickAction('device');
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
        e.preventDefault();
        quickAction('user');
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'h') {
        e.preventDefault();
        toggleHero();
    }
    if (e.key === 'Escape') {
        const panel = document.getElementById('recentSearchesPanel');
        if (panel.style.display === 'block') {
            closeRecentSearches();
        }
    }
});

// ============================================================
// QUICK ACTIONS PANEL
// ============================================================

/**
 * Copy text to clipboard with visual feedback
 */
async function copyToClipboard(type, value, buttonElement) {
    try {
        // Check if value exists and is not N/A
        if (!value || value === 'N/A' || value === 'Not assigned') {
            showToast(`No ${type} to copy`, 'warning');
            return;
        }

        // Use Clipboard API
        await navigator.clipboard.writeText(value);

        // Visual feedback on button
        if (buttonElement) {
            buttonElement.classList.add('success');
            const originalText = buttonElement.querySelector('.quick-action-text').textContent;
            buttonElement.querySelector('.quick-action-text').textContent = 'Copied!';

            setTimeout(() => {
                buttonElement.classList.remove('success');
                buttonElement.querySelector('.quick-action-text').textContent = originalText;
            }, 2000);
        }

        // Toast notification
        showToast(`${type} copied to clipboard`, 'success');

    } catch (err) {
        console.error('Failed to copy:', err);
        showToast(`Failed to copy ${type}`, 'error');
    }
}

/**
 * Open email client with user's email
 */
function emailUser(userEmail) {
    if (!userEmail || userEmail === 'N/A' || userEmail === 'Not assigned') {
        showToast('No user email available', 'warning');
        return;
    }

    window.location.href = `mailto:${userEmail}`;
    showToast('Opening email client...', 'info');
}

/**
 * Open external link in new tab
 */
function openExternalLink(url, serviceName) {
    if (!url) {
        showToast(`Cannot open ${serviceName}`, 'error');
        return;
    }

    window.open(url, '_blank');
    showToast(`Opening ${serviceName}...`, 'info');
}

/**
 * Generate Quick Actions Panel HTML for a device
 */
function generateQuickActionsPanel(device) {
    const serialNumber = device.serialNumber || 'N/A';
    const macAddress = device.macAddress || 'N/A';
    const assetTag = device.assetTag || 'N/A';
    const deviceId = device.deviceId || device.serialNumber;
    const assetId = device.assetId || '';
    const deviceType = device.deviceType || '';

    // Check if this is a Chromebook
    const isChromebook = deviceType === 'Chromebooks';

    // Construct URLs
    const googleAdminUrl = (deviceId && isChromebook) ? `https://admin.google.com/ac/chrome/devices/${deviceId}?journey=217` : '';
    const iiqUrl = assetId ? `https://crsd.incidentiq.com/agent/assets/${assetId}?asset-details-tab=details` : '';

    // Check if external links are valid
    const hasGoogleLink = googleAdminUrl !== '';
    const hasIiqLink = iiqUrl !== '';

    return `
        <div class="quick-actions-panel">
            <div class="quick-actions-header">⚡ Quick Actions</div>
            <div class="quick-actions-buttons">
                <button class="quick-action-btn" onclick="copyToClipboard('Serial Number', '${escapeHtml(serialNumber)}', this)" title="Copy serial number to clipboard">
                    <span class="quick-action-icon">📋</span>
                    <span class="quick-action-text">Copy Serial</span>
                </button>
                <button class="quick-action-btn" onclick="copyToClipboard('MAC Address', '${escapeHtml(macAddress)}', this)" title="Copy MAC address to clipboard">
                    <span class="quick-action-icon">🌐</span>
                    <span class="quick-action-text">Copy MAC</span>
                </button>
                <button class="quick-action-btn" onclick="copyToClipboard('Asset Tag', '${escapeHtml(assetTag)}', this)" title="Copy asset tag to clipboard">
                    <span class="quick-action-icon">🏷️</span>
                    <span class="quick-action-text">Copy Asset Tag</span>
                </button>
                ${hasGoogleLink ? `
                <button class="quick-action-btn" onclick="openExternalLink('${escapeHtml(googleAdminUrl)}', 'Google Admin')" title="Open in Google Admin Console (Chromebooks only)">
                    <span class="quick-action-icon">⚙️</span>
                    <span class="quick-action-text">Google Admin</span>
                </button>
                ` : ''}
                ${hasIiqLink ? `
                <button class="quick-action-btn" onclick="openExternalLink('${escapeHtml(iiqUrl)}', 'IncidentIQ')" title="Open in IncidentIQ">
                    <span class="quick-action-icon">📊</span>
                    <span class="quick-action-text">IncidentIQ</span>
                </button>
                ` : ''}
            </div>
        </div>
    `;
}

/**
 * Escape HTML special characters to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
