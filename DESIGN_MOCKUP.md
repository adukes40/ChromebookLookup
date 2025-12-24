# Device Card Design Mockup

## Overview
The redesigned device cards feature a modern, professional appearance with improved visual hierarchy, better use of color and spacing, and enhanced interactive elements.

## Card Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ ║  [Gradient background #161b22 → #0d1117]                      │
│ ║  ┌──────────────────────────────────────────────────────────┐ │
│ ║  │ HEADER SECTION (Light background with border)            │ │
│ ║  │                                                           │ │
│ ║  │ 🏷️ ASSET-12345                      ● ACTIVE    ✓       │ │
│ ║  │    Serial: 5CD1234ABC                (pulsing)           │ │
│ ║  │    💻 Chromebooks                    IIQ: Active         │ │
│ ║  │                                                           │ │
│ ║  └──────────────────────────────────────────────────────────┘ │
│ ║                                                                │
│ ║  [CONTENT SECTION - Padded area]                              │
│ ║                                                                │
│ ║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│ ║  │🔢 SERIAL NUM │  │👤 USER       │  │💻 MODEL      │        │
│ ║  │5CD1234ABC    │  │john@school   │  │HP Chromebook│        │
│ ║  │              │  │(IIQ Official)│  │14 G6        │        │
│ ║  └──────────────┘  └──────────────┘  └──────────────┘        │
│ ║                                                                │
│ ║  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│ ║  │📍 LOCATION   │  │🌐 MAC        │  │🌍 IP         │        │
│ ║  │Building A    │  │AA:BB:CC:...  │  │10.1.2.3     │        │
│ ║  └──────────────┘  └──────────────┘  └──────────────┘        │
│ ║                                                                │
│ ║  ────────────────────────────────────────────────────────     │
│ ║  📋 RECENT USERS                                              │
│ ║  [user1@school] [user2@school] [user3@school]                │
│ ║                                                                │
│ ║  ⚡ QUICK ACTIONS                                             │
│ ║  [📋 Copy Serial] [🌐 Copy MAC] [🏷️ Copy Tag] [⚙️ Google]   │
│ ║                                                                │
└─────────────────────────────────────────────────────────────────┘
  ▲
  Color-coded left border:
  - Green gradient: Chromebook + Active
  - Orange gradient: iPad
  - Red gradient: Disabled
```

## Visual Design Elements

### 1. Color-Coded Left Border (4px)
- **Chromebook + Active**: Green gradient (#4caf50 → #2e7d32)
- **iPad**: Orange gradient (#ff9800 → #e65100)
- **Disabled**: Red gradient (#f44336 → #c62828)
- **Default**: Blue accent (#58a6ff)

### 2. Card Header
**Background**: rgba(255, 255, 255, 0.02) - Subtle light overlay
**Border Bottom**: 1px solid #30363d
**Padding**: 24px top, 16px bottom

#### Left Side - Primary Info
- **Asset Tag**:
  - Font: 1.6em, bold (700 weight)
  - Color: #e6edf3 (bright white)
  - Clickable link to IIQ with icon
  - Hover: Changes to accent blue

- **Subtitle**:
  - Font: 0.85em
  - Color: #7d8590 (muted gray)
  - "Serial: 5CD1234ABC"

- **Device Type Badge**:
  - **Chromebook**: Green gradient background with soft border
    - Background: rgba(76, 175, 80, 0.2)
    - Border: rgba(76, 175, 80, 0.4)
    - Text: #81c784 (light green)
  - **iPad**: Orange gradient background
    - Background: rgba(255, 152, 0, 0.2)
    - Border: rgba(255, 152, 0, 0.4)
    - Text: #ffb74d (light orange)

#### Right Side - Status Badges
- **Status Badge**:
  - Gradient background with shadow
  - **Active**: Green gradient (#4caf50 → #388e3c)
  - **Disabled**: Red gradient (#f44336 → #d32f2f)
  - Includes pulsing status indicator dot
  - Text: Uppercase, 0.85em, letter-spacing

- **IIQ Status Badge** (if present):
  - Blue gradient (#2196f3 → #1976d2)
  - Smaller font (0.75em)

### 3. Content Section
**Padding**: 20px 24px

#### Device Fields (Grid Layout)
- **Grid**: Auto-fit, minimum 280px per column, 20px gap
- **Field Container**:
  - Light background: rgba(255, 255, 255, 0.02)
  - Border: 1px solid transparent
  - Border-radius: 8px
  - Padding: 12px
  - **Hover**: Background brightens, border appears

- **Field Label**:
  - Icon + Text
  - Font: 0.75em, uppercase, bold
  - Color: #7d8590 (muted)
  - Letter-spacing: 0.8px

- **Field Value**:
  - Font: 0.95em, monospace
  - Color: #e6edf3 (bright)
  - Links: #58a6ff with underline on hover

- **Source Badges** (IIQ/Google):
  - Inline badges next to field labels
  - **IIQ**: Green tinted
  - **Google**: Orange tinted
  - Font: 0.75em with rounded corners

### 4. Recent Users Section
**Border Top**: 1px solid #30363d
**Padding Top**: 20px
**Margin Top**: 20px

- **Section Header**:
  - Icon + Text
  - Font: 0.75em, uppercase
  - Color: #7d8590

- **User Chips**:
  - Blue gradient background
  - Border: rgba(88, 166, 255, 0.3)
  - Rounded corners (16px)
  - Font: 0.85em
  - **Hover**: Lifts up 1px, brightens

### 5. Quick Actions Panel
**Background**: rgba(88, 166, 255, 0.03) - Light blue tint
**Border Top**: 2px solid rgba(88, 166, 255, 0.2)
**Padding**: 20px
**Border Radius**: Rounded bottom corners

- **Action Buttons**:
  - Grid layout: Auto-fit, minimum 140px
  - Blue gradient background
  - Border: rgba(88, 166, 255, 0.3)
  - Shadow: 0 2px 4px rgba(0, 0, 0, 0.1)
  - **Hover**:
    - Lifts up 2px
    - Background brightens
    - Shadow increases
    - Border glows blue
  - **Success State** (after copy):
    - Green gradient
    - "Copied!" text for 2 seconds

## Interactive States

### Card Hover
- Transform: translateY(-4px) - Lifts up
- Shadow: 0 8px 24px rgba(0, 163, 255, 0.15) - Blue glow
- Border: Changes to accent color

### Field Hover
- Background: Brightens slightly
- Border: Becomes visible

### Button Hover
- Transform: translateY(-2px) - Subtle lift
- Shadow: Increases with blue glow
- Background: Brightens

## Color Palette

### Status Colors
- **Active Green**: #4caf50 / #81c784
- **Disabled Red**: #f44336 / #ffcdd2
- **Warning Orange**: #ff9800 / #ffb74d
- **Info Blue**: #2196f3 / #58a6ff

### Background Colors
- **Card Background**: #161b22 → #0d1117 gradient
- **Header Background**: rgba(255, 255, 255, 0.02)
- **Field Background**: rgba(255, 255, 255, 0.02)
- **Quick Actions**: rgba(88, 166, 255, 0.03)

### Text Colors
- **Primary**: #e6edf3 (bright white)
- **Secondary**: #7d8590 (muted gray)
- **Accent**: #58a6ff (blue)

### Border Colors
- **Default**: #30363d
- **Accent**: #58a6ff
- **Green**: rgba(76, 175, 80, 0.4)
- **Orange**: rgba(255, 152, 0, 0.4)

## Typography

### Font Stack
- **Primary**: -apple-system, sans-serif
- **Monospace**: 'SF Mono', 'Monaco', 'Consolas', monospace

### Font Sizes
- **Asset Tag**: 1.6em (25.6px on 16px base)
- **Serial Number**: 0.85em subtitle
- **Field Labels**: 0.75em uppercase
- **Field Values**: 0.95em
- **Badges**: 0.75-0.85em

### Font Weights
- **Asset Tag**: 700 (bold)
- **Field Labels**: 600 (semi-bold)
- **Badges**: 600 (semi-bold)
- **Field Values**: 400 (regular)

## Spacing System

### Padding
- **Card**: 0 (content sections handle padding)
- **Header**: 24px (top) / 24px (sides) / 16px (bottom)
- **Content**: 20px (top/bottom) / 24px (sides)
- **Fields**: 12px all around
- **Quick Actions**: 20px all around

### Margins
- **Card Bottom**: 20px
- **Field Gap**: 20px
- **Section Gap**: 20px

### Border Radius
- **Card**: 12px
- **Badges**: 20px (pill shape)
- **Buttons**: 8px
- **Fields**: 8px
- **User Chips**: 16px

## Animations

### Transitions
- **Duration**: 0.3s
- **Easing**: cubic-bezier(0.4, 0, 0.2, 1)

### Hover Effects
- Card: Y-axis translate + shadow
- Buttons: Y-axis translate + glow
- Fields: Background fade + border fade

### Status Indicator Pulse
- **Animation**: 2s ease-in-out infinite
- **Effect**: Opacity 1 → 0.5 → 1

## Mobile Responsiveness

### Tablet (max-width: 768px)
- Grid: 2 columns minimum (240px)
- Header: Stacks vertically
- Status badges: Horizontal row with wrap
- Quick Actions: 2 columns

### Mobile (max-width: 480px)
- Grid: 1 column
- Reduced padding (16px)
- Asset tag: Smaller (1.3em)
- Quick Actions: 1 column, full width
- All buttons: Full width, centered

## Accessibility Features

1. **High Contrast**: All text meets WCAG AA standards
2. **Focus States**: Visible outlines on interactive elements
3. **Hover Tooltips**: Title attributes on links and buttons
4. **Semantic HTML**: Proper heading hierarchy
5. **Color Independence**: Icons + text (not just color)

## Performance Optimizations

1. **Hardware Acceleration**: Transform and opacity animations
2. **Will-Change**: Applied to frequently animated properties
3. **Efficient Selectors**: Class-based, minimal nesting
4. **Minimal Repaints**: Transform instead of position changes
5. **CSS Grid**: Modern layout without JavaScript calculations
