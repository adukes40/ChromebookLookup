# Device Card Design - Quick Reference

## Visual Examples

### Card Color Coding (Left Border)

```
Chromebook + Active:  ║ Green gradient (#4caf50 → #2e7d32)
iPad:                 ║ Orange gradient (#ff9800 → #e65100)
Disabled:             ║ Red gradient (#f44336 → #c62828)
Default:              ║ Blue (#58a6ff)
```

### Status Badge Colors

```
✓ ACTIVE     → Green gradient background, white text, pulsing dot
✗ DISABLED   → Red gradient background, white text, pulsing dot
ⓘ IIQ Status → Blue gradient background, white text
```

### Type Badge Colors

```
💻 Chromebooks → Green tint (rgba(76, 175, 80, 0.2) bg)
📱 iPad        → Orange tint (rgba(255, 152, 0, 0.2) bg)
```

---

## Layout Grid

### Desktop (1400px+)
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Field 1 │ │ Field 2 │ │ Field 3 │ │ Field 4 │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Field 5 │ │ Field 6 │ │ Field 7 │ │ Field 8 │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Tablet (768px)
```
┌───────────────┐ ┌───────────────┐
│    Field 1    │ │    Field 2    │
└───────────────┘ └───────────────┘
┌───────────────┐ ┌───────────────┐
│    Field 3    │ │    Field 4    │
└───────────────┘ └───────────────┘
```

### Mobile (480px)
```
┌─────────────────────────────┐
│          Field 1            │
└─────────────────────────────┘
┌─────────────────────────────┐
│          Field 2            │
└─────────────────────────────┘
```

---

## Typography Scale

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Asset Tag | 1.6em | 700 | #e6edf3 |
| Serial Subtitle | 0.85em | 400 | #7d8590 |
| Type Badge | 0.9em | 600 | Varies |
| Status Badge | 0.85em | 600 | White |
| Field Label | 0.75em | 600 | #7d8590 |
| Field Value | 0.95em | 400 | #e6edf3 |
| Button Text | 0.85em | 500 | #e6edf3 |

---

## Spacing System

| Property | Value |
|----------|-------|
| Card Margin Bottom | 20px |
| Header Padding | 24px / 16px (top/bottom) |
| Content Padding | 20px / 24px (v/h) |
| Field Padding | 12px |
| Field Gap | 20px |
| Button Gap | 10px |
| Section Gap | 20px |

---

## Color Palette

### Primary Colors
```
Background Dark:    #0d1117
Card Background:    #161b22
Text Primary:       #e6edf3
Text Secondary:     #7d8590
Accent Blue:        #58a6ff
Border Color:       #30363d
```

### Status Colors
```
Success Green:      #4caf50 / #81c784
Error Red:          #f44336 / #ffcdd2
Warning Orange:     #ff9800 / #ffb74d
Info Blue:          #2196f3 / #58a6ff
```

### Opacity Overlays
```
Light 2%:   rgba(255, 255, 255, 0.02)
Light 4%:   rgba(255, 255, 255, 0.04)
Light 8%:   rgba(255, 255, 255, 0.08)
Blue 3%:    rgba(88, 166, 255, 0.03)
Blue 10%:   rgba(88, 166, 255, 0.1)
Green 10%:  rgba(76, 175, 80, 0.1)
Orange 10%: rgba(255, 152, 0, 0.1)
```

---

## Border Radius

| Element | Radius |
|---------|--------|
| Card | 12px |
| Badges | 20px (pill) |
| Buttons | 8px |
| Fields | 8px |
| User Chips | 16px |
| Type Badge | 20px |

---

## Shadows

```css
/* Card Default */
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);

/* Card Hover */
box-shadow: 0 8px 24px rgba(0, 163, 255, 0.15);

/* Badge */
box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);

/* Button */
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

/* Button Hover */
box-shadow: 0 4px 12px rgba(88, 166, 255, 0.2);
```

---

## Animation Specs

### Transition
```css
transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

### Hover Transforms
```css
/* Card */
transform: translateY(-4px);

/* Button */
transform: translateY(-2px);

/* User Chip */
transform: translateY(-1px);
```

### Status Indicator Pulse
```css
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
animation: pulse 2s ease-in-out infinite;
```

---

## Icon Reference

| Field | Icon | Field | Icon |
|-------|------|-------|------|
| Asset Tag | 🏷️ | Serial Number | 🔢 |
| User | 👤 | Model | 💻 |
| Location | 📍 | MAC Address | 🌐 |
| IP Address | 🌍 | OS Version | 💿 |
| Last Sync | 🔄 | Org Unit | 📁 |
| Access Point | 📡 | Last Seen | 🕐 |
| Recent Users | 📋 | Device Type (Chrome) | 💻 |
| Device Type (iPad) | 📱 | Quick Actions | ⚡ |

---

## Component States

### Device Card
```
Normal:   Default styling
Hover:    Lifts up, blue glow, border highlights
Active:   N/A (cards not clickable)
```

### Buttons
```
Normal:   Blue gradient background
Hover:    Lifts up, brighter, blue glow
Active:   Returns to position
Success:  Green gradient for 2 seconds
Disabled: 40% opacity, no interaction
```

### Fields
```
Normal:   Light background, transparent border
Hover:    Brighter background, visible border
```

### Links
```
Normal:   Blue color (#58a6ff)
Hover:    Underline, lighter blue (#79c0ff)
```

---

## Accessibility

### Color Contrast Ratios
```
Primary Text:     7.5:1 (AAA)
Secondary Text:   4.8:1 (AA)
Links:            4.5:1 (AA)
Badges:           7:1 (AAA)
```

### Interactive Elements
```
Minimum Touch Target:  44px × 44px (mobile)
Focus Indicators:      Visible outline
Hover States:          All clickable elements
Title Attributes:      All links and buttons
```

---

## Conditional Display Logic

### Chromebook-Only Fields
- Last Sync
- Last Known User
- Org Unit Path

### Always Shown Fields
- Serial Number
- Assigned User
- Model
- Location
- MAC Address
- IP Address
- OS Version

### Conditional Fields
- Recent Users (if data exists)
- Meraki AP Name (if data exists)
- Meraki Last Seen (if data exists)
- IIQ Status Badge (if status exists)

---

## Quick Actions

### Default Actions (All Devices)
1. 📋 Copy Serial Number
2. 🌐 Copy MAC Address
3. 🏷️ Copy Asset Tag
4. 📊 Open IncidentIQ (if assetId exists)

### Chromebook-Only Actions
5. ⚙️ Open Google Admin (if deviceId exists)

---

## CSS Variable Override Examples

### Change Accent Color
```css
:root {
    --accent-color: #ff6b6b; /* Red accent */
}
```

### Change Card Background
```css
:root {
    --bg-card: #1e1e1e; /* Darker cards */
}
```

### Change Success Color
```css
:root {
    --success-color: #00c853; /* Brighter green */
}
```

---

## Common Customizations

### Make Cards More Compact
```css
.device-header {
    padding: 16px 20px 12px 20px;
}

.device-content {
    padding: 16px 20px;
}

.device-grid {
    gap: 16px;
}
```

### Increase Card Hover Effect
```css
.device-card:hover {
    transform: translateY(-6px);
    box-shadow: 0 12px 32px rgba(0, 163, 255, 0.25);
}
```

### Change Border Accent
```css
.device-card::before {
    width: 6px; /* Thicker border */
}
```

---

## Debugging Tips

### Check Card Type Class
```javascript
// In browser console
document.querySelector('.device-card').classList;
// Should show: device-card, type-chromebook, status-active
```

### Verify Transitions
```javascript
// Check if transitions are applied
getComputedStyle(document.querySelector('.device-card')).transition;
```

### Test Hover States
```css
/* Add to CSS temporarily to see hover state */
.device-card {
    transform: translateY(-4px) !important;
    box-shadow: 0 8px 24px rgba(0, 163, 255, 0.15) !important;
}
```

### Check Grid Layout
```javascript
// View grid configuration
getComputedStyle(document.querySelector('.device-grid')).gridTemplateColumns;
```

---

## Browser DevTools Tips

### View Animation Performance
1. Open DevTools → Performance
2. Record interaction
3. Check for layout thrashing
4. Verify 60fps during animations

### Inspect Grid Layout
1. Open DevTools → Elements
2. Select `.device-grid`
3. Grid overlay shows columns/gaps

### Test Responsive Breakpoints
1. DevTools → Toggle Device Toolbar
2. Test at: 1400px, 768px, 480px
3. Verify layout changes correctly

---

## Common Issues & Fixes

### Cards Not Hovering
```css
/* Ensure transition is set */
.device-card {
    transition: var(--transition-smooth);
}
```

### Status Indicator Not Pulsing
```css
/* Check animation is applied */
.device-badge .status-indicator {
    animation: pulse 2s ease-in-out infinite;
}
```

### Grid Not Responsive
```css
/* Verify auto-fit is set */
.device-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}
```

### Buttons Not Full Width on Mobile
```css
/* Add media query */
@media (max-width: 480px) {
    .quick-action-btn {
        width: 100%;
    }
}
```
