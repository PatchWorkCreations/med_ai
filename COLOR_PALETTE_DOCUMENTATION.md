# NeuroMed Aira - Color Palette Documentation

**Last Updated:** Current  
**Version:** 1.0

---

## 📋 Table of Contents

1. [Brand Colors](#brand-colors)
2. [Accent Colors (User-Selectable)](#accent-colors-user-selectable)
3. [Tone Colors](#tone-colors)
4. [Background Colors](#background-colors)
5. [Text Colors](#text-colors)
6. [UI Element Colors](#ui-element-colors)
7. [Status & State Colors](#status--state-colors)
8. [CSS Variables Reference](#css-variables-reference)

---

## 🎨 Brand Colors

### Primary Brand Colors

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Primary Blue** | `#236092` | rgb(35, 96, 146) | Main brand color, buttons, headers, icons |
| **Primary Dark** | `#1B5A8E` | rgb(27, 90, 142) | Hover states, darker variants |
| **Accent Green** | `#28926D` | rgb(40, 146, 109) | Primary accent, highlights, borders |
| **Accent Light** | `#10b981` | rgb(16, 185, 129) | Light accent variant, hover states |

**CSS Variables:**
- `--nm-primary: #236092`
- `--nm-primary-dark: #1B5A8E`
- `--nm-accent: #28926D`
- `--nm-accent-light: #10b981`

**Usage Examples:**
- Primary buttons: `bg-[#236092]`
- Hover states: `hover:bg-[#1B5A8E]`
- Accent borders: `border-[#28926D]`
- Focus rings: `focus:ring-[#28926D]/40`

---

## 🎨 Accent Colors (User-Selectable)

Users can select from these accent colors in Settings > General > Accent color:

| Color Name | Hex Code | RGB | Light Variant | Usage |
|------------|----------|-----|---------------|-------|
| **Default/Green** | `#28926D` | rgb(40, 146, 109) | `#10b981` | Default accent color |
| **Blue** | `#236092` | rgb(35, 96, 146) | `#3B82F6` | Alternative accent |
| **Purple** | `#7C3AED` | rgb(124, 58, 237) | `#A78BFA` | Alternative accent |
| **Red** | `#DC2626` | rgb(220, 38, 38) | `#EF4444` | Alternative accent |

**Note:** When a user selects an accent color, it updates the CSS variable `--nm-accent` throughout the application.

---

## 🎨 Tone Colors

These colors are used for the chat tone selector options:

| Tone | Icon Color | Hex Code | RGB | Description |
|------|------------|----------|-----|-------------|
| **Balanced** | Blue | `#236092` | rgb(35, 96, 146) | Clear explanations with clinical notes |
| **Caregiver** | Amber | `#F59E0B` | rgb(245, 158, 11) | Gentle, practical guidance |
| **Faith** | Indigo | `#4F46E5` | rgb(79, 70, 229) | Spiritual support and encouragement |
| **Clinical** | Slate | `#475569` | rgb(71, 85, 105) | Structured, medical-first approach |
| **Geriatric** | Green | `#28926D` | rgb(40, 146, 109) | Simple, clear steps for older adults |
| **Emotional Support** | Rose | `#E11D48` | rgb(225, 29, 72) | Calm, validating support |

**Tone Chip Background Colors (from documentation):**
- **Balanced**: `#e2e8f0` (background), `#334155` (text)
- **Caregiver**: `#ffe4e6` (background), `#9f1239` (text)
- **Faith**: `#e0e7ff` (background), `#3730a3` (text)
- **Clinical**: `#fef9c3` (background), `#92400e` (text)
- **Geriatric**: `#dcfce7` (background), `#065f46` (text)
- **Emotional Support**: `#ede9fe` (background), `#6d28d9` (text)

---

## 🎨 Background Colors

### Base Backgrounds

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Body Background** | `#f8fafc` → `#f1f5f9` | Gradient | Main page background gradient |
| **Paper/White** | `#ffffff` | rgb(255, 255, 255) | Cards, modals, chat bubbles |
| **Glass Surface** | `rgba(255, 255, 255, 0.85)` | - | Glass morphism effects |
| **Frost Surface** | `rgba(255, 255, 255, 0.95)` | - | Stronger glass effects |

**CSS Variables:**
- `--nm-paper: #ffffff`
- `--nm-glass: rgba(255, 255, 255, 0.85)`
- `--nm-frost: rgba(255, 255, 255, 0.95)`

### Chat Bubble Backgrounds

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| **User Message** | Light Blue Gradient | `#dbeafe` → `#bfdbfe` | User chat bubbles |
| **AI Message** | White | `#ffffff` | AI chat bubbles |
| **Code Block** | Dark | `#0f172a` | Code syntax highlighting background |

---

## 🎨 Text Colors

### Text Hierarchy

| Color Name | Hex Code | RGB | Usage |
|------------|----------|-----|-------|
| **Primary Text** | `#0f172a` | rgb(15, 23, 42) | Main body text, headings |
| **Secondary Text** | `#475569` | rgb(71, 85, 105) | Secondary information |
| **Muted Text** | `#94a3b8` | rgb(148, 163, 184) | Placeholders, hints |

**CSS Variables:**
- `--nm-text-primary: #0f172a`
- `--nm-text-secondary: #475569`
- `--nm-text-muted: #94a3b8`

### Tailwind Gray Scale Usage

| Class | Hex Code | Usage |
|-------|----------|-------|
| `text-gray-800` | `#1f2937` | Primary headings |
| `text-gray-700` | `#374151` | Secondary text |
| `text-gray-600` | `#4b5563` | Tertiary text |
| `text-gray-500` | `#6b7280` | Muted text |
| `text-gray-400` | `#9ca3af` | Disabled text |

---

## 🎨 UI Element Colors

### Borders

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| **Default Border** | Light Gray | `rgba(229, 231, 235, 0.8)` | Standard borders |
| **Glass Border** | Light Gray | `rgba(229, 231, 235, 0.8)` | Glass surface borders |
| **Focus Border** | Accent Color | `var(--nm-accent)` | Input focus states |
| **Table Border** | Light Gray | `#e2e8f0` | Table cell borders |

**CSS Variables:**
- `--nm-border: 1px solid rgba(229, 231, 235, 0.8)`
- `--nm-border-focus: 2px solid var(--nm-accent)`

### Shadows

All shadows use black with varying opacity:

| Shadow Level | Opacity | Usage |
|--------------|---------|-------|
| **Small** | `rgba(0, 0, 0, 0.05)` | Subtle elevation |
| **Default** | `rgba(0, 0, 0, 0.1)` | Standard cards |
| **Large** | `rgba(0, 0, 0, 0.1)` | Prominent elements |
| **Extra Large** | `rgba(0, 0, 0, 0.1)` | Modals, overlays |

**CSS Variables:**
- `--nm-shadow-sm`
- `--nm-shadow`
- `--nm-shadow-lg`
- `--nm-shadow-xl`

---

## 🎨 Status & State Colors

### Interactive States

| State | Color | Hex Code | Usage |
|-------|-------|----------|-------|
| **Hover (Primary)** | Dark Blue | `#1B5A8E` | Button hover states |
| **Active/Selected** | Accent Green | `#28926D` | Selected items, active states |
| **Focus Ring** | Accent (40% opacity) | `rgba(40, 146, 109, 0.4)` | Input focus rings |

### Special UI Colors

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| **Selected Tone Background** | Teal Green | `#28926D` | Selected tone option |
| **Softer Green Variant** | `#2d9f7a` | rgb(45, 159, 122) | Alternative green (popover) |
| **User Avatar Background** | Primary Blue | `#236092` | User icon background |

---

## 🎨 CSS Variables Reference

### Complete CSS Variable List

```css
:root {
  /* Brand tokens */
  --nm-primary: #236092;
  --nm-primary-dark: #1B5A8E;
  --nm-accent: #28926D;
  --nm-accent-light: #10b981;
  
  /* Paper & glass surfaces */
  --nm-paper: #ffffff;
  --nm-glass: rgba(255, 255, 255, 0.85);
  --nm-glass-border: rgba(229, 231, 235, 0.8);
  --nm-frost: rgba(255, 255, 255, 0.95);
  
  /* Text hierarchy */
  --nm-text-primary: #0f172a;
  --nm-text-secondary: #475569;
  --nm-text-muted: #94a3b8;
  
  /* Depth & shadows */
  --nm-shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --nm-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --nm-shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --nm-shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  
  /* Borders */
  --nm-border: 1px solid rgba(229, 231, 235, 0.8);
  --nm-border-focus: 2px solid var(--nm-accent);
  
  /* Spacing */
  --nm-radius: 12px;
  --nm-radius-lg: 16px;
  --nm-radius-xl: 20px;
}
```

---

## 🎨 Color Usage Guidelines

### When to Use Each Color

1. **Primary Blue (`#236092`)**
   - Primary action buttons
   - Main navigation elements
   - Brand logos and icons
   - Headers and titles

2. **Accent Green (`#28926D`)**
   - Success states
   - Positive indicators
   - Selected states
   - Focus rings
   - Borders and highlights

3. **Tone Colors**
   - Only for tone selector icons
   - Tone chip backgrounds
   - Tone-specific UI elements

4. **Gray Scale**
   - Text hierarchy (darker = more important)
   - Borders and dividers
   - Backgrounds for subtle elements

### Color Accessibility

- **Contrast Ratios:** All text colors meet WCAG AA standards (4.5:1 minimum)
- **Focus States:** All interactive elements have visible focus indicators
- **Color Blindness:** Information is not conveyed by color alone

---

## 🎨 Dark Mode Colors

**Note:** Dark mode implementation is in progress. When enabled, the following color adjustments apply:

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| **Background** | `#f8fafc` | `#0f172a` → `#1e293b` |
| **Paper/Cards** | `#ffffff` | `#1e293b` |
| **Text Primary** | `#0f172a` | `#f1f5f9` |
| **Text Secondary** | `#475569` | `#cbd5e1` |
| **Borders** | `rgba(229, 231, 235, 0.8)` | `rgba(51, 65, 85, 0.8)` |

---

## 📝 Notes

- All colors are defined in CSS variables for easy theming
- Accent colors can be changed by users in Settings
- Brand colors (Primary Blue) should remain consistent
- Tone colors are specific to chat tone functionality
- All colors support both light and dark modes (dark mode in progress)

---

**Document Maintained By:** Development Team  
**For Questions:** Refer to `new_dashboard.html` CSS variables section

