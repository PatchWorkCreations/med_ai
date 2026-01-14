# Web App Settings Implementation

This document details the implementation of all settings functionality for the web app.

## Overview

All settings are now fully functional and synced between the server (database) and client (localStorage) for cross-device synchronization.

---

## Settings Implemented

### General Settings

1. **Appearance** (`appearance`)
   - Options: `system`, `light`, `dark`
   - Stored in: Profile.settings JSONField
   - Applied immediately via `applyTheme()` function
   - Synced to localStorage for client-side access

2. **Accent Color** (`accent_color`)
   - Options: `default`, `green`, `blue`, `purple`, `red`
   - Stored in: Profile.settings JSONField
   - Applied immediately via `applyAccentColor()` function
   - Uses radio button for "Default" and dropdown for custom colors

3. **Language** (`language`)
   - Options: `auto`, `en-US`, `es-ES`, `fr-FR`, `de-DE`, etc.
   - Stored in: Profile.language (CharField) and Profile.settings JSONField
   - Used for AI responses

4. **Spoken Language** (`spoken_language`)
   - Options: `auto`, `en-US`, `es-ES`, `fr-FR`, `de-DE`, etc.
   - Stored in: Profile.settings JSONField
   - Used for voice recognition and TTS

5. **Voice** (`voice`)
   - Options: `spruce`, `cove`, `ember`, `juniper`
   - Stored in: Profile.settings JSONField
   - Used for text-to-speech

6. **Separate Voice Mode** (`separate_voice_mode`)
   - Type: Boolean (toggle)
   - Stored in: Profile.settings JSONField
   - Controls whether voice mode uses separate full-screen interface

7. **Show Additional Models** (`show_additional_models`)
   - Type: Boolean (toggle)
   - Stored in: Profile.settings JSONField
   - Controls visibility of additional AI models in UI

### Personalization Settings

All stored in `Profile.settings.personalization` JSONField:

1. **Base Style and Tone** (`base_style_tone`)
   - Options: `PlainClinical`, `Clinical`, `Caregiver`, `Faith`, etc.
   - Default: `PlainClinical`

2. **Characteristic Warm** (`characteristic_warm`)
   - Options: `default`, `warm`, `neutral`, `cool`

3. **Characteristic Enthusiastic** (`characteristic_enthusiastic`)
   - Options: `default`, `enthusiastic`, `neutral`, `reserved`

4. **Characteristic Headers** (`characteristic_headers`)
   - Options: `default`, `yes`, `no`

5. **Characteristic Emoji** (`characteristic_emoji`)
   - Options: `default`, `yes`, `no`

6. **Custom Instructions** (`custom_instructions`)
   - Type: Text (textarea)
   - Free-form text for custom AI behavior

7. **Nickname** (`nickname`)
   - Type: Text
   - User's preferred nickname

8. **Occupation** (`occupation`)
   - Type: Text
   - User's occupation/profession

9. **More About You** (`more_about_you`)
   - Type: Text (textarea)
   - Additional context about the user

10. **Reference Saved Memories** (`reference_saved_memories`)
    - Type: Boolean
    - Default: `true`

11. **Reference Chat History** (`reference_chat_history`)
    - Type: Boolean
    - Default: `true`

### Account Settings

1. **Display Name** (`display_name`)
   - Stored in: Profile.display_name (CharField)
   - Used throughout the app for user identification

2. **Profession** (`profession`)
   - Stored in: Profile.profession (CharField)
   - User's profession

3. **First Name** (`first_name`)
   - Stored in: User.first_name

4. **Last Name** (`last_name`)
   - Stored in: User.last_name

5. **Email** (`email`)
   - Stored in: User.email

---

## Database Changes

### Profile Model Updates

Added new field:
```python
settings = models.JSONField(
    default=dict,
    blank=True,
    help_text="User settings: appearance, accent_color, spoken_language, voice, separate_voice_mode, show_additional_models, personalization, etc."
)
```

**Migration Required:**
```bash
python manage.py makemigrations myApp --name add_settings_to_profile
python manage.py migrate
```

---

## Backend Functions

### `get_user_settings` (GET /api/user/settings/)

**Returns:**
```json
{
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "profession": "Doctor",
  "language": "en-US",
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
  }
}
```

### `update_user_settings` (POST /api/user/settings/update/)

**Accepts:**
```json
{
  "display_name": "John Doe",
  "profession": "Doctor",
  "language": "en-US",
  "first_name": "John",
  "last_name": "Doe",
  "email": "user@example.com",
  "appearance": "light",
  "accent_color": "green",
  "spoken_language": "en-US",
  "voice": "spruce",
  "separate_voice_mode": true,
  "show_additional_models": false,
  "personalization": {
    "base_style_tone": "PlainClinical",
    "characteristic_warm": "warm",
    "characteristic_enthusiastic": "enthusiastic",
    "characteristic_headers": "yes",
    "characteristic_emoji": "no",
    "custom_instructions": "Be concise and friendly",
    "nickname": "Johnny",
    "occupation": "Physician",
    "more_about_you": "I work in emergency medicine",
    "reference_saved_memories": true,
    "reference_chat_history": true
  }
}
```

**Returns:**
```json
{
  "status": "success",
  "message": "Settings updated successfully"
}
```

---

## Frontend Implementation

### Settings Loading Flow

1. **On Settings Modal Open:**
   - `loadSettings()` is called
   - First attempts to load from server (`/api/user/settings/`)
   - Syncs server settings to localStorage
   - Falls back to localStorage if server fails
   - Applies all settings to UI elements

2. **Settings Saving Flow:**
   - `saveSettings()` collects all settings from UI
   - Saves to localStorage immediately (for client-side access)
   - Sends to server (`/api/user/settings/update/`)
   - Applies appearance and accent color immediately
   - Refreshes user display name

### Real-Time Updates

Settings changes are applied immediately via `initSettingsChangeHandlers()`:
- **Appearance**: Changes theme instantly
- **Accent Color**: Updates CSS variables immediately
- **Language**: Saved but applied on next chat message
- **Voice**: Saved for future voice interactions
- **Toggles**: Saved immediately

### localStorage Keys

All settings are stored in localStorage with `nm_` prefix:
- `nm_appearance`
- `nm_accent_color`
- `nm_language`
- `nm_spoken_language`
- `nm_voice`
- `nm_separate_voice_mode`
- `nm_show_additional_models`
- `nm_base_style_tone`
- `nm_characteristic_warm`
- `nm_characteristic_enthusiastic`
- `nm_characteristic_headers`
- `nm_characteristic_emoji`
- `nm_custom_instructions`
- `nm_personalization_nickname`
- `nm_personalization_occupation`
- `nm_more_about_you`
- `nm_reference_saved_memories`
- `nm_reference_chat_history`

---

## UI Components

### Settings Modal Structure

1. **Left Navigation** (Desktop):
   - General ⚙️
   - Notifications 🔔
   - Personalization 🎨
   - Apps 📱
   - Schedules 📅
   - Data controls 💾
   - Security 🔐
   - Parental controls 👨‍👩‍👧
   - Account 👤

2. **Mobile Dropdown**: Replaces left navigation on mobile

3. **Right Content Area**: Shows selected section's settings

### General Section Controls

- **Appearance**: Dropdown select
- **Accent Color**: Radio button (Default) + Dropdown (Color selection)
- **Language**: Dropdown select
- **Spoken Language**: Dropdown select with description
- **Voice**: Play button + Dropdown select
- **Separate Voice Mode**: Toggle switch with description
- **Show Additional Models**: Toggle switch

---

## Testing Checklist

- [ ] Appearance changes apply immediately (light/dark/system)
- [ ] Accent color changes apply immediately (default/green/blue/purple/red)
- [ ] Language setting saves and loads correctly
- [ ] Spoken language setting saves and loads correctly
- [ ] Voice setting saves and loads correctly
- [ ] Separate voice mode toggle saves and loads correctly
- [ ] Show additional models toggle saves and loads correctly
- [ ] Personalization settings save and load correctly
- [ ] Account settings (display name, profession) save and load correctly
- [ ] Settings sync across browser tabs (via localStorage)
- [ ] Settings persist after page refresh
- [ ] Settings load from server on login (cross-device sync)

---

## Migration Steps

1. **Create Migration:**
   ```bash
   python manage.py makemigrations myApp --name add_settings_to_profile
   ```

2. **Apply Migration:**
   ```bash
   python manage.py migrate
   ```

3. **Verify:**
   - Check that `Profile` model has `settings` JSONField
   - Test saving/loading settings via API

---

## Notes

- Settings are stored in both database (for cross-device sync) and localStorage (for immediate client-side access)
- Server settings take precedence over localStorage when loading
- All settings are saved together in a single API call
- Appearance and accent color are applied immediately for better UX
- Personalization settings affect AI behavior and response style
- Account settings (display_name, profession) are used throughout the app for personalization

---

*Last Updated: January 8, 2025*

