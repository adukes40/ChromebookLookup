# Device Card Design - Implementation Examples

## Complete Working Examples

### Example 1: Active Chromebook Card

```html
<div class="device-card type-chromebook status-active">
    <!-- Card Header -->
    <div class="device-header">
        <div class="device-primary-info">
            <div class="device-asset-tag">
                <a href="https://crsd.incidentiq.com/agent/assets/12345?asset-details-tab=details"
                   target="_blank"
                   title="View in IncidentIQ">
                    <span class="asset-icon">🏷️</span>
                    <span>ASSET-12345</span>
                </a>
            </div>
            <div class="device-subtitle">Serial: 5CD1234ABC</div>
            <div class="device-type-badge type-chromebook">
                <span>💻</span>
                <span>Chromebooks</span>
            </div>
        </div>
        <div class="device-status-badges">
            <span class="device-badge badge-active">
                <span class="status-indicator"></span>
                <span>ACTIVE</span>
            </span>
            <span class="device-badge badge-iiq-status">IIQ: Active</span>
        </div>
    </div>

    <!-- Card Content -->
    <div class="device-content">
        <div class="device-grid">
            <!-- Serial Number -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🔢</span>
                    <span>Serial Number</span>
                </div>
                <div class="field-value">
                    <a href="https://admin.google.com/ac/chrome/devices/5CD1234ABC?journey=217"
                       target="_blank"
                       title="View in Google Admin Console">5CD1234ABC</a>
                </div>
            </div>

            <!-- Assigned User -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">👤</span>
                    <span>Assigned User</span>
                    <span class="field-badge badge-iiq">IIQ Official</span>
                </div>
                <div class="field-value">
                    john.doe@school.edu
                    <div class="field-value-secondary">John Doe</div>
                </div>
            </div>

            <!-- Model -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">💻</span>
                    <span>Model</span>
                </div>
                <div class="field-value">HP Chromebook 14 G6</div>
            </div>

            <!-- Location -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">📍</span>
                    <span>Location</span>
                </div>
                <div class="field-value">Building A - Room 101</div>
            </div>

            <!-- MAC Address -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🌐</span>
                    <span>MAC Address</span>
                </div>
                <div class="field-value">AA:BB:CC:DD:EE:FF</div>
            </div>

            <!-- IP Address -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🌍</span>
                    <span>IP Address</span>
                </div>
                <div class="field-value">10.1.2.3</div>
            </div>

            <!-- OS Version -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">💿</span>
                    <span>OS Version</span>
                </div>
                <div class="field-value">Chrome OS 118.0.5993.117</div>
            </div>

            <!-- Last Sync (Chromebook only) -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🔄</span>
                    <span>Last Sync</span>
                </div>
                <div class="field-value">12/24/2025, 2:30:15 PM</div>
            </div>

            <!-- Last Known User (Chromebook only) -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">👤</span>
                    <span>Last Known User</span>
                </div>
                <div class="field-value">john.doe@school.edu</div>
            </div>

            <!-- Org Unit (Chromebook only) -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">📁</span>
                    <span>Org Unit Path</span>
                </div>
                <div class="field-value">/Students/Grade 10</div>
            </div>

            <!-- Meraki AP -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">📡</span>
                    <span>Last Known AP</span>
                </div>
                <div class="field-value">
                    AP-BuildingA-Floor2
                    <div class="field-value-secondary">Main Campus Network</div>
                </div>
            </div>

            <!-- Meraki Last Seen -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🕐</span>
                    <span>Meraki Last Seen</span>
                </div>
                <div class="field-value">
                    12/24/2025, 2:45:00 PM
                    <div class="field-value-secondary" style="color: var(--success-color)">
                        Newer than Google (within 24h)
                    </div>
                </div>
            </div>
        </div>

        <!-- Recent Users Section -->
        <div class="recent-users-section">
            <div class="section-header">
                <span>📋</span>
                <span>Recent Users</span>
            </div>
            <div>
                <span class="user-chip">👤 john.doe@school.edu</span>
                <span class="user-chip">👤 jane.smith@school.edu</span>
                <span class="user-chip">👤 bob.wilson@school.edu</span>
            </div>
        </div>

        <!-- Quick Actions Panel -->
        <div class="quick-actions-panel">
            <div class="quick-actions-header">⚡ Quick Actions</div>
            <div class="quick-actions-buttons">
                <button class="quick-action-btn"
                        onclick="copyToClipboard('Serial Number', '5CD1234ABC', this)"
                        title="Copy serial number to clipboard">
                    <span class="quick-action-icon">📋</span>
                    <span class="quick-action-text">Copy Serial</span>
                </button>
                <button class="quick-action-btn"
                        onclick="copyToClipboard('MAC Address', 'AA:BB:CC:DD:EE:FF', this)"
                        title="Copy MAC address to clipboard">
                    <span class="quick-action-icon">🌐</span>
                    <span class="quick-action-text">Copy MAC</span>
                </button>
                <button class="quick-action-btn"
                        onclick="copyToClipboard('Asset Tag', 'ASSET-12345', this)"
                        title="Copy asset tag to clipboard">
                    <span class="quick-action-icon">🏷️</span>
                    <span class="quick-action-text">Copy Asset Tag</span>
                </button>
                <button class="quick-action-btn"
                        onclick="openExternalLink('https://admin.google.com/ac/chrome/devices/5CD1234ABC?journey=217', 'Google Admin')"
                        title="Open in Google Admin Console">
                    <span class="quick-action-icon">⚙️</span>
                    <span class="quick-action-text">Google Admin</span>
                </button>
                <button class="quick-action-btn"
                        onclick="openExternalLink('https://crsd.incidentiq.com/agent/assets/12345?asset-details-tab=details', 'IncidentIQ')"
                        title="Open in IncidentIQ">
                    <span class="quick-action-icon">📊</span>
                    <span class="quick-action-text">IncidentIQ</span>
                </button>
            </div>
        </div>
    </div>
</div>
```

---

### Example 2: Disabled iPad Card

```html
<div class="device-card type-ipad status-disabled">
    <!-- Card Header -->
    <div class="device-header">
        <div class="device-primary-info">
            <div class="device-asset-tag">
                <a href="https://crsd.incidentiq.com/agent/assets/67890?asset-details-tab=details"
                   target="_blank"
                   title="View in IncidentIQ">
                    <span class="asset-icon">🏷️</span>
                    <span>IPAD-67890</span>
                </a>
            </div>
            <div class="device-subtitle">Serial: DMQV2WXHJ1GH</div>
            <div class="device-type-badge type-ipad">
                <span>📱</span>
                <span>iPad</span>
            </div>
        </div>
        <div class="device-status-badges">
            <span class="device-badge badge-disabled">
                <span class="status-indicator"></span>
                <span>DISABLED</span>
            </span>
        </div>
    </div>

    <!-- Card Content -->
    <div class="device-content">
        <div class="device-grid">
            <!-- Serial Number (no Google link for iPad) -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🔢</span>
                    <span>Serial Number</span>
                </div>
                <div class="field-value">DMQV2WXHJ1GH</div>
            </div>

            <!-- Assigned User -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">👤</span>
                    <span>Assigned User</span>
                </div>
                <div class="field-value">Not assigned</div>
            </div>

            <!-- Model -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">💻</span>
                    <span>Model</span>
                </div>
                <div class="field-value">iPad (7th generation)</div>
            </div>

            <!-- Location -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">📍</span>
                    <span>Location</span>
                </div>
                <div class="field-value">IT Storage</div>
            </div>

            <!-- MAC Address -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🌐</span>
                    <span>MAC Address</span>
                </div>
                <div class="field-value">11:22:33:44:55:66</div>
            </div>

            <!-- IP Address -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">🌍</span>
                    <span>IP Address</span>
                </div>
                <div class="field-value">N/A</div>
            </div>

            <!-- OS Version -->
            <div class="device-field">
                <div class="field-label">
                    <span class="field-icon">💿</span>
                    <span>OS Version</span>
                </div>
                <div class="field-value">iOS 17.2.1</div>
            </div>
        </div>

        <!-- No Recent Users section -->

        <!-- Quick Actions Panel -->
        <div class="quick-actions-panel">
            <div class="quick-actions-header">⚡ Quick Actions</div>
            <div class="quick-actions-buttons">
                <button class="quick-action-btn"
                        onclick="copyToClipboard('Serial Number', 'DMQV2WXHJ1GH', this)">
                    <span class="quick-action-icon">📋</span>
                    <span class="quick-action-text">Copy Serial</span>
                </button>
                <button class="quick-action-btn"
                        onclick="copyToClipboard('MAC Address', '11:22:33:44:55:66', this)">
                    <span class="quick-action-icon">🌐</span>
                    <span class="quick-action-text">Copy MAC</span>
                </button>
                <button class="quick-action-btn"
                        onclick="copyToClipboard('Asset Tag', 'IPAD-67890', this)">
                    <span class="quick-action-icon">🏷️</span>
                    <span class="quick-action-text">Copy Asset Tag</span>
                </button>
                <button class="quick-action-btn"
                        onclick="openExternalLink('https://crsd.incidentiq.com/agent/assets/67890?asset-details-tab=details', 'IncidentIQ')">
                    <span class="quick-action-icon">📊</span>
                    <span class="quick-action-text">IncidentIQ</span>
                </button>
                <!-- No Google Admin button for iPad -->
            </div>
        </div>
    </div>
</div>
```

---

## JavaScript Generation Example

### Complete displayResults Function

```javascript
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
                <div class="device-type-badge ${isChromebook ? 'type-chromebook' : 'type-ipad'}">
                    <span>${typeIcon}</span>
                    <span>${escapeHtml(device.deviceType)}</span>
                </div>
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
                <span>IP Address</span>
            </div>
            <div class="field-value">${escapeHtml(device.ipAddress || 'N/A')}</div>
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
```

---

## CSS Customization Examples

### Example 1: Change Accent Color to Purple

```css
:root {
    --accent-color: #9b59b6; /* Purple */
}

/* Update button gradients */
.quick-action-btn {
    background: linear-gradient(135deg, rgba(155, 89, 182, 0.08) 0%, rgba(155, 89, 182, 0.04) 100%);
    border: 1px solid rgba(155, 89, 182, 0.3);
}

.quick-action-btn:hover {
    background: linear-gradient(135deg, rgba(155, 89, 182, 0.15) 0%, rgba(155, 89, 182, 0.08) 100%);
    border-color: #9b59b6;
    box-shadow: 0 4px 12px rgba(155, 89, 182, 0.2);
}

/* Update quick actions panel */
.quick-actions-panel {
    background: rgba(155, 89, 182, 0.03);
    border-top: 2px solid rgba(155, 89, 182, 0.2);
}
```

### Example 2: Increase Card Spacing

```css
.device-card {
    margin-bottom: 30px; /* Was 20px */
}

.device-grid {
    gap: 24px; /* Was 20px */
}

.device-header {
    padding: 30px 28px 20px 28px; /* Increased all sides */
}

.device-content {
    padding: 24px 28px; /* Increased horizontal */
}
```

### Example 3: Add Card Entrance Animation

```css
@keyframes cardSlideIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.device-card {
    animation: cardSlideIn 0.4s ease-out;
}

/* Stagger animation for multiple cards */
.device-card:nth-child(1) { animation-delay: 0s; }
.device-card:nth-child(2) { animation-delay: 0.1s; }
.device-card:nth-child(3) { animation-delay: 0.2s; }
.device-card:nth-child(4) { animation-delay: 0.3s; }
.device-card:nth-child(5) { animation-delay: 0.4s; }
```

### Example 4: Add Loading Skeleton

```css
.device-card.loading {
    pointer-events: none;
}

.device-card.loading * {
    background: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.02) 25%,
        rgba(255, 255, 255, 0.05) 50%,
        rgba(255, 255, 255, 0.02) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 2s infinite;
    color: transparent !important;
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}
```

---

## Testing Snippets

### Test Card Hover in Console

```javascript
// Add permanent hover state for testing
const card = document.querySelector('.device-card');
card.style.transform = 'translateY(-4px)';
card.style.boxShadow = '0 8px 24px rgba(0, 163, 255, 0.15)';
card.style.borderColor = 'var(--accent-color)';
```

### Test Button Success State

```javascript
// Manually trigger success state
const btn = document.querySelector('.quick-action-btn');
btn.classList.add('success');
btn.querySelector('.quick-action-text').textContent = 'Copied!';

setTimeout(() => {
    btn.classList.remove('success');
    btn.querySelector('.quick-action-text').textContent = 'Copy Serial';
}, 2000);
```

### Test Responsive Breakpoints

```javascript
// Resize viewport and log grid columns
function testBreakpoints() {
    const grid = document.querySelector('.device-grid');
    const columns = getComputedStyle(grid).gridTemplateColumns.split(' ').length;
    console.log(`Width: ${window.innerWidth}px, Columns: ${columns}`);
}

window.addEventListener('resize', testBreakpoints);
testBreakpoints();
```

---

## Browser Compatibility Notes

### Modern Browsers (Full Support)
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Features Used
- CSS Grid (all modern browsers)
- CSS Custom Properties (all modern browsers)
- CSS Gradients (all browsers)
- Transform/Transitions (all browsers)

### Progressive Enhancement
```css
/* Fallback for older browsers */
@supports not (display: grid) {
    .device-grid {
        display: flex;
        flex-wrap: wrap;
    }

    .device-field {
        flex: 1 1 280px;
    }
}
```

---

## Performance Tips

### Optimize Rendering

```javascript
// Use DocumentFragment for multiple cards
function displayResultsOptimized(devices) {
    const fragment = document.createDocumentFragment();
    const container = document.getElementById('resultsContainer');

    devices.forEach(device => {
        const card = createCardElement(device);
        fragment.appendChild(card);
    });

    // Single DOM update
    container.innerHTML = '';
    container.appendChild(fragment);
}
```

### Lazy Load Images (if added)

```html
<img src="placeholder.png"
     data-src="actual-image.png"
     loading="lazy"
     alt="Device image">
```

### Debounce Hover Effects on Mobile

```css
@media (hover: none) {
    .device-card:hover,
    .quick-action-btn:hover,
    .device-field:hover {
        /* Disable hover on touch devices */
        transform: none !important;
        box-shadow: initial !important;
    }
}
```

---

This completes the implementation examples. You now have working code samples for all components of the new design!
