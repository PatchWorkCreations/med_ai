# NeuroMed AI Dashboard - Complete Function List

## Overview
The dashboard is the main authenticated interface where users can chat with the AI, manage their medical summaries, and access various features.

---

## Core Chat Functions

### 1. **Chat Messaging**
- **`sendChat()`** - Sends user messages and file attachments to the AI
- **`appendChatBubble(role, textOrNode, isHistory)`** - Displays chat messages in the UI
- **`appendRichBubble(content, isUser, isHistory)`** - Renders rich markdown content in chat bubbles
- **`appendBubble(message, isUser)`** - Simple wrapper for appending chat bubbles
- **Typing indicator** - Shows "NeuroMed is typing..." animation while AI processes

### 2. **File Management**
- **`addFiles(files)`** - Adds files to the pending attachments tray
- **`removePending(index)`** - Removes a file from pending attachments
- **`clearPending()`** - Clears all pending attachments
- **`renderPending()`** - Renders the pending attachments grid
- **File input** - Supports multiple file selection (up to 15 files)
- **Drag & drop** - Users can drag files into the composer area
- **Supported formats**: PDF, DOCX, TXT, JPG, JPEG, PNG, WEBP, HEIC

---

## Session Management

### 3. **Chat Sessions**
- **`refreshSessionList()`** - Loads and displays all chat sessions in sidebar
- **`openSession(id)`** - Opens a specific chat session and loads its messages
- **`newChat()`** - Creates a new chat session and clears the current chat
- **`startInlineRename(li, id)`** - Allows inline renaming of session titles
- **Session persistence** - Sessions are saved to database and persist across logins
- **Active session highlighting** - Current session is highlighted in sidebar

### 4. **Session Actions** (API endpoints)
- **Rename session** - `/api/chat/sessions/<id>/rename/` - Updates session title
- **Archive session** - `/api/chat/sessions/<id>/archive/` - Toggles archive status
- **Delete session** - `/api/chat/sessions/<id>/delete/` - Permanently deletes session
- **List sessions** - `/api/chat/sessions/` - Gets all user's chat sessions
- **Get session** - `/api/chat/sessions/<id>/` - Gets specific session details
- **Create session** - `/api/chat/sessions/new/` - Creates a new session

---

## Tone & Settings

### 5. **Tone Selection**
- **Available tones:**
  - Balanced (PlainClinical)
  - Caregiver
  - Faith
  - Clinical
  - Geriatric
  - Emotional Support
- **`currentTone()`** - Gets the currently selected tone
- **`updateBubbleChips()`** - Updates visual chips showing active tone/settings
- **Tone persistence** - Selected tone is saved and applied to all messages

### 6. **Care Setting**
- **Available settings:**
  - Hospital
  - Ambulatory
  - Urgent
- **`loadCareSetting()`** - Loads care setting from localStorage
- **`saveCareSetting(v)`** - Saves care setting to localStorage
- **`bindCareSettingUI()`** - Binds UI controls to care setting functions
- **Conditional display** - Only shows for Caregiver and Clinical tones

### 7. **Faith Setting**
- **Available traditions:**
  - General
  - Christian
  - Muslim
  - Hindu
  - Buddhist
  - Jewish
- **`loadFaithSetting()`** - Loads faith setting from localStorage
- **`saveFaithSetting(v)`** - Saves faith setting to localStorage
- **`bindFaithSettingUI()`** - Binds UI controls to faith setting functions
- **Conditional display** - Only shows when Faith tone is selected

---

## Language & Localization

### 8. **Language Selection**
- **`loadLang()`** - Gets current language from localStorage or browser
- **`saveLang(code)`** - Saves selected language
- **`labelForLang(code)`** - Gets display label for language code
- **`applyLangUI(code)`** - Updates UI to reflect selected language
- **`pickLang(code)`** - Handles language selection
- **`buildDesktopMenu()`** - Builds desktop language dropdown
- **`buildMobileLangList()`** - Builds mobile language list
- **40+ languages supported** - Full internationalization support
- **Browser detection** - Auto-detects user's browser language

---

## User Interface

### 9. **Layout & Navigation**
- **`toggleSidebar()`** - Shows/hides sidebar on mobile
- **`updateComposerPadding()`** - Adjusts chat window padding for composer
- **`applyZoomFromTone()`** - Applies zoom level based on tone (Geriatric mode)
- **Responsive design** - Adapts to mobile, tablet, and desktop
- **Sidebar** - Fixed sidebar with session history (desktop) / slide-out (mobile)

### 10. **Modals & Overlays**
- **Settings Modal**
  - **`openSettingsModal()`** - Opens user settings modal
  - **`closeSettingsModal()`** - Closes settings modal
  - **`saveSettings()`** - Saves user profile settings (display name, profession)
- **Summary Modal** - Displays full summary in a modal popup
- **Loading Overlay** - Shows loading animation during processing
- **Feedback Modal** - Beta feedback submission form

### 11. **User Settings**
- **Profile management**
  - Display name editing
  - Profession field
  - Settings persistence via API
- **`logoutUser()`** - Handles user logout
- **Settings dropdown** - Quick access to profile/logout

---

## Voice Input

### 12. **Voice Dictation**
- **`startDictation()`** - Initiates voice input using Web Speech API
- **Microphone button** - Toggle voice input
- **Browser compatibility** - Works with Chrome, Edge, Safari
- **Real-time transcription** - Speech converted to text in chat input

---

## Markdown & Content Rendering

### 13. **Content Rendering**
- **`renderAssistantMarkdown(mdText)`** - Converts markdown to HTML for AI responses
- **`renderStreamingMarkdown(mdText, targetEl)`** - Renders streaming markdown content
- **Rich formatting support:**
  - Headers (H1-H4)
  - Lists (ordered/unordered)
  - Bold, italic, code blocks
  - Tables
  - Blockquotes
- **Compact styling** - Optimized for chat bubbles

---

## Utility Functions

### 14. **API Helpers**
- **`apiPost(url, data)`** - Makes POST requests with CSRF token
- **`apiJson(url, opt)`** - Makes JSON requests
- **`getCSRFToken()`** - Retrieves CSRF token from cookies
- **`getCookie(name)`** - Gets cookie value by name

### 15. **Session Storage**
- **`getSessionId()`** - Gets current session ID from localStorage
- **`setSessionId(id)`** - Saves session ID to localStorage
- **`clearSessionId()`** - Clears session ID from localStorage
- **Session key**: `nm_session_id`

### 16. **Date & Formatting**
- **`fmtDate(s)`** - Formats ISO date string to locale string
- **Date display** - Shows formatted dates in session list

---

## User Experience

### 17. **Greeting & Onboarding**
- **`greetUser()`** - Displays personalized greeting with user's name
- **Random greetings** - Multiple greeting variations
- **Welcome messages** - Context-aware welcome based on user state

### 18. **Feedback System**
- **`openFeedback()`** - Opens beta feedback modal
- **`closeFeedback()`** - Closes feedback modal
- **`showToast(msg)`** - Displays toast notifications
- **Feedback submission** - Collects user feedback via API

### 19. **Accessibility**
- **Geriatric mode** - 25% zoom for easier reading
- **Font size controls** - Adjustable text size
- **Keyboard navigation** - Full keyboard support
- **Screen reader support** - ARIA labels and semantic HTML

---

## Backend Integration

### 20. **API Endpoints Used**
- **`/api/send-chat/`** - Send chat messages with files
- **`/api/chat/sessions/`** - List all sessions
- **`/api/chat/sessions/<id>/`** - Get session details
- **`/api/chat/sessions/new/`** - Create new session
- **`/api/chat/sessions/<id>/rename/`** - Rename session
- **`/api/chat/sessions/<id>/archive/`** - Archive session
- **`/api/chat/sessions/<id>/delete/`** - Delete session
- **`/api/user/settings/`** - Get user settings
- **`/api/user/settings/update/`** - Update user settings
- **`/clear-session/`** - Clear session data
- **`/beta/api/submit/`** - Submit feedback

---

## Advanced Features

### 21. **Multi-Image Processing**
- **Up to 15 files** - Can attach multiple images/documents
- **Combined analysis** - Multiple images analyzed together for context
- **File preview** - Thumbnail previews in attachment tray
- **File type detection** - Automatically detects image vs document

### 22. **Real-time Updates**
- **Live typing indicator** - Shows when AI is processing
- **Streaming responses** - (If implemented) Real-time response streaming
- **Auto-scroll** - Chat window auto-scrolls to latest message
- **Session sync** - Real-time session updates

### 23. **Search & Filter**
- **Search summaries** - Search input in sidebar (UI ready)
- **Session filtering** - Filter by date, tone, etc. (if implemented)
- **Quick access** - Recent sessions at top of list

---

## Security & Authentication

### 24. **Authentication**
- **Login required** - Dashboard requires authentication
- **Session management** - Secure session handling
- **CSRF protection** - All POST requests include CSRF tokens
- **Logout** - Secure logout with session cleanup

---

## Performance Optimizations

### 25. **Optimizations**
- **Debounced resize** - Debounced window resize handler
- **Lazy loading** - Sessions loaded on demand
- **Efficient rendering** - Optimized DOM updates
- **Image optimization** - Compressed image previews
- **Caching** - localStorage for user preferences

---

## Mobile Features

### 26. **Mobile-Specific**
- **Burger menu** - Mobile sidebar toggle
- **Touch gestures** - Swipe support (if implemented)
- **Mobile language picker** - Full-screen mobile language selection
- **Responsive composer** - Adapts to mobile keyboard
- **Viewport handling** - Proper mobile viewport management

---

## Summary

The dashboard provides a comprehensive chat interface with:
- ✅ Full chat functionality with AI
- ✅ File upload and management (up to 15 files)
- ✅ Session management (create, rename, archive, delete)
- ✅ Multiple tone and setting options
- ✅ 40+ language support
- ✅ Voice input
- ✅ Rich markdown rendering
- ✅ User profile management
- ✅ Mobile-responsive design
- ✅ Accessibility features
- ✅ Real-time updates
- ✅ Secure authentication

Total: **26 major feature categories** with **100+ individual functions**
