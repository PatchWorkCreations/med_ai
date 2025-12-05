# System Summary: NeuroMed AI Platform

## Overall System Function

**NeuroMed AI** is a medical AI assistant platform that provides intelligent health guidance through multiple interaction modes. The system serves both individual users and healthcare organizations with:

1. **Main Neuromed AI Chat** - Core conversational AI for medical questions
2. **Dashboard Analytics** - Comprehensive analytics for tracking usage and engagement
3. **Main Website** - Public-facing landing pages and user authentication
4. **Organizational Portal** - Multi-tenant healthcare organization management (with various staff apps)

---

## Core Components (Active & Important)

### 1. **Main Neuromed AI Chat** (`/api/send-chat/`)
**Location:** `myApp/views.py` - `send_chat()` function

**Function:**
- Primary AI chat interface powered by OpenAI GPT models
- Processes medical questions, symptoms, and uploaded files (PDFs, images, documents)
- Supports multiple communication tones:
  - **PlainClinical** - Warm but precise medical guidance
  - **Caregiver** - Comforting health companion mode
  - **Faith** - Faith-filled health guidance with spiritual support
  - **Clinical** - Structured SOAP notes for healthcare professionals
  - **Bilingual** - Multi-language support
  - **Geriatric** - Elderly care focused
  - **EmotionalSupport** - Emotional support mode

**Key Features:**
- File upload and medical record summarization
- Multi-language support (50+ languages)
- Session persistence (authenticated users)
- Context-aware responses (Quick Mode, Explain Mode, Full Breakdown Mode)
- Medical document parsing (PDF, DOCX, images via OCR)

**Endpoints:**
- `POST /api/send-chat/` - Main chat endpoint
- `POST /api/send_chat/` - Alias for frontend compatibility
- `GET /api/chat/sessions/` - List chat sessions
- `GET /api/chat/sessions/<id>/` - Get session details

---

### 2. **Dashboard Analytics** (`/dashboard/analytics/`)
**Location:** `myApp/analytics_views.py`, `myApp/views.py` - `analytics_dashboard()`

**Function:**
Comprehensive analytics dashboard tracking:
- **User Metrics:**
  - Unique visitors, page views, signups, sign-ins
  - Active users (DAU), conversion rates
  - User list with activity stats (summaries, chat sessions, sign-ins)

- **Traffic Analytics:**
  - Device/browser/OS breakdown
  - Geographic data (country-level)
  - Traffic sources (direct, search, social, referral)
  - Popular pages, entry/exit pages
  - UTM campaign tracking

- **Session Analytics:**
  - Average session duration
  - Pages per session
  - Bounce rate
  - Returning vs new visitors

- **Medical AI Analytics:**
  - Daily summaries and chat sessions
  - Care setting breakdown (hospital, ambulatory, urgent care)
  - Tone usage breakdown
  - Profession breakdown
  - Language usage
  - Satisfaction metrics

- **Time Series Data:**
  - Daily/hourly activity charts
  - Period comparison (current vs previous)
  - Conversion funnel analysis

**Access:** Staff-only (`is_staff` required)

---

### 3. **Main Website**
**Location:** `myApp/views.py`, `myApp/templates/`

**Components:**
- **Landing Page** (`/`) - Public homepage
- **Signup/Login** (`/signup/`, `/login/`) - User authentication
- **User Dashboard** (`/dashboard/`) - Personal dashboard showing medical summaries
- **About Page** (`/about/`) - Information about the platform
- **Legal Pages** (`/legal/`, `/terms/`, `/privacy/`) - Terms and privacy
- **Beta Feedback** (`/beta/`) - User feedback collection

**Features:**
- User registration and authentication
- Profile management (profession, language, display name)
- Medical summary history
- Chat session management (rename, archive, delete)

---

### 4. **Organizational Portal** (`/portal/`)
**Location:** `myApp/product_views.py`

**Function:**
Multi-tenant system for healthcare organizations:
- Organization management with domain-based access
- Patient and encounter management
- Staff role-based access
- Front desk board (Kanban-style encounter tracking)
- Various staff apps:
  - Triage (`/app/triage`)
  - Front Desk (`/app/frontdesk`)
  - Clinical (`/app/clinical`)
  - Diagnostics (`/app/diagnostics`)
  - Scribe (`/app/scribe`)
  - Coding (`/app/coding`)
  - Care (`/app/care`)

**API Endpoints:**
- `/api/v1/triage/chat` - Triage chat interface
- `/api/v1/upload` - File uploads
- `/api/v1/encounters/` - Encounter management
- `/api/v1/clinical/chart-brief` - Clinical chart summaries
- And more...

---

## Unused/Clutter Components

### **Kiosk Feature** (NOT IN USE - Consider Removing)
**Location:** 
- `myApp/product_views.py` - `kiosk_intake()`, `kiosk_consent()`
- `myApp/templates/kiosk/` - 3 template files
- `myApp/urls.py` - Routes: `/kiosk/intake`, `/kiosk/consent`

**What it was:**
- Token-based kiosk interface for patient intake
- Required device tokens for organization binding
- No-login patient check-in system

**Why it's clutter:**
- Not actively used
- Adds complexity to codebase
- References scattered across:
  - Dashboard templates (kiosk link creation UI)
  - Admin launch links page
  - Device token management code
  - Multiple API endpoints checking for kiosk tokens

**Files to consider removing:**
- `myApp/templates/kiosk/intake.html`
- `myApp/templates/kiosk/consent.html`
- `myApp/templates/kiosk/token_required.html`
- Kiosk-related code in `product_views.py` (lines ~513-607)
- Kiosk routes in `urls.py` (lines 125-126)
- Kiosk UI elements in dashboard templates

---

## System Architecture Summary

### **Data Models** (`myApp/models.py`)
- **User/Profile** - User accounts with profession, language preferences
- **ChatSession** - Persistent chat conversations
- **MedicalSummary** - Summarized medical records
- **Visitor/PageView/Session** - Analytics tracking
- **Org/Patient/Encounter** - Multi-tenant healthcare data
- **BetaFeedback** - User feedback collection

### **Key Technologies**
- **Backend:** Django (Python)
- **AI:** OpenAI GPT-4o, Whisper (voice transcription)
- **File Processing:** PyMuPDF (PDF), python-docx, PIL (images), OCR
- **Analytics:** Custom tracking with database models
- **Frontend:** HTML templates with JavaScript

### **Authentication & Security**
- Django authentication system
- CSRF protection
- Session-based guest access
- Organization-scoped access for portal
- IP and country tracking

---

## Recommendations

1. **Remove Kiosk Feature** - Clean up unused kiosk code and templates
2. **Focus on Core:**
   - Main AI chat (`/api/send-chat/`)
   - Dashboard analytics (`/dashboard/analytics/`)
   - Main website (landing, signup, dashboard)
3. **Keep Portal** - If organizations are using it, maintain it; otherwise consider deprecation

---

## File Structure Overview

```
myApp/
├── views.py              # Main AI chat, dashboard, website views
├── analytics_views.py    # Analytics calculations
├── analytics_utils.py    # Analytics helper functions
├── medical_analytics.py  # Medical-specific analytics
├── product_views.py      # Portal and kiosk views (kiosk = unused)
├── models.py             # Database models
├── urls.py               # URL routing
├── templates/
│   ├── dashboard/        # Dashboard templates
│   ├── analytics/        # Analytics dashboard templates
│   ├── kiosk/           # UNUSED - kiosk templates
│   └── [other templates]
└── api_chat.py          # Chat session API endpoints
```

---

## Summary

**Active & Important:**
✅ Main Neuromed AI Chat - Core functionality  
✅ Dashboard Analytics - Comprehensive tracking  
✅ Main Website - User-facing interface  
✅ Organizational Portal - If in use  

**Unused Clutter:**
❌ Kiosk Feature - Should be removed


