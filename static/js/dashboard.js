// Version marker for debugging cache issues
console.log('🔄 ✅ PRODUCTION - DEC25 - COLLAPSIBLE USERS + DEVICE LISTS ✅');

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
    initializeDashboardWidgets();
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

// ============================================================
// DASHBOARD WIDGETS - AUE & SECURITY ALERTS
// ============================================================

async function fetchAueExpirationData(forceRefresh = false) {
    try {
        const url = `/api/dashboard/aue-expiration${forceRefresh ? '?force_refresh=true' : ''}`;
        const res = await fetch(url);
        const data = await res.json();

        if (res.ok) {
            updateAueExpirationWidget(data);
        } else {
            displayWidgetError('aue');
        }
    } catch (e) {
        console.error('AUE expiration fetch error:', e);
        displayWidgetError('aue');
    }
}

async function fetchSecurityAlertsData(forceRefresh = false) {
    try {
        const url = `/api/dashboard/security-alerts${forceRefresh ? '?force_refresh=true' : ''}`;
        const res = await fetch(url);
        const data = await res.json();

        if (res.ok) {
            updateSecurityAlertsWidget(data);
        } else {
            displayWidgetError('security');
        }
    } catch (e) {
        console.error('Security alerts fetch error:', e);
        displayWidgetError('security');
    }
}

function updateAueExpirationWidget(data) {
    const container = document.getElementById('aueYearsContainer');
    const currentYear = data.currentYear || new Date().getFullYear();

    // Update expired count
    document.getElementById('aueExpiredCount').textContent = data.expiredCount.toLocaleString();

    // Clear loading state
    container.innerHTML = '';

    // Check if we have year data
    if (!data.years || data.years.length === 0) {
        container.innerHTML = '<div class="aue-loading">No AUE data available</div>';
        return;
    }

    // Create tiles for each year
    data.years.forEach(yearData => {
        const tile = document.createElement('div');
        tile.className = 'aue-year-tile';

        // Add color coding based on year proximity
        const yearDiff = yearData.year - currentYear;
        if (yearDiff === 0) {
            tile.classList.add('current-year');
        } else if (yearDiff <= 2) {
            tile.classList.add('near-future');
        } else {
            tile.classList.add('far-future');
        }

        // Create tile content
        tile.innerHTML = `
            <div class="aue-year-count">${yearData.count.toLocaleString()}</div>
            <div class="aue-year-label">${yearData.year}</div>
            <div class="aue-tooltip">
                <div class="aue-tooltip-header">${yearData.count.toLocaleString()} device${yearData.count !== 1 ? 's' : ''} expiring in ${yearData.year}</div>
                <div class="aue-tooltip-models">
                    ${yearData.models.map(m => `<div class="aue-tooltip-model">${m.count.toLocaleString()} | ${m.model}</div>`).join('')}
                </div>
            </div>
        `;

        container.appendChild(tile);
    });
}

function updateSecurityAlertsWidget(data) {
    document.getElementById('devModeCount').textContent = data.devModeCount.toLocaleString();
    document.getElementById('poorBatteryCount').textContent = data.poorBatteryCount.toLocaleString();
    document.getElementById('pendingRepairsCount').textContent = data.pendingRepairsCount.toLocaleString();
    document.getElementById('totalAlerts').textContent = data.totalAlerts.toLocaleString();
}

function displayWidgetError(widgetType) {
    const errorText = 'Error';
    if (widgetType === 'aue') {
        const container = document.getElementById('aueYearsContainer');
        container.innerHTML = '<div class="aue-loading" style="color: #f44336;">Error loading AUE data</div>';
        document.getElementById('aueExpiredCount').textContent = errorText;
    } else if (widgetType === 'security') {
        document.getElementById('devModeCount').textContent = errorText;
        document.getElementById('poorBatteryCount').textContent = errorText;
        document.getElementById('pendingRepairsCount').textContent = errorText;
        document.getElementById('totalAlerts').textContent = errorText;
    }
}

async function refreshWidgets() {
    const refreshIcon = document.getElementById('widgetRefreshIcon');
    const originalIcon = refreshIcon.textContent;

    refreshIcon.classList.add('loading-spinner');

    try {
        const res = await fetch('/api/dashboard/refresh-widgets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) throw new Error('Failed to refresh widget cache');

        await Promise.all([
            fetchAueExpirationData(true),
            fetchSecurityAlertsData(true)
        ]);

        showToast('Dashboard widgets refreshed successfully', 'success');
        refreshIcon.classList.remove('loading-spinner');
        refreshIcon.textContent = '✅';
        setTimeout(() => { refreshIcon.textContent = originalIcon; }, 2000);

    } catch (e) {
        console.error('Widget refresh failed:', e);
        showToast('Failed to refresh dashboard widgets', 'error');
        refreshIcon.classList.remove('loading-spinner');
        refreshIcon.textContent = '❌';
        setTimeout(() => { refreshIcon.textContent = originalIcon; }, 2000);
    }
}

function initializeDashboardWidgets() {
    fetchAueExpirationData();
    fetchSecurityAlertsData();
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

// Normalize field names from camelCase (simple search) to snake_case (advanced search format)
function normalizeDeviceFields(devices) {
    return devices.map(d => ({
        // Core fields
        asset_tag: d.assetTag || d.asset_tag,
        serial_number: d.serialNumber || d.serial_number,
        model: d.model,
        status: d.googleStatus || d.status,
        device_id: d.deviceId || d.device_id,
        iiq_asset_id: d.assetId || d.iiq_asset_id,

        // User fields
        iiq_owner_name: d.iiqOwnerName || d.iiq_owner_name,
        iiq_owner_email: d.iiqOwnerEmail || d.iiq_owner_email,
        iiq_owner_student_id: d.iiqOwnerStudentId || d.iiq_owner_student_id,
        annotated_user: d.assignedUser || d.annotated_user,
        user_full_name: d.userFullName || d.user_full_name,

        // Location & org
        iiq_location: d.iiqLocation || d.iiq_location,
        iiq_room: d.iiqRoom || d.iiq_room,
        annotated_location: d.annotatedLocation || d.annotated_location,
        org_unit_path: d.orgUnitPath || d.org_unit_path,

        // Battery & boot
        battery_health: d.batteryHealth || d.battery_health,
        boot_mode: d.bootMode || d.boot_mode,

        // Dates & versions
        auto_update_expiration: d.aueDate || d.auto_update_expiration,
        iiq_status: d.iiqStatus || d.iiq_status,
        mac_address: d.macAddress || d.mac_address,
        ip_address: d.ipAddress || d.ip_address,
        wan_ip_address: d.wanIpAddress || d.wan_ip_address,
        os_version: d.osVersion || d.os_version,
        last_used_date: d.lastUsedDate || d.last_used_date,
        recent_users: d.recentUsers || d.recent_users || [],
        iiq_asset_id: d.assetId || d.iiq_asset_id
    }));
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
        // Normalize field names and use the same display function as advanced search
        const normalizedData = {
            devices: normalizeDeviceFields(data.devices || []),
            total_count: data.count || 0
        };
        displayAdvancedSearchResults(normalizedData);
        // Format info display to match advanced search style
        document.getElementById('searchInfo').innerHTML=`<div style="color:var(--text-secondary);margin-bottom:15px"><strong>${(data.count || 0).toLocaleString()}</strong> device(s) found</div>`;
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
        const iiqLink = `https://crsd.incidentiq.com/agent/assets/${device.assetId || ''}`;
        const googleLink = `https://admin.google.com/ac/chrome/devices/${device.deviceId || device.serialNumber}?journey=217`;

        // User information
        const userEmail = device.iiqOwnerEmail || device.assignedUser || 'Not assigned';
        const hasIiqUser = !!device.iiqOwnerEmail;
        const hasGoogleUser = device.assignedUser && device.assignedUser !== 'Not assigned';
        const userSource = hasIiqUser
            ? '<span class="field-badge badge-iiq">IIQ Official</span>'
            : (hasGoogleUser ? '<span class="field-badge badge-google">Google</span>' : '');

        // Build user name with student ID
        let userName = '';
        if (device.iiqOwnerName && device.iiqOwnerEmail) {
            const studentIdText = device.iiqOwnerStudentId ? ` (${escapeHtml(device.iiqOwnerStudentId)})` : '';
            userName = `<div class="field-value-secondary">${escapeHtml(device.iiqOwnerName)}${studentIdText}</div>`;
        }

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

function generateQuickActionsCompact(device, isChromebook) {
    const serialNumber = device.serialNumber || 'N/A';
    const macAddress = device.macAddress || 'N/A';
    const assetTag = device.assetTag || 'N/A';
    const deviceId = device.deviceId || device.serialNumber;
    const assetId = device.assetId || '';

    // Construct URLs
    const googleAdminUrl = (deviceId && isChromebook) ? `https://admin.google.com/ac/chrome/devices/${deviceId}?journey=217` : '';
    const iiqUrl = assetId ? `https://crsd.incidentiq.com/agent/assets/${assetId}` : '';

    // Check if external links are valid
    const hasGoogleLink = googleAdminUrl !== '';
    const hasIiqLink = iiqUrl !== '';

    // Google G icon SVG
    const googleIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>`;

    // IncidentIQ icon (using their blue color scheme)
    const iiqIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="7" height="7" rx="1" fill="#365C96"/><rect x="13" y="3" width="7" height="7" rx="1" fill="#365C96"/><rect x="3" y="13" width="7" height="7" rx="1" fill="#365C96"/><rect x="13" y="13" width="7" height="7" rx="1" fill="#365C96"/></svg>`;

    // Escape for HTML attributes (simple version - only escape quotes and angle brackets)
    const attrEscape = (str) => String(str).replace(/"/g, '&quot;').replace(/'/g, '&#39;');

    return `
        <div class="quick-actions-compact">
            ${hasGoogleLink ? `<button class="quick-action-btn-compact" onclick="window.open('${googleAdminUrl}', '_blank')" title="Open in Google Admin">${googleIcon} Google</button>` : ''}
            ${hasIiqLink ? `<button class="quick-action-btn-compact" onclick="window.open('${iiqUrl}', '_blank')" title="Open in IncidentIQ">${iiqIcon} IIQ</button>` : ''}
            <button class="quick-action-btn-compact copy-btn" data-copy-type="Serial" data-copy-value="${attrEscape(serialNumber)}" title="Copy serial">📋 Serial</button>
            ${macAddress !== 'N/A' ? `<button class="quick-action-btn-compact copy-btn" data-copy-type="MAC" data-copy-value="${attrEscape(macAddress)}" title="Copy MAC">🌐 MAC</button>` : ''}
            <button class="quick-action-btn-compact copy-btn" data-copy-type="Asset Tag" data-copy-value="${attrEscape(assetTag)}" title="Copy asset tag">🏷️ Asset</button>
        </div>
    `;
}

function generateBatteryBadge(device) {
    if (!device.batteryHealth && device.batteryHealth !== 0) {
        return '';
    }

    const health = device.batteryHealth;
    let badgeClass = 'badge-battery-excellent';
    let icon = '🔋';
    let label = 'Battery';

    if (health < 30) {
        badgeClass = 'badge-battery-critical';
        icon = '🔴';
        label = 'Battery';
    } else if (health < 50) {
        badgeClass = 'badge-battery-warning';
        icon = '⚠️';
        label = 'Battery';
    } else if (health < 70) {
        badgeClass = 'badge-battery-fair';
        icon = '🟡';
        label = 'Battery';
    } else if (health < 90) {
        badgeClass = 'badge-battery-good';
        icon = '🟢';
        label = 'Battery';
    }

    return `<span class="device-badge ${badgeClass}" title="Battery Health: ${health}%">${icon} ${label}: ${health}%</span>`;
}

function generateCardHeader(device, isChromebook, typeIcon, badgeClass, status, iiqLink) {
    return `
        <div class="device-header">
            <div class="device-header-top">
                <div class="device-primary-info">
                    <div class="device-asset-tag">
                        <a href="${iiqLink}" target="_blank" title="View in IncidentIQ">
                            <span class="asset-icon">🏷️</span>
                            <span>${escapeHtml(device.assetTag)}</span>
                        </a>
                    </div>
                    <div class="device-subtitle">Serial: ${escapeHtml(device.serialNumber)}</div>
                </div>
                ${generateQuickActionsCompact(device, isChromebook)}
            </div>
            <div class="device-header-bottom">
                <div class="status-heading">Statuses:</div>
                <div class="device-status-badges">
                    <span class="device-badge ${badgeClass}">
                        <span class="status-indicator"></span>
                        <span>🌐 Google: ${status}</span>
                    </span>
                    ${device.iiqStatus ? `<span class="device-badge badge-iiq-status">🎫 IIQ: ${escapeHtml(device.iiqStatus)}</span>` : ''}
                    ${isChromebook ? generateBatteryBadge(device) : ''}
                </div>
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
        </div>
    `;
}

function generatePriorityFields(device, isChromebook, googleLink, userEmail, userSource, userName) {
    // Check for user mismatch (only for Chromebooks with both assigned and last known user)
    let userMismatchWarning = '';
    if (isChromebook && device.lastKnownUser && device.lastKnownUser !== 'N/A') {
        const assignedUserEmail = (device.iiqOwnerEmail || device.assignedUser || '').toLowerCase();
        const lastKnownEmail = device.lastKnownUser.toLowerCase();

        if (assignedUserEmail && assignedUserEmail !== 'not assigned' && assignedUserEmail !== lastKnownEmail) {
            userMismatchWarning = `<div class="field-warning">⚠️ User mismatch: Device recently used by different user</div>`;
        }
    }

    return `
        <!-- USER INFORMATION -->
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">👤</span>
                <span>Assigned User</span>
                ${userSource}
            </div>
            <div class="field-value">
                ${escapeHtml(userEmail)}
                ${userName}
                ${userMismatchWarning}
            </div>
        </div>

        ${isChromebook && device.lastKnownUser ? `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🕐</span>
                <span>Last Known User</span>
            </div>
            <div class="field-value">${escapeHtml(device.lastKnownUser)}</div>
        </div>
        ` : ''}

        <!-- DEVICE INFORMATION -->
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

        ${isChromebook && device.orgUnitPath ? `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">📁</span>
                <span>Org Unit Path</span>
            </div>
            <div class="field-value">${escapeHtml(device.orgUnitPath)}</div>
        </div>
        ` : ''}

        <!-- NETWORK INFORMATION -->
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

        <!-- SOFTWARE INFORMATION -->
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">💿</span>
                <span>OS Version</span>
            </div>
            <div class="field-value">${escapeHtml(device.osVersion || 'N/A')}</div>
        </div>

        ${isChromebook && device.lastSync ? `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🔄</span>
                <span>Last Sync</span>
            </div>
            <div class="field-value">${fmt(device.lastSync)}</div>
        </div>
        ` : ''}
    `;
}

function generateBatteryDetails(device) {
    if (!device.batteryHealth && device.batteryHealth !== 0) {
        return '';
    }

    let cycleWarning = '';
    if (device.batteryCycleCount && device.batteryCycleCount > 500) {
        cycleWarning = ' <span style="color: #ff9800;">⚠️ High</span>';
    }

    let capacityLoss = '';
    if (device.batteryFullChargeCapacity && device.batteryDesignCapacity) {
        const loss = Math.round((1 - (device.batteryFullChargeCapacity / device.batteryDesignCapacity)) * 100);
        if (loss > 10) {
            capacityLoss = ` <span style="color: #999;">(${loss}% degraded)</span>`;
        }
    }

    return `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🔋</span>
                <span>Battery Health</span>
            </div>
            <div class="field-value">${device.batteryHealth}%${capacityLoss}</div>
        </div>
        ${device.batteryCycleCount ? `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">🔄</span>
                <span>Charge Cycles</span>
            </div>
            <div class="field-value">${device.batteryCycleCount}${cycleWarning}</div>
        </div>
        ` : ''}
        ${device.batteryFullChargeCapacity && device.batteryDesignCapacity ? `
        <div class="device-field">
            <div class="field-label">
                <span class="field-icon">⚡</span>
                <span>Battery Capacity</span>
            </div>
            <div class="field-value">${device.batteryFullChargeCapacity} / ${device.batteryDesignCapacity} mAh</div>
        </div>
        ` : ''}
    `;
}

function generateChromebookFields(device) {
    return `
        <!-- BATTERY INFORMATION -->
        ${generateBatteryDetails(device)}
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

// Advanced Search Functions
function toggleAdvancedSearch() {
    const panel = document.getElementById('advancedSearchPanel');
    const toggle = document.querySelector('.advanced-search-toggle');
    const icon = document.getElementById('advancedSearchToggleIcon');

    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
        toggle.classList.add('expanded');
        icon.textContent = '▲';
    } else {
        panel.style.display = 'none';
        toggle.classList.remove('expanded');
        icon.textContent = '▼';
    }
}

function clearAdvancedFilters() {
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterModel').value = '';
    document.getElementById('filterLocation').value = '';
    document.getElementById('filterOrgUnit').value = '';
    document.getElementById('filterBattery').value = '';
    document.getElementById('filterBootMode').value = '';
    document.getElementById('filterAueYear').value = '';
    document.getElementById('filterRepairStatus').value = '';

    // Clear results
    document.getElementById('searchInfo').innerHTML = '';
    document.getElementById('resultsContainer').innerHTML = '<div class="no-results">Enter search criteria</div>';

    showToast('Filters cleared', 'success');
}

async function advancedSearchDevices() {
    // Build query parameters from filters
    const params = new URLSearchParams();

    const status = document.getElementById('filterStatus').value;
    const model = document.getElementById('filterModel').value.trim();
    const location = document.getElementById('filterLocation').value.trim();
    const orgUnit = document.getElementById('filterOrgUnit').value.trim();
    const battery = document.getElementById('filterBattery').value;
    const bootMode = document.getElementById('filterBootMode').value;
    const aueYear = document.getElementById('filterAueYear').value;
    const repairStatus = document.getElementById('filterRepairStatus').value;

    // Add non-empty filters to params
    if (status) params.append('status', status);
    if (model) params.append('model', model);
    if (location) params.append('location', location);
    if (orgUnit) params.append('org_unit', orgUnit);
    if (bootMode) params.append('boot_mode', bootMode);
    if (aueYear) params.append('aue_year', aueYear);
    if (repairStatus) params.append('repair_status', repairStatus);

    // Handle battery range
    if (battery) {
        const [min, max] = battery.split('-').map(Number);
        params.append('battery_min', min);
        params.append('battery_max', max);
    }

    // Check if at least one filter is set
    if (params.toString() === '') {
        showToast('Please select at least one filter', 'warning');
        return;
    }

    // Show loading state
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = '<div style="text-align:center;padding:40px"><div class="loading-spinner"></div><div style="margin-top:15px;color:var(--text-secondary)">Searching devices...</div></div>';

    try {
        const res = await fetch(`/api/devices/advanced-search?${params.toString()}`);
        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || 'Search failed');

        // Display results
        displayAdvancedSearchResults(data);

        // Update search info
        const activeFilters = [];
        if (status) activeFilters.push(`Status: ${status}`);
        if (model) activeFilters.push(`Model: ${model}`);
        if (location) activeFilters.push(`Location: ${location}`);
        if (orgUnit) activeFilters.push(`Org Unit: ${orgUnit}`);
        if (battery) activeFilters.push(`Battery: ${battery}%`);
        if (bootMode) activeFilters.push(`Boot: ${bootMode}`);
        if (aueYear) activeFilters.push(`AUE: ${aueYear}`);
        if (repairStatus) activeFilters.push(`Repair: ${repairStatus}`);

        document.getElementById('searchInfo').innerHTML = `
            <div style="color:var(--text-secondary);margin-bottom:15px">
                <strong>${data.total_count.toLocaleString()}</strong> device(s) found
                <br><small>Filters: ${activeFilters.join(', ')}</small>
            </div>
        `;

        showToast(`Found ${data.total_count.toLocaleString()} devices`, 'success');

    } catch (e) {
        console.error('Advanced search error:', e);
        resultsContainer.innerHTML = '<div class="error-message">Search failed. Please try again.</div>';
        showToast('Search failed', 'error');
    }
}

function displayAdvancedSearchResults(data) {
    const container = document.getElementById('resultsContainer');

    if (!data.devices || data.devices.length === 0) {
        container.innerHTML = '<div class="no-results">No devices found matching the criteria</div>';
        return;
    }

    let html = '';

    data.devices.forEach(device => {
        // Prioritize IIQ data (cleaner), fallback to Google data
        const assetTag = device.asset_tag || 'N/A';
        const serialNumber = device.serial_number || 'N/A';
        const model = device.model || 'N/A';
        const status = device.status || 'N/A';

        // User name priority: IIQ owner name > User full name from users table > Unassigned (don't use email as name)
        const userName = device.iiq_owner_name || device.userFullName || 'Unassigned';
        // User email priority: IIQ owner email > Google annotated user
        const userEmail = device.iiq_owner_email || device.annotated_user || '';
        const location = device.iiq_location || device.annotated_location || 'Unknown';
        const room = device.iiq_room || '';
        const batteryHealth = device.battery_health !== null ? device.battery_health : null;
        const bootMode = device.boot_mode || 'N/A';

        // Format AUE date as "Month Year" (e.g., "June 2027")
        let aueDate = 'N/A';
        if (device.auto_update_expiration && device.auto_update_expiration !== 'N/A') {
            try {
                const aueDateTime = new Date(device.auto_update_expiration);
                aueDate = aueDateTime.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
            } catch (e) {
                aueDate = device.auto_update_expiration;
            }
        }
        const iiqStatus = device.iiq_status || 'N/A';
        const macAddress = device.mac_address || 'N/A';
        const ipAddress = device.ip_address || 'N/A';
        const wanIpAddress = device.wan_ip_address || 'N/A';
        const osVersion = device.os_version || 'N/A';
        const lastUsed = device.last_used_date ? new Date(device.last_used_date).toLocaleDateString() : 'N/A';
        const orgUnit = device.org_unit_path || 'N/A';
        const studentId = device.iiqOwnerStudentId || null;
        const studentGrade = device.studentGrade || null;

        // Extract email addresses from recent_users array
        let recentUsers = [];
        if (device.recent_users && Array.isArray(device.recent_users)) {
            recentUsers = device.recent_users.map(u => u.email || u).filter(email => email);
        }

        // Build external links
        // IIQ: Prefer direct asset link if available, otherwise use search by serial number
        let iiqUrl = null;
        if (device.iiq_asset_id) {
            iiqUrl = `https://crsd.incidentiq.com/agent/assets/${device.iiq_asset_id}`;
        } else if (serialNumber && serialNumber !== 'N/A') {
            // Fallback: Search IIQ by serial number
            iiqUrl = `https://crsd.incidentiq.com/agent/search?query=${encodeURIComponent(serialNumber)}`;
        }

        const googleUrl = device.device_id ? `https://admin.google.com/ac/chrome/devices/${device.device_id}?journey=217` : null;

        // Battery health styling
        let batteryClass = '';
        let batteryDisplay = 'N/A';
        if (batteryHealth !== null) {
            batteryDisplay = `${batteryHealth}%`;
            if (batteryHealth < 30) batteryClass = 'battery-critical';
            else if (batteryHealth < 50) batteryClass = 'battery-low';
            else if (batteryHealth < 80) batteryClass = 'battery-good';
            else batteryClass = 'battery-excellent';
        }

        html += `
            <div class="device-card">
                <div class="card-header">
                    <div class="card-title">
                        <strong class="primary-identifier">${assetTag}</strong>
                        <span class="secondary-identifier">SN: ${serialNumber}</span>
                    </div>
                    <div class="status-badge status-${status.toLowerCase()}">${status}</div>
                </div>
                <div class="card-body">
                    <!-- Quick Actions Row -->
                    <div class="quick-actions-compact" style="margin-bottom: 16px;">
                        <button class="quick-action-btn-compact" onclick="copyToClipboard('Asset Tag', '${assetTag}', this)" title="Copy asset tag">
                            📋 ${assetTag}
                        </button>
                        <button class="quick-action-btn-compact" onclick="copyToClipboard('Serial', '${serialNumber}', this)" title="Copy serial number">
                            📋 ${serialNumber}
                        </button>
                        ${macAddress !== 'N/A' ? `
                        <button class="quick-action-btn-compact" onclick="copyToClipboard('MAC', '${macAddress}', this)" title="Copy MAC address">
                            📋 ${macAddress}
                        </button>
                        ` : ''}
                        ${iiqUrl ? `
                        <a href="${iiqUrl}" target="_blank" class="external-link-btn iiq-link" title="Open in IncidentIQ">
                            <img src="/static/images/iiq-icon.svg" alt="IIQ" style="width: 16px; height: 16px; vertical-align: middle; margin-right: 4px;"> IIQ
                        </a>
                        ` : ''}
                        ${googleUrl ? `
                        <a href="${googleUrl}" target="_blank" class="external-link-btn google-link" title="Open in Google Admin">
                            <img src="/static/images/google-icon.svg" alt="Google" style="width: 16px; height: 16px; vertical-align: middle; margin-right: 4px;"> Google
                        </a>
                        ` : ''}
                    </div>

                    <!-- Device Info Grid with Composite Tiles -->
                    <div class="device-info-grid">
                        <!-- COMPOSITE: Model + AUE Date -->
                        <div class="info-row model-aue-tile">
                            <div class="model-aue-item">
                                <span class="info-label">Model:</span>
                                <span class="info-value">${model}</span>
                            </div>
                            <div class="model-aue-item">
                                <span class="info-label">AUE:</span>
                                <span class="info-value">${aueDate}</span>
                            </div>
                        </div>

                        <!-- COMPOSITE: User Info (Name + Email + Student ID) -->
                        <div class="info-row user-composite-tile">
                            <div class="user-detail-row">
                                <span class="user-icon">👤</span>
                                <span class="user-text"><strong>${userName}</strong></span>
                            </div>
                            <div class="user-detail-row">
                                <span class="user-icon">📧</span>
                                <span class="user-text clickable" onclick="copyToClipboard('User Email', '${userEmail}', this)" title="Click to copy: ${userEmail}">${userEmail}</span>
                            </div>
                            ${studentId ? `
                            <div class="user-detail-row">
                                <span class="user-icon">🎓</span>
                                <span class="user-text">Student ID: ${studentId}</span>
                            </div>
                            ` : ''}
                        </div>

                        <!-- Location -->
                        <div class="info-row">
                            <span class="info-label">Location:</span>
                            <span class="info-value">${location}${room ? ` - ${room}` : ''}</span>
                        </div>

                        <!-- Org Unit -->
                        <div class="info-row">
                            <span class="info-label">Org Unit:</span>
                            <span class="info-value">${orgUnit}</span>
                        </div>

                        <!-- COMPOSITE: Network Info (LAN IP + WAN IP + MAC) -->
                        ${ipAddress !== 'N/A' || wanIpAddress !== 'N/A' || macAddress !== 'N/A' ? `
                        <div class="info-row network-composite-tile">
                            <div class="network-item">
                                <span class="mini-label">LAN IP</span>
                                <span class="mini-value clickable" onclick="copyToClipboard('LAN IP', '${ipAddress}', this)" title="Click to copy">${ipAddress}</span>
                            </div>
                            <div class="network-item">
                                <span class="mini-label">WAN IP</span>
                                <span class="mini-value clickable ${!wanIpAddress.startsWith('167') && wanIpAddress !== 'N/A' ? 'wan-ip-warning' : ''}" onclick="copyToClipboard('WAN IP', '${wanIpAddress}', this)" title="Click to copy">${wanIpAddress}</span>
                            </div>
                            <div class="network-item">
                                <span class="mini-label">MAC</span>
                                <span class="mini-value clickable" onclick="copyToClipboard('MAC', '${macAddress}', this)" title="Click to copy">${macAddress}</span>
                            </div>
                        </div>
                        ` : ''}

                        <!-- COMPOSITE: System Info (Battery + Boot Mode + OS Version + Last Used) -->
                        <div class="info-row system-composite-tile">
                            <div class="system-stat">
                                <span class="stat-label">Battery</span>
                                <span class="stat-value ${batteryClass}">${batteryDisplay}</span>
                            </div>
                            <div class="system-stat">
                                <span class="stat-label">Boot</span>
                                <span class="stat-value ${bootMode === 'Dev' ? 'boot-dev-mode' : 'boot-verified'}">${bootMode}</span>
                            </div>
                            <div class="system-stat">
                                <span class="stat-label">OS</span>
                                <span class="stat-value">${osVersion}</span>
                            </div>
                            <div class="system-stat">
                                <span class="stat-label">Last Used</span>
                                <span class="stat-value">${lastUsed}</span>
                            </div>
                        </div>

                        <!-- IIQ Status (if exists) -->
                        ${iiqStatus !== 'N/A' ? `
                        <div class="info-row">
                            <span class="info-label">Repair Status:</span>
                            <span class="info-value">${iiqStatus}</span>
                        </div>
                        ` : ''}
                    </div>

                    <!-- Recent Users Section -->
                    ${recentUsers && recentUsers.length > 0 ? `
                    <div class="recent-users-section">
                        <div class="recent-users-header">Recent Sign-Ins (Last 5 Users)</div>
                        <div class="recent-users-list">
                            ${recentUsers.slice(0, 5).map((user, index) => `
                                <div class="recent-user-item">
                                    <span class="recent-user-number">${index + 1}.</span>
                                    <span class="recent-user-email">${user}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

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
        const userCardId = `user-card-${userIndex}`;

        // Generate IIQ and Google links
        const googleAdminLink = userId ? `https://admin.google.com/ac/users/${userId}` : '#';
        const iiqSearchLink = `https://crsd.incidentiq.com/agent/search?query=${encodeURIComponent(u.email)}`;

        // Google G icon SVG
        const googleIcon = `<svg width="16" height="16" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/></svg>`;

        // IncidentIQ icon
        const iiqIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="7" height="7" rx="1" fill="#365C96"/><rect x="13" y="3" width="7" height="7" rx="1" fill="#365C96"/><rect x="3" y="13" width="7" height="7" rx="1" fill="#365C96"/><rect x="13" y="13" width="7" height="7" rx="1" fill="#365C96"/></svg>`;

        html += `
            <div class="device-card user-card" id="${userCardId}">
                <!-- User Header (Always Visible) -->
                <div class="device-header">
                    <div class="device-header-top">
                        <div class="device-primary-info" onclick="toggleUserCard('${userCardId}')" style="cursor: pointer; flex: 1;">
                            <div class="device-asset-tag">
                                <span class="asset-icon">👤</span>
                                <span>${escapeHtml(u.fullName)}${u.isStudent && u.studentId ? ` <span style="color: rgba(255,255,255,0.5); font-weight: 400; font-size: 0.75em;">(ID: ${escapeHtml(u.studentId)})</span>` : ''} ${u.feeBalance !== undefined && u.feeBalance !== null ? `<span style="color: ${u.feeBalance > 0 ? '#ff6b6b' : '#4caf50'}; font-weight: 500; margin-left: 8px; padding: 2px 6px; background: ${u.feeBalance > 0 ? 'rgba(255,107,107,0.15)' : 'rgba(76,175,80,0.15)'}; border-radius: 4px; font-size: 0.8em;">💰 $${u.feeBalance.toFixed(2)}</span>` : ''}</span>
                            </div>
                            <div class="device-subtitle">
                                ${escapeHtml(u.email)}
                                <span style="margin-left: 16px; color: rgba(255,255,255,0.7); font-size: 0.9em;">
                                    ${u.location ? `📍 ${escapeHtml(u.location)}` : ''}
                                    ${u.grade ? `<span style="margin-left: 12px;">🎓 Grade ${escapeHtml(u.grade)}</span>` : ''}
                                    ${u.googleOrgUnit ? `<span style="margin-left: 12px;">📁 ${escapeHtml(u.googleOrgUnit)}</span>` : ''}
                                </span>
                            </div>
                        </div>
                        <div class="quick-actions-compact" onclick="event.stopPropagation()">
                            ${userId ? `<button class="quick-action-btn-compact" onclick="window.open('${googleAdminLink}', '_blank')" title="Open in Google Admin">${googleIcon} Google</button>` : ''}
                            <button class="quick-action-btn-compact" onclick="window.open('${iiqSearchLink}', '_blank')" title="Search in IncidentIQ">${iiqIcon} IIQ</button>
                            <button class="quick-action-btn-compact copy-btn" data-copy-type="Email" data-copy-value="${escapeHtml(u.email)}" title="Copy email">📋 Email</button>
                            <span id="${userCardId}-icon" onclick="toggleUserCard('${userCardId}')" style="font-size: 20px; color: var(--primary-color); transition: transform 0.2s; cursor: pointer; margin-left: 8px;">▶</span>
                        </div>
                    </div>
                    <div class="device-header-bottom" onclick="toggleUserCard('${userCardId}')" style="cursor: pointer;">
                        <div class="status-heading">Status:</div>
                        <div class="device-status-badges">
                            <span class="device-badge ${badgeClass}">
                                <span class="status-indicator"></span>
                                <span>Google: ${status}</span>
                            </span>
                            <span class="device-badge" style="background: rgba(0,163,255,0.15); color: var(--primary-color); border: 1px solid rgba(0,163,255,0.3);">
                                📦 Assigned Devices: ${u.iiqAssignedCount || 0}
                            </span>
                            <span class="device-badge" style="background: rgba(76,175,80,0.15); color: #4caf50; border: 1px solid rgba(76,175,80,0.3);">
                                🔐 Recent Devices: ${u.googleRecentCount || 0}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- User Details (Collapsible) -->
                <div id="${userCardId}-content" class="user-card-content" style="display: none;">
                    ${generateUserDetailsSection(u, userId, userIndex)}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function generateUserDetailsSection(u, userId, userIndex) {
    return `
        <div class="device-content">
            <!-- IIQ Assigned Devices -->
            ${generateUserDeviceSection(u.iiqAssignedDevices, 'IIQ Assigned Devices', '📦', 'iiq', userIndex)}

            <!-- Google Recent Logins -->
            ${generateUserDeviceSection(u.googleRecentDevices, 'Recent Logins (Last 5, Most Recent First)', '🔐', 'google', userIndex)}
        </div>
    `;
}

function toggleUserCard(cardId) {
    const content = document.getElementById(`${cardId}-content`);
    const icon = document.getElementById(`${cardId}-icon`);

    if (content.style.display === 'none') {
        content.style.display = 'block';
        icon.style.transform = 'rotate(90deg)';
        icon.textContent = '▼';
    } else {
        content.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
        icon.textContent = '▶';
    }
}

function generateUserDeviceSection(devices, title, icon, type, userIndex) {
    const sectionId = `user-${userIndex}-${type}-devices`;
    const deviceCount = devices ? devices.length : 0;

    let html = `
        <div class="user-devices-section">
            <div class="user-devices-header" style="background: rgba(0,163,255,0.08); padding: 10px 16px; margin: 0 -20px; border-top: 1px solid var(--card-border);">
                <span class="field-icon">${icon}</span>
                <span style="font-weight: 600; font-size: 0.95em;">${title}</span>
                <span style="margin-left: 8px; background: var(--primary-color); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">${deviceCount}</span>
            </div>
    `;

    // If no devices, show message
    if (!devices || devices.length === 0) {
        html += `
            <div class="user-devices-list empty-list" style="padding: 12px 0; color: rgba(255,255,255,0.5); font-style: italic;">
                No devices found
            </div>
        </div>
        `;
        return html;
    }

    html += `<div class="user-devices-list" style="padding-top: 8px;">`;

    devices.forEach((device, deviceIndex) => {
        const deviceId = `${sectionId}-${deviceIndex}`;
        const googleLink = device.deviceId ? `https://admin.google.com/ac/chrome/devices/${device.deviceId}?journey=217` : '#';
        const iiqLink = device.iiqAssetId ? `https://crsd.incidentiq.com/agent/assets/${device.iiqAssetId}` : '#';

        // Determine status badges
        const googleStatus = device.googleStatus || 'N/A';
        const googleBadgeClass = googleStatus === 'ACTIVE' ? 'badge-active' : 'badge-disabled';

        // Battery badge
        let batteryBadge = '';
        if (device.batteryHealth !== undefined && device.batteryHealth !== null) {
            const health = device.batteryHealth;
            let badgeClass = 'badge-battery-excellent';
            let batteryIcon = '🔋';

            if (health < 30) {
                badgeClass = 'badge-battery-critical';
                batteryIcon = '🔴';
            } else if (health < 50) {
                badgeClass = 'badge-battery-warning';
                batteryIcon = '⚠️';
            } else if (health < 70) {
                badgeClass = 'badge-battery-fair';
                batteryIcon = '🟡';
            } else if (health < 90) {
                badgeClass = 'badge-battery-good';
                batteryIcon = '🟢';
            }

            batteryBadge = `<span class="device-badge ${badgeClass}" title="Battery Health: ${health}%">${batteryIcon} Battery: ${health}%</span>`;
        }

        html += `
            <div class="user-device-item" style="border-bottom: 1px solid rgba(255,255,255,0.05); padding: 8px 0;">
                <div class="user-device-summary" onclick="toggleDeviceDetails('${deviceId}')" style="display: flex; justify-content: space-between; align-items: center; cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: background 0.2s;" onmouseover="this.style.background='rgba(0,163,255,0.08)'" onmouseout="this.style.background='transparent'">
                    <div class="user-device-info" style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap; flex: 1;">
                        <span class="user-device-asset" style="font-weight: 600; color: var(--primary-color);">🏷️ ${escapeHtml(device.assetTag)}</span>
                        <span class="user-device-serial" style="color: rgba(255,255,255,0.7); font-size: 0.9em;">SN: ${escapeHtml(device.serialNumber)}</span>
                        <span class="device-badge ${googleBadgeClass}" style="font-size: 0.75em;">🌐 ${googleStatus}</span>
                        ${batteryBadge ? `<span style="font-size: 0.75em;">${batteryBadge}</span>` : ''}
                    </div>
                    <div class="user-device-expand" style="margin-left: 12px;">
                        <span id="${deviceId}-icon" style="color: var(--primary-color); font-size: 16px; transition: transform 0.2s;">▶</span>
                    </div>
                </div>

                <div id="${deviceId}-details" class="user-device-details" style="display: none;">
                    <div class="device-grid" style="margin-top: 12px;">
                        <!-- DEVICE INFORMATION -->
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">💻</span><span>Model</span></div>
                            <div class="field-value">${escapeHtml(device.model || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📍</span><span>Location</span></div>
                            <div class="field-value">${escapeHtml(device.location || 'N/A')}</div>
                        </div>
                        ${device.room ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🚪</span><span>Room</span></div>
                            <div class="field-value">${escapeHtml(device.room)}</div>
                        </div>
                        ` : ''}
                        ${device.orgUnitPath ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📁</span><span>Org Unit Path</span></div>
                            <div class="field-value">${escapeHtml(device.orgUnitPath)}</div>
                        </div>
                        ` : ''}

                        <!-- STATUS INFORMATION -->
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌐</span><span>Google Status</span></div>
                            <div class="field-value">${escapeHtml(googleStatus)}</div>
                        </div>
                        ${device.iiqStatus ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🎫</span><span>IIQ Status</span></div>
                            <div class="field-value">${escapeHtml(device.iiqStatus)}</div>
                        </div>
                        ` : ''}

                        <!-- NETWORK INFORMATION -->
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌐</span><span>MAC Address</span></div>
                            <div class="field-value">${escapeHtml(device.macAddress || 'N/A')}</div>
                        </div>
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌍</span><span>LAN IP</span></div>
                            <div class="field-value">${escapeHtml(device.ipAddress || 'N/A')}</div>
                        </div>
                        ${device.wanIpAddress ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🌐</span><span>WAN IP</span></div>
                            <div class="field-value">${escapeHtml(device.wanIpAddress)}</div>
                        </div>
                        ` : ''}

                        <!-- SOFTWARE INFORMATION -->
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">💿</span><span>OS Version</span></div>
                            <div class="field-value">${escapeHtml(device.osVersion || 'N/A')}</div>
                        </div>
                        ${device.lastSync ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🔄</span><span>Last Sync</span></div>
                            <div class="field-value">${fmt(device.lastSync)}</div>
                        </div>
                        ` : ''}

                        <!-- BATTERY INFORMATION -->
                        ${device.batteryHealth !== undefined && device.batteryHealth !== null ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🔋</span><span>Battery Health</span></div>
                            <div class="field-value">${device.batteryHealth}%${device.batteryFullChargeCapacity && device.batteryDesignCapacity ? ` <span style="color: #999;">(${Math.round((1 - (device.batteryFullChargeCapacity / device.batteryDesignCapacity)) * 100)}% degraded)</span>` : ''}</div>
                        </div>
                        ` : ''}
                        ${device.batteryCycleCount ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🔄</span><span>Charge Cycles</span></div>
                            <div class="field-value">${device.batteryCycleCount}${device.batteryCycleCount > 500 ? ' <span style="color: #ff9800;">⚠️ High</span>' : ''}</div>
                        </div>
                        ` : ''}
                        ${device.batteryFullChargeCapacity && device.batteryDesignCapacity ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">⚡</span><span>Battery Capacity</span></div>
                            <div class="field-value">${device.batteryFullChargeCapacity} / ${device.batteryDesignCapacity} mAh</div>
                        </div>
                        ` : ''}

                        <!-- MERAKI INFORMATION -->
                        ${device.merakiApName ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">📡</span><span>Last Known AP</span></div>
                            <div class="field-value">
                                ${escapeHtml(device.merakiApName)}
                                ${device.merakiNetwork ? `<div class="field-value-secondary">${escapeHtml(device.merakiNetwork)}</div>` : ''}
                            </div>
                        </div>
                        ` : ''}
                        ${device.merakiLastSeen ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🕐</span><span>Meraki Last Seen</span></div>
                            <div class="field-value">
                                ${fmt(device.merakiLastSeen)}
                                ${device.merakiNote ? `<div class="field-value-secondary" style="color: ${device.merakiNewer ? 'var(--success-color)' : 'var(--warning-color)'}">${escapeHtml(device.merakiNote)}</div>` : ''}
                            </div>
                        </div>
                        ` : ''}

                        <!-- USER INFORMATION -->
                        ${device.lastKnownUser ? `
                        <div class="device-field">
                            <div class="field-label"><span class="field-icon">🕐</span><span>Last Known User</span></div>
                            <div class="field-value">${escapeHtml(device.lastKnownUser)}</div>
                        </div>
                        ` : ''}
                    </div>

                    <!-- RECENT USERS -->
                    ${device.recentUsers && device.recentUsers.length > 0 ? `
                    <div class="recent-users-section">
                        <div class="section-header">
                            <span>📋</span>
                            <span>Recent Users</span>
                        </div>
                        <div>
                            ${device.recentUsers.map(user => `<span class="user-chip">👤 ${escapeHtml(user)}</span>`).join('')}
                        </div>
                    </div>
                    ` : ''}

                    <!-- QUICK ACTIONS -->
                    <div class="quick-actions-panel" style="margin-top: 12px;">
                        <div class="quick-actions-buttons">
                            <button class="quick-action-btn" onclick="copyToClipboard('Serial', '${escapeHtml(device.serialNumber)}', this)">
                                <span class="quick-action-icon">📋</span>
                                <span class="quick-action-text">Copy Serial</span>
                            </button>
                            <button class="quick-action-btn" onclick="copyToClipboard('MAC', '${escapeHtml(device.macAddress || '')}', this)">
                                <span class="quick-action-icon">🌐</span>
                                <span class="quick-action-text">Copy MAC</span>
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

// Copy button event delegation
document.addEventListener('click', function(e) {
    const copyBtn = e.target.closest('.copy-btn');
    if (copyBtn) {
        e.preventDefault();
        e.stopPropagation();
        const type = copyBtn.getAttribute('data-copy-type');
        const value = copyBtn.getAttribute('data-copy-value');
        console.log('Copy button clicked:', type, value);
        copyToClipboard(type, value, copyBtn);
    }
});

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
    console.log('copyToClipboard called with:', {type, value, buttonElement});
    try {
        // Check if value exists and is not N/A
        if (!value || value === 'N/A' || value === 'Not assigned') {
            console.log('Value is N/A or not assigned');
            showToast(`No ${type} to copy`, 'warning');
            return;
        }

        console.log('Attempting to copy to clipboard:', value);

        // Try modern Clipboard API first, fallback to textarea method
        let copySuccess = false;

        if (navigator.clipboard && window.isSecureContext) {
            // Modern Clipboard API (requires HTTPS)
            try {
                await navigator.clipboard.writeText(value);
                copySuccess = true;
                console.log('Successfully copied using Clipboard API');
            } catch (clipboardErr) {
                console.warn('Clipboard API failed, trying fallback method:', clipboardErr);
            }
        }

        // Fallback method for HTTP (non-secure context)
        if (!copySuccess) {
            const textarea = document.createElement('textarea');
            textarea.value = value;
            textarea.style.position = 'fixed';
            textarea.style.left = '-999999px';
            textarea.style.top = '-999999px';
            document.body.appendChild(textarea);
            textarea.focus();
            textarea.select();

            try {
                const successful = document.execCommand('copy');
                if (successful) {
                    copySuccess = true;
                    console.log('Successfully copied using execCommand fallback');
                } else {
                    throw new Error('execCommand returned false');
                }
            } catch (execErr) {
                console.error('Fallback copy method also failed:', execErr);
                throw execErr;
            } finally {
                document.body.removeChild(textarea);
            }
        }

        if (!copySuccess) {
            throw new Error('All copy methods failed');
        }

        // Visual feedback on button
        if (buttonElement) {
            buttonElement.classList.add('success');

            // Check if it's a compact button (text directly in button) or regular button (text in .quick-action-text)
            const textElement = buttonElement.querySelector('.quick-action-text');
            if (textElement) {
                // Regular button
                const originalText = textElement.textContent;
                textElement.textContent = 'Copied!';

                setTimeout(() => {
                    buttonElement.classList.remove('success');
                    textElement.textContent = originalText;
                }, 2000);
            } else {
                // Compact button - just remove success class after delay
                setTimeout(() => {
                    buttonElement.classList.remove('success');
                }, 2000);
            }
        }

        // Toast notification
        showToast(`${type} copied to clipboard`, 'success');

    } catch (err) {
        console.error('Failed to copy - error details:', err);
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
    const iiqUrl = assetId ? `https://crsd.incidentiq.com/agent/assets/${assetId}` : '';

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
