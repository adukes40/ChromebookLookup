# Design Preview Testing Guide

## 🎨 What's Been Done

### 1. Sync Limit Increased ✅
- Changed from 50,000 → 100,000 assets in IIQ sync
- File: `/opt/chromebook-dashboard/services/sync_service_simple.py:49`

### 2. Preview Page Created ✅
- **URL**: `http://your-dashboard-url/preview`
- Shows NEW card design without affecting production
- Orange banner at top with link back to production dashboard

### 3. Design Improvements Created ✅

**Files:**
- `/opt/chromebook-dashboard/static/css/preview.css` (20KB) - Enhanced styles
- `/opt/chromebook-dashboard/static/js/preview.js` (26KB) - Improved card generation
- `/opt/chromebook-dashboard/templates/preview.html` (6.5KB) - Preview page template

**New Features:**
- ✨ Color-coded left borders (Green = Chromebook, Orange = iPad, Red = Disabled)
- ✨ Animated pulsing status indicators
- ✨ Larger, more prominent asset tags (60% bigger)
- ✨ Enhanced field cards with hover effects
- ✨ Source badges showing "IIQ Official" vs "Google"
- ✨ Better visual hierarchy and spacing
- ✨ Improved Quick Actions panel with blue tint
- ✨ Mobile-responsive design
- ✨ Professional gradients and shadows throughout

---

## 🧪 How to Test the Preview

### Step 1: Access Preview Page
Navigate to: **`http://your-dashboard-url/preview`**

You'll see an orange banner at the top indicating you're in preview mode.

### Step 2: Search for a Device
1. Enter a serial number, asset tag, or user email
2. Click "Search"
3. View the NEW card design

### Step 3: Compare with Production
Click "← Back to Production Dashboard" in the orange banner to compare.

### Step 4: Test Different Device Types
Try searching for:
- Chromebooks (should have green left border)
- iPads (should have orange left border)
- Disabled devices (should have red border)
- Devices with IIQ owner (should show "IIQ Official" badge)
- Devices with Google owner (should show "Google" badge)

---

## 📊 What to Look For

### Card Header
- [ ] Asset tag is large and prominent
- [ ] Serial number appears as subtitle below asset tag
- [ ] Device type badge shows correct icon and type
- [ ] Status badges show with animated pulsing indicator
- [ ] IIQ status badge appears (if available)

### Card Content
- [ ] Fields are in individual cards with light backgrounds
- [ ] Hover effect on fields (background changes on hover)
- [ ] Icons appear before each field label
- [ ] Source badges show for user field (IIQ Official or Google)
- [ ] Secondary info displays (like full name under email)

### Quick Actions Panel
- [ ] Blue-tinted background on panel
- [ ] Gradient buttons with hover effects
- [ ] Copy buttons show success animation
- [ ] Google Admin button only for Chromebooks
- [ ] IncidentIQ button for all devices

### Mobile (Test on Phone/Tablet)
- [ ] Cards stack properly on small screens
- [ ] Buttons are full-width and touch-friendly
- [ ] Header info reorganizes for mobile
- [ ] All text remains readable

---

## ✅ If You Like It - Apply to Production

### Option 1: Manual Backup & Replace
```bash
# Backup originals
cp /opt/chromebook-dashboard/static/css/main.css /opt/chromebook-dashboard/static/css/main.css.backup
cp /opt/chromebook-dashboard/static/js/dashboard.js /opt/chromebook-dashboard/static/js/dashboard.js.backup

# Apply preview design
cp /opt/chromebook-dashboard/static/css/preview.css /opt/chromebook-dashboard/static/css/main.css
cp /opt/chromebook-dashboard/static/js/preview.js /opt/chromebook-dashboard/static/js/dashboard.js

# Restart service
systemctl restart chromebook-dashboard
```

### Option 2: Ask Claude to Apply It
Just say: "Apply the preview design to production"

---

## ❌ If You Don't Like It - Request Changes

Tell Claude what you'd like changed, examples:
- "Make the asset tags even bigger"
- "Change the color scheme"
- "Remove the animations"
- "Adjust the spacing"
- "Different field layout"

Claude can iterate on the design in the preview before applying to production.

---

## 🔄 Rollback (If Needed)

If you apply to production and want to go back:

```bash
# Restore originals
cp /opt/chromebook-dashboard/static/css/main.css.backup /opt/chromebook-dashboard/static/css/main.css
cp /opt/chromebook-dashboard/static/js/dashboard.js.backup /opt/chromebook-dashboard/static/js/dashboard.js

# Restart service
systemctl restart chromebook-dashboard
```

---

## 📚 Additional Documentation

Detailed design documentation is available in:
- `DESIGN_README.md` - Complete overview
- `DESIGN_VISUAL_GUIDE.md` - ASCII mockups and examples
- `DESIGN_QUICK_REFERENCE.md` - Color codes and measurements
- `DESIGN_BEFORE_AFTER.md` - Detailed comparison
- `DESIGN_IMPLEMENTATION_EXAMPLES.md` - Code examples

---

## 🎯 Summary

**Preview URL**: `/preview`

**What Changed**:
1. Sync limit increased to 100,000 assets
2. New card design with better visual hierarchy
3. Color-coded borders by device type
4. Animated status indicators
5. Source badges (IIQ vs Google)
6. Enhanced hover states and animations
7. Mobile-optimized layout

**Status**: ✅ Ready to test

Search for a device on the preview page to see the new design!
