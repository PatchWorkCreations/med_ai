# Settings Functions Documentation

This document provides a comprehensive overview of all settings functions in the web app, organized by section. Use this document to provide instructions for implementing or modifying each setting.

---

## Table of Contents

1. [General Settings](#1-general-settings)
2. [Notifications Settings](#2-notifications-settings)
3. [Personalization Settings](#3-personalization-settings)
4. [Apps Settings](#4-apps-settings)
5. [Schedules Settings](#5-schedules-settings)
6. [Data Controls Settings](#6-data-controls-settings)
7. [Security Settings](#7-security-settings)
8. [Parental Controls Settings](#8-parental-controls-settings)
9. [Account Settings](#9-account-settings)

---

## 1. General Settings

**Status:** ✅ Fully Implemented  
**Section ID:** `settingsSection-general`  
**Backend Field:** `user_settings` JSONField in Profile model

### 1.1 Appearance
- **Element ID:** `appearanceSelect`
- **Type:** Dropdown select
- **Options:** `system`, `light`, `dark`
- **Default:** `system`
- **Backend Field:** `user_settings["appearance"]`
- **Functionality:** Controls the theme/appearance of the web app
- **Instructions:**
  - When changed, immediately apply theme to `document.documentElement.setAttribute('data-theme', value)`
  - Save to `localStorage` as `nm_appearance` for immediate UI update
  - Save to backend via `/api/user/settings/update/` endpoint
  - Should persist across page reloads

### 1.2 Accent Color
- **Element IDs:** 
  - Radio button: `input[name="accentColor"]` (value="default")
  - Dropdown: `accentColorSelect`
- **Type:** Radio button + Dropdown select
- **Options:** 
  - Radio: `default`
  - Dropdown: `green`, `blue`, `purple`, `red`
- **Default:** `default`
- **Backend Field:** `user_settings["accent_color"]`
- **Functionality:** Controls the accent color used throughout the UI
- **Instructions:**
  - When "Default" radio is selected, save `"default"` as accent color
  - When a color is selected from dropdown, save that color (e.g., `"green"`, `"blue"`)
  - Apply color immediately via CSS variables: `--token-accent` and related color variables
  - Save to `localStorage` as `nm_accent_color` for immediate UI update
  - Save to backend via `/api/user/settings/update/` endpoint

### 1.3 Language
- **Element ID:** `languageSelect`
- **Type:** Dropdown select
- **Options:** `auto`, `en-US`, `es-ES`, `fr-FR`, `de-DE` (and more from LANGUAGE_CHOICES)
- **Default:** `auto`
- **Backend Field:** `Profile.language` (direct field, not in JSONField)
- **Functionality:** Sets the primary language for the UI and AI responses
- **Instructions:**
  - Update `Profile.language` field directly (not in JSONField)
  - This affects the language of AI responses and UI text
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 1.4 Spoken Language
- **Element ID:** `spokenLanguageSelect`
- **Type:** Dropdown select
- **Options:** `auto`, `en-US`, `es-ES`, `fr-FR`, `de-DE` (and more)
- **Default:** `auto`
- **Backend Field:** `user_settings["spoken_language"]`
- **Functionality:** Sets the language for voice/speech features
- **Instructions:**
  - Save to `user_settings["spoken_language"]` in backend
  - Used for voice synthesis and speech recognition
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 1.5 Voice
- **Element IDs:** 
  - Play button: `playVoiceBtn`
  - Dropdown: `voiceSelect`
- **Type:** Button + Dropdown select
- **Options:** `spruce`, `cove`, `ember`, `juniper`
- **Default:** `spruce`
- **Backend Field:** `user_settings["voice"]`
- **Functionality:** Selects the voice for text-to-speech
- **Instructions:**
  - Play button should preview the selected voice
  - Save selected voice to `user_settings["voice"]` in backend
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 1.6 Separate Voice Mode
- **Element ID:** `separateVoiceMode`
- **Type:** Toggle switch (checkbox styled as toggle)
- **Options:** `true` (checked), `false` (unchecked)
- **Default:** `false`
- **Backend Field:** `user_settings["separate_voice_mode"]`
- **Functionality:** Keeps ChatGPT Voice in a separate full screen without real-time transcripts
- **Instructions:**
  - Toggle should save boolean value to `user_settings["separate_voice_mode"]`
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 1.7 Show Additional Models
- **Element ID:** `showAdditionalModels`
- **Type:** Toggle switch (checkbox styled as toggle)
- **Options:** `true` (checked), `false` (unchecked)
- **Default:** `false`
- **Backend Field:** `user_settings["show_additional_models"]`
- **Functionality:** Shows additional AI models in the model selector
- **Instructions:**
  - Toggle should save boolean value to `user_settings["show_additional_models"]`
  - Should be saved to backend via `/api/user/settings/update/` endpoint

---

## 2. Notifications Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-notifications`  
**Backend Field:** TBD (should be added to `user_settings` JSONField)

### 2.1 Notification Preferences
- **Instructions:**
  - Design notification settings UI
  - Options should include:
    - Email notifications (on/off)
    - Push notifications (on/off)
    - Chat message notifications (on/off)
    - Summary completion notifications (on/off)
    - Weekly digest (on/off)
  - Save to `user_settings["notifications"]` object in backend
  - Structure: `{ "email": true, "push": false, "chat": true, "summary": true, "digest": false }`

### 2.2 Notification Frequency
- **Instructions:**
  - Allow users to set frequency for different notification types
  - Options: `immediate`, `hourly`, `daily`, `weekly`, `never`
  - Save to `user_settings["notification_frequency"]` object

---

## 3. Personalization Settings

**Status:** ✅ Fully Implemented  
**Section ID:** `settingsSection-personalization`  
**Backend Field:** `user_settings["personalization"]` (nested object in JSONField)

### 3.1 Base Style and Tone
- **Element ID:** `baseStyleToneSelector` (container with buttons)
- **Type:** Button grid (selectable cards)
- **Options:** 
  - `PlainClinical` (Balanced)
  - `Caregiver`
  - `Faith`
  - `Clinical`
  - `Geriatric`
  - `EmotionalSupport`
- **Default:** `PlainClinical`
- **Backend Field:** `user_settings["personalization"]["base_style_tone"]`
- **Functionality:** Sets the base style and tone for AI responses
- **Instructions:**
  - Selected tone should be visually highlighted (border, checkmark)
  - Save selected tone value to `user_settings["personalization"]["base_style_tone"]`
  - This tone is used when generating AI responses
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.2 Characteristics
- **Element IDs:**
  - Warm: `characteristicWarm`
  - Enthusiastic: `characteristicEnthusiastic`
  - Headers & Lists: `characteristicHeaders`
  - Emoji: `characteristicEmoji`
- **Type:** Dropdown selects
- **Options:** `default`, `more`, `less`
- **Default:** `default`
- **Backend Fields:**
  - `user_settings["personalization"]["characteristic_warm"]`
  - `user_settings["personalization"]["characteristic_enthusiastic"]`
  - `user_settings["personalization"]["characteristic_headers"]`
  - `user_settings["personalization"]["characteristic_emoji"]`
- **Functionality:** Fine-tunes AI response characteristics
- **Instructions:**
  - Each characteristic adjusts the AI's response style
  - Save each value to the corresponding backend field
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.3 Custom Instructions
- **Element ID:** `customInstructions`
- **Type:** Textarea (multi-line text input)
- **Default:** Empty
- **Backend Field:** `user_settings["personalization"]["custom_instructions"]`
- **Functionality:** Allows users to provide custom instructions for AI behavior
- **Instructions:**
  - Save text content to `user_settings["personalization"]["custom_instructions"]`
  - This text is used to customize AI responses
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.4 About You - Nickname
- **Element ID:** `personalizationNickname`
- **Type:** Text input
- **Default:** Empty
- **Backend Field:** `user_settings["personalization"]["nickname"]`
- **Functionality:** Sets a nickname for the AI to use when addressing the user
- **Instructions:**
  - Save text to `user_settings["personalization"]["nickname"]`
  - AI should use this when addressing the user
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.5 About You - Occupation
- **Element ID:** `personalizationOccupation`
- **Type:** Text input
- **Default:** Empty
- **Backend Field:** `user_settings["personalization"]["occupation"]` (also saved to `Profile.profession`)
- **Functionality:** Sets the user's occupation/profession
- **Instructions:**
  - Save to both `user_settings["personalization"]["occupation"]` and `Profile.profession`
  - Used to personalize AI responses
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.6 About You - More About You
- **Element ID:** `moreAboutYou`
- **Type:** Textarea (multi-line text input)
- **Default:** Empty
- **Backend Field:** `user_settings["personalization"]["more_about_you"]`
- **Functionality:** Allows users to provide additional context about themselves
- **Instructions:**
  - Save text content to `user_settings["personalization"]["more_about_you"]`
  - Used to personalize AI responses
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.7 Memory - Reference Saved Memories
- **Element ID:** `referenceSavedMemories`
- **Type:** Toggle switch (checkbox styled as toggle)
- **Options:** `true` (checked), `false` (unchecked)
- **Default:** `true`
- **Backend Field:** `user_settings["personalization"]["reference_saved_memories"]`
- **Functionality:** Enables/disables AI's ability to save and use memories
- **Instructions:**
  - Toggle should save boolean value to `user_settings["personalization"]["reference_saved_memories"]`
  - When enabled, AI can save and reference memories across conversations
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.8 Memory - Reference Chat History
- **Element ID:** `referenceChatHistory`
- **Type:** Toggle switch (checkbox styled as toggle)
- **Options:** `true` (checked), `false` (unchecked)
- **Default:** `true`
- **Backend Field:** `user_settings["personalization"]["reference_chat_history"]`
- **Functionality:** Enables/disables AI's ability to reference previous conversations
- **Instructions:**
  - Toggle should save boolean value to `user_settings["personalization"]["reference_chat_history"]`
  - When enabled, AI can reference all previous conversations when responding
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 3.9 Memory - Manage Button
- **Element ID:** `manageMemoryBtn`
- **Type:** Button
- **Functionality:** Opens a memory management interface
- **Instructions:**
  - Should open a modal or page to view/edit/delete saved memories
  - Implementation TBD

---

## 4. Apps Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-apps`  
**Backend Field:** TBD (should be added to `user_settings` JSONField)

### 4.1 Installed Apps
- **Instructions:**
  - Display list of installed/integrated apps
  - Allow users to enable/disable apps
  - Save to `user_settings["apps"]` object
  - Structure: `{ "app_name": { "enabled": true, "settings": {} } }`

### 4.2 App Permissions
- **Instructions:**
  - Manage permissions for each app
  - Options: `read`, `write`, `full_access`
  - Save to `user_settings["apps"][app_name]["permissions"]`

---

## 5. Schedules Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-schedules`  
**Backend Field:** TBD (should be added to `user_settings` JSONField or separate model)

### 5.1 Scheduled Summaries
- **Instructions:**
  - Allow users to schedule automatic medical summary generation
  - Options:
    - Frequency: `daily`, `weekly`, `monthly`
    - Time: Time picker
    - Documents: Select which documents to include
  - Save to `user_settings["schedules"]` array or separate `Schedule` model

### 5.2 Scheduled Reminders
- **Instructions:**
  - Allow users to set reminders for medication, appointments, etc.
  - Options:
    - Type: `medication`, `appointment`, `checkup`, `other`
    - Frequency: `once`, `daily`, `weekly`, `monthly`
    - Time: Time picker
  - Save to `user_settings["schedules"]["reminders"]` array

---

## 6. Data Controls Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-data`  
**Backend Field:** TBD (should be added to `user_settings` JSONField)

### 6.1 Data Export
- **Instructions:**
  - Provide button to export all user data
  - Export format: JSON or CSV
  - Include: Chat history, summaries, settings, profile data
  - Create endpoint: `/api/user/data/export/`

### 6.2 Data Deletion
- **Instructions:**
  - Provide options to delete specific data types:
    - Chat history
    - Medical summaries
    - Uploaded files
    - All data (account deletion)
  - Add confirmation dialogs for destructive actions
  - Create endpoints: `/api/user/data/delete/` or `/api/user/data/delete/<type>/`

### 6.3 Data Retention
- **Instructions:**
  - Allow users to set data retention policies
  - Options:
    - Keep forever
    - Delete after X days/months/years
    - Auto-delete after inactivity
  - Save to `user_settings["data_retention"]` object

### 6.4 Third-Party Data Sharing
- **Instructions:**
  - Toggle to enable/disable sharing data with third parties
  - List which third parties have access
  - Save to `user_settings["data_sharing"]` object

---

## 7. Security Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-security`  
**Backend Field:** TBD (should be added to `user_settings` JSONField)

### 7.1 Password Management
- **Instructions:**
  - Change password form
  - Current password, new password, confirm password
  - Create endpoint: `/api/user/change-password/`
  - Validate password strength

### 7.2 Two-Factor Authentication (2FA)
- **Instructions:**
  - Enable/disable 2FA toggle
  - QR code for authenticator app setup
  - Backup codes display
  - Save 2FA status to `user_settings["security"]["two_factor_enabled"]`

### 7.3 Active Sessions
- **Instructions:**
  - Display list of active sessions (devices, browsers, locations)
  - Allow users to revoke sessions
  - Create endpoint: `/api/user/sessions/` (GET, DELETE)

### 7.4 Login History
- **Instructions:**
  - Display recent login history
  - Show: Date, time, IP address, location, device
  - Create endpoint: `/api/user/login-history/`

### 7.5 API Keys
- **Instructions:**
  - Display list of API keys
  - Allow users to create, revoke, regenerate API keys
  - Create endpoints: `/api/user/api-keys/` (GET, POST, DELETE)

---

## 8. Parental Controls Settings

**Status:** ⚠️ Placeholder (Not Implemented)  
**Section ID:** `settingsSection-parental`  
**Backend Field:** TBD (should be added to `user_settings` JSONField or separate model)

### 8.1 Child Account Management
- **Instructions:**
  - List of child accounts linked to parent account
  - Add/remove child accounts
  - Set age restrictions
  - Save to `user_settings["parental"]["child_accounts"]` array

### 8.2 Content Filtering
- **Instructions:**
  - Enable/disable content filtering
  - Set filtering level: `strict`, `moderate`, `lenient`
  - Save to `user_settings["parental"]["content_filter"]`

### 8.3 Time Limits
- **Instructions:**
  - Set daily/weekly time limits for child accounts
  - Set allowed hours (e.g., 9 AM - 9 PM)
  - Save to `user_settings["parental"]["time_limits"]` object

### 8.4 Activity Monitoring
- **Instructions:**
  - Enable/disable activity monitoring
  - Display activity reports for child accounts
  - Save to `user_settings["parental"]["monitoring_enabled"]`

---

## 9. Account Settings

**Status:** ✅ Partially Implemented  
**Section ID:** `settingsSection-account`  
**Backend Fields:** `Profile.display_name`, `Profile.profession`, `User.first_name`, `User.last_name`, `User.email`

### 9.1 Display Name
- **Element ID:** `displayName`
- **Type:** Text input
- **Default:** User's full name or username
- **Backend Field:** `Profile.display_name`
- **Functionality:** Sets the user's display name shown throughout the app
- **Instructions:**
  - Save to `Profile.display_name` field
  - Update user's display name in UI immediately
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 9.2 Profession
- **Element ID:** `profession`
- **Type:** Text input
- **Default:** Empty or existing profession
- **Backend Field:** `Profile.profession`
- **Functionality:** Sets the user's profession/occupation
- **Instructions:**
  - Save to `Profile.profession` field
  - Also syncs with Personalization > About You > Occupation
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 9.3 First Name
- **Instructions:**
  - Add input field for first name
  - Save to `User.first_name` field
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 9.4 Last Name
- **Instructions:**
  - Add input field for last name
  - Save to `User.last_name` field
  - Should be saved to backend via `/api/user/settings/update/` endpoint

### 9.5 Email
- **Instructions:**
  - Display current email (read-only or editable)
  - If editable, require email verification
  - Save to `User.email` field
  - Create endpoint: `/api/user/change-email/` with verification

### 9.6 Logout
- **Element:** Button with `onclick="logoutUser()"`
- **Functionality:** Logs out the current user
- **Instructions:**
  - Clear session
  - Redirect to login page
  - Implement `logoutUser()` function if not already present

### 9.7 Delete Account
- **Instructions:**
  - Add "Delete Account" button (destructive action)
  - Require confirmation (password or confirmation dialog)
  - Delete all user data (GDPR compliance)
  - Create endpoint: `/api/user/delete-account/`

---

## Backend API Endpoints

### Current Endpoints

1. **GET `/api/user/settings/`**
   - Returns all user settings from `Profile.user_settings` JSONField
   - Returns: `{ "display_name", "first_name", "last_name", "full_name", "profession", "language", "appearance", "accent_color", "spoken_language", "voice", "separate_voice_mode", "show_additional_models", "personalization": { ... } }`

2. **POST `/api/user/settings/update/`**
   - Updates user settings
   - Accepts JSON body with any settings fields
   - Updates `Profile.user_settings` JSONField
   - Also updates `Profile.display_name`, `Profile.profession`, `Profile.language` directly

### Endpoints to Create

- `POST /api/user/change-password/` - Change password
- `GET /api/user/sessions/` - List active sessions
- `DELETE /api/user/sessions/<session_id>/` - Revoke session
- `GET /api/user/login-history/` - Get login history
- `GET /api/user/api-keys/` - List API keys
- `POST /api/user/api-keys/` - Create API key
- `DELETE /api/user/api-keys/<key_id>/` - Revoke API key
- `GET /api/user/data/export/` - Export user data
- `POST /api/user/data/delete/<type>/` - Delete specific data type
- `POST /api/user/change-email/` - Change email (with verification)
- `POST /api/user/delete-account/` - Delete account

---

## Frontend Functions

### Current Functions

1. **`loadSettings()`**
   - Fetches settings from `/api/user/settings/`
   - Merges with `localStorage` values
   - Populates all settings UI elements

2. **`saveSettings()`**
   - Collects all settings from UI
   - Sends to `/api/user/settings/update/`
   - Saves client-specific settings to `localStorage`
   - Applies theme and accent color immediately

3. **`applyAccentColor(color)`**
   - Applies accent color to CSS variables
   - Updates `--token-accent` and related variables

4. **`applyTheme(theme)`**
   - Applies theme to `document.documentElement.setAttribute('data-theme', theme)`

5. **`switchSettingsSection(section)`**
   - Switches between settings sections
   - Updates navigation active state

### Functions to Create

- `changePassword()` - Handle password change
- `enable2FA()` - Enable two-factor authentication
- `exportData()` - Export user data
- `deleteData(type)` - Delete specific data type
- `manageSessions()` - Manage active sessions
- `deleteAccount()` - Delete user account

---

## Data Structure

### Backend: Profile.user_settings JSONField

```json
{
  "appearance": "system",
  "accent_color": "default",
  "spoken_language": "auto",
  "voice": "spruce",
  "separate_voice_mode": false,
  "show_additional_models": false,
  "personalization": {
    "base_style_tone": "PlainClinical",
    "characteristic_warm": "default",
    "characteristic_enthusiastic": "default",
    "characteristic_headers": "default",
    "characteristic_emoji": "default",
    "custom_instructions": "",
    "nickname": "",
    "occupation": "",
    "more_about_you": "",
    "reference_saved_memories": true,
    "reference_chat_history": true
  },
  "notifications": {
    "email": true,
    "push": false,
    "chat": true,
    "summary": true,
    "digest": false
  },
  "security": {
    "two_factor_enabled": false
  },
  "data_retention": {
    "policy": "forever"
  }
}
```

---

## Implementation Priority

### High Priority (Core Functionality)
1. ✅ General Settings (Appearance, Accent Color, Language, Voice)
2. ✅ Personalization Settings (Tone, Characteristics, Custom Instructions)
3. ✅ Account Settings (Display Name, Profession)

### Medium Priority (User Experience)
4. Notifications Settings
5. Data Controls (Export, Deletion)
6. Security Settings (Password, 2FA, Sessions)

### Low Priority (Advanced Features)
7. Apps Settings
8. Schedules Settings
9. Parental Controls Settings

---

## Notes

- All settings should be saved to the backend `Profile.user_settings` JSONField
- Client-specific settings (appearance, accent_color) should also be saved to `localStorage` for immediate UI updates
- Settings should be loaded on page load and when opening the settings modal
- All destructive actions (delete data, delete account) should require confirmation
- All security-related changes (password, email, 2FA) should require re-authentication
- Settings should be validated on both frontend and backend

---

## Testing Checklist

- [ ] All General settings save and load correctly
- [ ] All Personalization settings save and load correctly
- [ ] Account settings save and load correctly
- [ ] Settings persist across page reloads
- [ ] Theme and accent color apply immediately
- [ ] Settings sync between devices (via backend)
- [ ] Error handling for failed saves
- [ ] Validation for invalid inputs
- [ ] Confirmation dialogs for destructive actions

---

**Last Updated:** 2026-01-07  
**Document Version:** 1.0

