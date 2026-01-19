# NeuroMed Aira - Landing Page & Dashboard Documentation

## Table of Contents
1. [Landing Page Overview](#landing-page-overview)
2. [Dashboard Overview](#dashboard-overview)
3. [Tone Selectors](#tone-selectors)
4. [Additional Features](#additional-features)
5. [User Interface Components](#user-interface-components)

---

## Landing Page Overview

The landing page (`landing_page.html`) serves as the main entry point for NeuroMed Aira, providing a clean, accessible interface for users to interact with the medical AI assistant.

### Key Features

#### Hero Section
- **Headline**: "Make medical papers easy."
- **Subheadline**: "Upload a note, lab, or script — get clear next steps."
- **Primary CTAs**:
  - "Upload a file" button
  - "Try a quick demo" button

#### Header Navigation
- **Brand Logo**: NeuroMed Aira logo with link to home
- **Desktop Controls**:
  - Font size controls (A− / A＋)
  - Easy Read toggle (hidden by default)
  - High Contrast toggle
  - Sign up / Log in links
  - Language selector (globe icon)
- **Mobile Menu**: Hamburger menu with all controls accessible

#### Language Selector
- **Supported Languages**: 50+ languages including:
  - English, Spanish, French, German, Italian, Portuguese
  - Japanese, Chinese (Simplified/Traditional), Korean
  - Arabic, Hindi, Tagalog, and many more
- **Storage**: Language preference saved in `localStorage` as `nm_lang`
- **Auto-detection**: Automatically detects browser language on first visit

---

## Dashboard Overview

The dashboard (`dashboard.html`) provides authenticated users with a comprehensive interface for managing medical document summaries and interactions.

### Key Features

#### Header
- **Organization Branding**: Customizable organization name and theme
- **User Profile**: Display name, profession, settings access
- **Language Selector**: Same multi-language support as landing page
- **Mobile Burger Menu**: Collapsible sidebar navigation

#### Tone Bar
Located prominently below the header, the tone bar provides quick access to:
- **Summary Tone** selector (6 options)
- **Care Setting** selector (conditional, shown for Caregiver/Clinical tones)
- **Faith Setting** selector (conditional, shown for Faith tone)

---

## Tone Selectors

### Summary Tone Options

The tone selector is available on both the landing page and dashboard, allowing users to customize how the AI presents medical information.

#### 1. **Balanced** (PlainClinical)
- **Icon**: Message icon (`fa-regular fa-message`)
- **Color**: Blue (`#236092`)
- **Description**: Clear + calm explanations
- **Use Case**: General-purpose, balanced medical explanations
- **Default**: Yes (on dashboard)

#### 2. **Caregiver**
- **Icon**: Hands holding child (`fa-solid fa-hands-holding-child`)
- **Color**: Amber (`text-amber-700`)
- **Description**: Gentle, practical steps
- **Use Case**: For family members caring for loved ones
- **Default**: Yes (on landing page)
- **Special Features**: 
  - Shows "Care Setting" selector when selected
  - Care settings: Hospital, Ambulatory, Urgent

#### 3. **Clinical**
- **Icon**: Stethoscope (`fa-solid fa-stethoscope`)
- **Color**: Slate (`text-slate-800`)
- **Description**: Concise & technical
- **Use Case**: For healthcare professionals
- **Special Features**:
  - Shows "Care Setting" selector when selected
  - SOAP format summaries
  - Evidence-based clarity

#### 4. **Faith**
- **Icon**: Praying hands (`fa-solid fa-hands-praying`)
- **Color**: Indigo (`text-indigo-700`)
- **Description**: Guidance with encouragement
- **Use Case**: For users seeking faith-based support
- **Special Features**:
  - Shows "Faith Setting" selector when selected
  - Faith traditions: General, Christian, Muslim, Hindu, Buddhist, Jewish

#### 5. **Geriatric**
- **Icon**: Person with cane (`fa-solid fa-person-cane`)
- **Color**: Green (`#28926D`)
- **Description**: Larger text, simpler steps
- **Use Case**: Tailored for older adults
- **Special Features**:
  - Automatically enables "Easy Read" mode
  - Simplified language and formatting

#### 6. **Emotional Support**
- **Icon**: Heart (`fa-solid fa-heart`)
- **Color**: Rose (`text-rose-700`)
- **Description**: Validating, calm & gentle
- **Use Case**: For users needing emotional support during medical situations

### Tone Selector Implementation

#### Landing Page
- **Desktop**: Horizontal grid of mode chips (auto-fit, min 160px width)
- **Mobile**: Bottom sheet picker with descriptions
- **Storage**: Saved in `localStorage` as `nm_mode`
- **Visual Feedback**: Selected tone shows ring highlight and active state

#### Dashboard
- **Location**: Fixed tone bar below header (`#toneBar`)
- **Format**: Radio button group with labels
- **Responsive**: Wraps on smaller screens
- **Visual Chips**: Tone chips appear in chat bubbles showing current tone

### Conditional Selectors

#### Care Setting Selector
- **Visibility**: Only shown when "Caregiver" or "Clinical" tone is selected
- **Options**:
  - **Hospital**: Inpatient care context
  - **Ambulatory**: Outpatient/clinic context
  - **Urgent**: Urgent care/emergency context
- **Storage**: Saved in `localStorage` as `nm_care_setting`
- **Default**: Hospital

#### Faith Setting Selector
- **Visibility**: Only shown when "Faith" tone is selected
- **Options**:
  - **General**: Non-specific faith-based guidance
  - **Christian**: Christian faith traditions
  - **Muslim**: Islamic faith traditions
  - **Hindu**: Hindu faith traditions
  - **Buddhist**: Buddhist faith traditions
  - **Jewish**: Jewish faith traditions
- **Storage**: Saved in `localStorage` as `nm_faith_setting`
- **Default**: General

---

## Additional Features

### Accessibility Features

#### Font Size Controls
- **A− Button**: Decreases font size (minimum 16px)
- **A＋ Button**: Increases font size (maximum 22px)
- **Storage**: Font size preference not persisted (session-only)
- **Location**: Header (desktop) and mobile menu

#### Easy Read Mode
- **Toggle**: "Easy" button (hidden by default, can be enabled)
- **Effect**: 
  - Increases font scale to 1.2x
  - Increases line height to 1.12x
  - Improves readability
- **Auto-enabled**: When "Geriatric" tone is selected

#### High Contrast Mode
- **Toggle**: "Contrast" button
- **Effect**:
  - Black text on white background
  - High contrast borders
  - Improved visibility for low vision users
- **Storage**: Toggle state not persisted

### File Upload

#### Supported Formats
- **Documents**: PDF, DOC, DOCX, TXT
- **Images**: JPG, JPEG, PNG, HEIC, WEBP

#### Upload Methods
1. **Click Upload**: Paperclip button opens file picker
2. **Drag & Drop**: Drop files onto dropzone area
3. **Paste**: Paste images from clipboard

#### Features
- **Single File**: Currently supports one file at a time (landing page)
- **Multiple Files**: Dashboard supports multiple file attachments
- **Visual Preview**: File chips show file type icons
- **Remove**: X button on file chips to remove before sending

### Chat Interface

#### Input Area
- **Text Input**: Multi-line textarea with auto-resize
- **Placeholder**: Context-aware placeholder text
- **Keyboard Shortcuts**:
  - `Enter`: Send message
  - `Shift+Enter`: New line
- **Voice Input**: Microphone button for speech-to-text (Chrome recommended)

#### Chat Window
- **User Messages**: Right-aligned, dark background
- **AI Messages**: Left-aligned, white background with markdown support
- **Tone Chips**: Visual indicators showing active tone in AI responses
- **Timestamps**: Each message shows time sent
- **Markdown Rendering**: Full markdown support with sanitization

#### Suggestions
- **Quick Start Prompts**: Pre-written questions users can click
- **Examples**:
  - "Simplify this ER discharge for my family"
  - "Explain these labs in plain English"
  - "Make a daily medication schedule"
  - "Questions to ask my doctor"
  - "Translate this for my lola (Taglish)"
- **Toggle**: "Show more" / "Show fewer" button

### Demo Mode

#### Quick Demo Button
- **Location**: Hero section on landing page
- **Samples**:
  - **ER Discharge Demo**: Sample emergency room discharge note
  - **Lab Results Demo**: Sample lab work explanation
- **Functionality**: Automatically sends sample data to demonstrate AI capabilities

---

## User Interface Components

### Visual Design

#### Color Scheme
- **Primary Brand**: `#236092` (Blue)
- **Secondary**: `#1B5A8E` (Darker blue)
- **Accent**: `#28926D` (Green)
- **Background**: `#f6f8fb` (Light gray)
- **Text**: `#111827` (Dark gray)

#### Typography
- **Font Family**: Inter (Google Fonts)
- **Base Font Size**: 18px (1.125rem scale)
- **Line Height**: 1.55 (with 1.08 scale factor)
- **Responsive**: Scales down on mobile devices

#### Tone Chip Colors
- **Balanced**: Gray (`#e2e8f0` background, `#334155` text)
- **Caregiver**: Pink (`#ffe4e6` background, `#9f1239` text)
- **Faith**: Blue (`#e0e7ff` background, `#3730a3` text)
- **Clinical**: Yellow (`#fef9c3` background, `#92400e` text)
- **Geriatric**: Green (`#dcfce7` background, `#065f46` text)
- **Emotional Support**: Purple (`#ede9fe` background, `#6d28d9` text)

### Responsive Design

#### Breakpoints
- **Mobile**: < 768px
  - Tone selector becomes bottom sheet
  - Simplified navigation
  - Compact chat interface
- **Tablet**: 768px - 1024px
  - Grid layouts adapt
  - Tone chips remain visible
- **Desktop**: > 1024px
  - Full feature set visible
  - Sidebar navigation (dashboard)

### Interactive Elements

#### Buttons
- **Primary**: Brand color background, white text
- **Secondary**: Border, transparent background
- **Icon Buttons**: Circular, icon-only
- **Hover States**: Brightness filter or background change
- **Disabled States**: Reduced opacity, pointer-events disabled

#### Modals & Overlays
- **Signup Gate**: Full-screen overlay for unauthenticated users
- **Settings Modal**: Centered modal for user preferences
- **Summary Modal**: Large modal for full summary view
- **Feedback Panel**: Slide-over panel from right side

#### Loading States
- **Typing Indicator**: Spinner with "Thinking..." text
- **Loading Overlay**: Full-screen overlay with animated brain icon
- **Shimmer Effect**: Subtle animation on content updates

### Tour & Onboarding

#### Spotlight Tour
- **Trigger**: "?" help button (bottom left)
- **Auto-run**: First-time visitors (once per browser)
- **Steps**:
  1. Welcome message
  2. Font size controls
  3. Tone selector
  4. File upload
  5. Suggestions
  6. Sign up prompt
  7. Chat input
  8. Send button
  9. Completion message
- **Navigation**: Next/Back buttons, Skip option, keyboard navigation

---

## Technical Implementation

### Storage & Persistence

#### LocalStorage Keys
- `nm_mode`: Current tone selection
- `nm_lang`: Language preference
- `nm_care_setting`: Care setting preference
- `nm_faith_setting`: Faith setting preference
- `nm_guest_turns`: Guest usage counter
- `nm_chat_tour_done_v2`: Tour completion flag
- `nm_auth_nudge_dismissed`: Auth prompt dismissal

### API Integration

#### Endpoints Used
- `/api/send-chat/`: Send chat message with tone and settings
- `/api/auth/status/`: Check authentication status
- `/api/export/pdf/latest`: Export latest summary as PDF
- `/api/share/latest`: Generate shareable link
- `/api/translate/latest`: Translate latest summary

#### Request Format
```javascript
FormData {
  message: string,
  tone: string,           // PlainClinical, Caregiver, etc.
  lang: string,           // en-US, es-ES, etc.
  care_setting: string,   // hospital, ambulatory, urgent
  faith_setting: string,  // general, christian, muslim, etc.
  files[]: File[]         // Uploaded files
}
```

### Browser Compatibility

#### Required Features
- **Modern Browser**: Chrome, Firefox, Safari, Edge (latest versions)
- **Speech Recognition**: Chrome recommended for voice input
- **File API**: For drag & drop and file uploads
- **LocalStorage**: For preference storage
- **Fetch API**: For API calls

---

## User Flows

### Landing Page Flow
1. User arrives at landing page
2. Optional: Adjust font size or contrast
3. Optional: Select language
4. Select tone (default: Caregiver)
5. Upload file OR type question OR click demo
6. Receive AI summary
7. Optional: Download PDF or share link
8. Prompted to sign up after 3 guest interactions

### Dashboard Flow
1. User logs in and sees dashboard
2. Tone bar shows current preferences
3. Select tone (default: Balanced)
4. If Caregiver/Clinical: Select care setting
5. If Faith: Select faith tradition
6. Upload files and/or type question
7. Receive formatted summary with tone chips
8. View full summary in modal
9. Export or share summary

---

## Best Practices

### Tone Selection Guidelines
- **Balanced**: Default choice for most users
- **Caregiver**: Family members helping loved ones
- **Clinical**: Healthcare professionals
- **Faith**: Users seeking spiritual support
- **Geriatric**: Older adults or those preferring simpler language
- **Emotional Support**: Users experiencing stress or anxiety

### Accessibility Recommendations
- Always test with screen readers
- Ensure keyboard navigation works
- Maintain sufficient color contrast
- Provide text alternatives for icons
- Support font size adjustments
- Offer high contrast mode

### Performance Considerations
- Lazy load language menu options
- Debounce font size changes
- Optimize image uploads
- Cache tone preferences
- Minimize localStorage writes

---

## Future Enhancements

### Planned Features
- Profile photo upload
- Additional tone options
- Custom tone creation
- Tone-specific templates
- Multi-language chat support
- Enhanced mobile experience
- Offline mode support

---

## Support & Feedback

For questions, issues, or feature requests related to the UI:
- Use the feedback panel (slide-over from right side)
- Contact support through the dashboard
- Check documentation for common questions

---

*Last Updated: 2024*
*Version: 1.0*

