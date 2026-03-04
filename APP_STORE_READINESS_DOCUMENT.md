# NeuroMed Aira — App Store Readiness Document

**Last Updated:** February 2025  
**Purpose:** Summary of recently created functions, current progress, and pre–App Store checklist

---

## Table of Contents

1. [Recently Created Functions](#recently-created-functions)
2. [Current Progress Overview](#current-progress-overview)
3. [Pre–App Store Double-Check Checklist](#pre-app-store-double-check-checklist)

---

## Recently Created Functions

### 1. **Adaptive Response System** (January 2025)

**Status:** Implemented, feature-flagged (disabled by default)

| Component | Location | Description |
|-----------|----------|-------------|
| `InteractionProfile` model | `myApp/models.py` | Stores inferred user preferences (verbosity, emotional support, structure, technical depth) |
| `SignalExtractor` | `myApp/preference_inference.py` | Extracts behavioral signals from user messages |
| `PreferenceInference` | `myApp/preference_inference.py` | Updates profiles with weighted smoothing |
| `ResponseStrategyResolver` | `myApp/preference_inference.py` | Maps profiles to style modifiers |
| `build_adaptive_system_prompt()` | `myApp/views.py` | Injects style-only modifiers into system prompts |

**Key behavior:**
- Learns from user interaction patterns
- Style-only modifications (never changes medical content)
- Topic-change detection for context reset
- Feature flag: `ENABLE_ADAPTIVE_RESPONSE` (set to `True` to enable)

---

### 2. **Mobile API (iOS Backend)** (October 2025)

**Status:** Backend complete; iOS needs 2 model fixes

| Endpoint | Method | Function | Status |
|----------|--------|----------|--------|
| `/api/signup/` | POST | User registration | ✅ Working |
| `/api/login/` | POST | Authentication + token | ✅ Working |
| `/api/auth/status/` | GET | Health check | ✅ Working |
| `/api/send-chat/` | POST | AI chat (all tones, modes, file upload) | ✅ Backend ready |
| `/api/chat/sessions/` | GET | List chat sessions | ✅ Working |
| `/api/chat/sessions/new/` | POST | Create session | ✅ Working |
| `/api/chat/clear-session/` | POST | Clear current session | ✅ Working |
| `/api/user/settings/` | GET | Get user profile | ✅ Working |
| `/api/user/settings/update/` | POST | Update profile | ✅ Working |
| `/api/config/` | GET | API configuration | ✅ Working |
| `/api/tones/` | GET | Available AI tones | ✅ Working |

---

### 3. **Chat & AI Core Functions** (`myApp/views.py`)

| Function | Purpose |
|----------|---------|
| `send_chat()` | Main chat handler — processes messages, files, tones, modes |
| `_classify_mode()` | Classifies QUICK / EXPLAIN / FULL based on input |
| `build_system_prompt()` | Builds tone-specific system prompts |
| `build_adaptive_system_prompt()` | Adds adaptive style modifiers (when enabled) |
| `extract_contextual_medical_insights_from_image()` | Single-image analysis |
| `extract_contextual_medical_insights_from_multiple_images()` | Multi-image analysis |
| `summarize_medical_record()` | Summarizes uploaded medical documents |
| `normalize_tone()` | Normalizes tone names for API compatibility |

---

### 4. **Session & Chat Management**

| Function | Purpose |
|----------|---------|
| `list_chat_sessions()` | List user sessions |
| `get_chat_session()` | Get single session with messages |
| `create_chat_session()` | Create new session |
| `clear_session()` | Clear current session |
| `chat_session_rename()` | Rename session |
| `chat_session_archive()` | Archive session |
| `chat_session_delete()` | Delete session |

---

### 5. **User Account & Security**

| Function | Purpose |
|----------|---------|
| `get_user_settings()` | Get display name, profession, language |
| `update_user_settings()` | Update profile |
| `change_password()` | Password change |
| `export_account_data()` | GDPR-style data export |
| `delete_account()` | Account deletion |
| `forgot_password()` / `verify_otp()` / `reset_password()` | OTP-based password reset |
| `get_active_sessions()` / `revoke_session()` | Session management |
| `update_privacy_settings()` / `update_security_alerts()` | Privacy & security prefs |

---

### 6. **Billing & Subscriptions** (`myApp/billing_views.py`)

| Function | Purpose |
|----------|---------|
| `billing_settings()` | Billing dashboard |
| `subscription_status()` | Current plan status |
| `create_checkout_session()` | PayPal checkout |
| `capture_order()` | Order capture |
| `paypal_webhook()` | Webhook handler |
| `billing_history()` | Payment history |
| `cancel_subscription()` | Cancel subscription |
| `contact_clinical()` | Clinical support contact |

---

### 7. **Analytics & Dashboard**

| Function | Purpose |
|----------|---------|
| `analytics_dashboard()` | Staff analytics (visitors, sessions, AI usage) |
| `analytics_export()` | CSV/PDF export |
| `export_users_list()` | User list export |

---

### 8. **Premium Dashboard** (`new_dashboard()`)

- 3-zone layout: Sidebar, Main Chat, Composer  
- Session management (rename, archive, delete)  
- Tone selector, care setting, faith setting  
- Language picker (50+ languages)  
- Voice dictation, file upload (15-file limit)  
- Settings modal, summary modal, feedback modal  

---

## Current Progress Overview

### Backend (Web + API)

| Component | Status |
|-----------|--------|
| Main AI Chat | ✅ 100% |
| Mobile API | ✅ 100% |
| Authentication (email + Google OAuth) | ✅ 100% |
| Session management | ✅ 100% |
| User settings | ✅ 100% |
| Billing (PayPal) | ✅ Implemented |
| Analytics dashboard | ✅ Staff-only |
| Adaptive response system | ✅ Implemented (disabled by default) |
| Legal pages (Terms, Privacy, Trust) | ✅ Implemented |

### iOS App

| Component | Status |
|-----------|--------|
| Backend integration | ✅ Ready |
| User model | ⚠️ Needs fix (date format, optional fields) |
| ChatMessage model | ⚠️ Needs fix (remove `metadata` property) |
| Login flow | ⚠️ Blocked by User model |
| Chat flow | ⚠️ Blocked until login works |

**Estimated fix time:** ~7 minutes (see `mobile_api/QUICK_FIX_GUIDE.md` and `mobile_api/CHATMESSAGE_QUICK_FIX.md`)

---

## Pre–App Store Double-Check Checklist

### 1. Legal & Compliance

| Item | Status | Notes |
|------|--------|-------|
| Privacy Policy | ⬜ Verify | Must be linked from app; `/privacy` or `/legal/#privacy` |
| Terms of Service | ⬜ Verify | `/terms` or `/legal/#terms` |
| Medical disclaimer | ⬜ Verify | App must clearly state it does **not** provide diagnosis or replace medical professionals |
| Data collection disclosure | ⬜ Verify | Describe what data is collected (chat, health info, usage) and how it is used |
| Age rating | ⬜ Set | Medical apps typically 17+ or 12+ depending on content |
| Export compliance | ⬜ Confirm | Encryption use (e.g., TLS) — may need export compliance declaration |

---

### 2. Health & Medical App Guidelines (Apple)

| Item | Status | Notes |
|------|--------|-------|
| Not providing diagnosis | ⬜ Verify | Prompts and UI must state this is informational only |
| Not replacing medical care | ⬜ Verify | Clear “seek professional care” messaging |
| Health data handling | ⬜ Verify | If storing health-related chat, follow Section 5.1.3 |
| HealthKit | ⬜ N/A or Implement | Not used unless integrating HealthKit |
| HIPAA | ⬜ Document | Trust page mentions HIPAA; confirm actual compliance if claiming it |

---

### 3. iOS App–Specific

| Item | Status | Notes |
|------|--------|-------|
| User model fix | ⬜ Apply | `firstName`, `lastName` optional; `dateJoined`, `lastLogin` as `String` |
| ChatMessage model fix | ⬜ Apply | Remove `metadata` property from model and `CodingKeys` |
| App Store screenshots | ⬜ Create | Required sizes for all device types |
| App description | ⬜ Write | Clear description, medical disclaimer in text |
| Keywords | ⬜ Choose | Relevant, no misleading terms |
| Support URL | ⬜ Set | Working support or contact page |
| Privacy policy URL | ⬜ Set | Must match link in app |

---

### 4. Functional Testing

| Item | Status | Notes |
|------|--------|-------|
| Signup flow | ⬜ Test | Email + password, Google OAuth |
| Login flow | ⬜ Test | After User model fix |
| Chat (all tones) | ⬜ Test | PlainClinical, Caregiver, Faith, Clinical, Geriatric, EmotionalSupport |
| File upload | ⬜ Test | PDF, images, DOCX |
| Session management | ⬜ Test | Create, list, rename, archive, delete |
| Offline behavior | ⬜ Test | Clear error messages when offline |
| Deep links | ⬜ Test | If used (e.g., password reset, OAuth callback) |

---

### 5. Security & Data

| Item | Status | Notes |
|------|--------|-------|
| API keys | ⬜ Verify | No hardcoded keys in app or public repo |
| HTTPS only | ⬜ Verify | All API calls over HTTPS |
| Token storage | ⬜ Verify | Secure storage (e.g., Keychain) for auth tokens |
| Sensitive data in logs | ⬜ Verify | No health or PII in logs |

---

### 6. UX & Accessibility

| Item | Status | Notes |
|------|--------|-------|
| Loading states | ⬜ Verify | Spinners or placeholders during API calls |
| Error messages | ⬜ Verify | User-friendly, no raw stack traces |
| Accessibility labels | ⬜ Verify | VoiceOver support for main actions |
| Minimum font size | ⬜ Verify | Readable text (especially for medical content) |

---

### 7. Backend / Server

| Item | Status | Notes |
|------|--------|-------|
| Production environment | ⬜ Verify | Stable, scalable hosting |
| `OPENAI_API_KEY` | ⬜ Verify | Set in production, not exposed to client |
| Database backups | ⬜ Verify | Regular backups, tested restore |
| Rate limiting | ⬜ Verify | Protect chat and auth endpoints |
| CORS / API domain | ⬜ Verify | Only allowed origins can call API |

---

## Summary

**Recently built:**
- Adaptive Response System (preference learning)
- Full Mobile API for iOS
- Session clear endpoint
- Account export, deletion, OTP reset
- Billing and subscription flows

**Current blockers:**
- iOS User and ChatMessage model fixes (≈7 min)
- Verification of legal and App Store checklist items

**Recommended order:**
1. Apply iOS model fixes and validate login + chat
2. Recheck all legal and App Store items
3. Run through functional and security checklist
4. Prepare metadata (screenshots, description, support URL) for App Store Connect

---

*Document generated from codebase analysis and existing documentation.*
