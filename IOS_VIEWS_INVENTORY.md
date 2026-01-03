# iOS Views Inventory - Complete Implementation Details

This document provides comprehensive details about what currently exists in the codebase for each iOS view/feature requested, including complete code snippets, API specifications, templates, and implementation details.

---

## HomeView (1)

### ✅ **HomeView / Dashboard**
- **Status:** ✅ **Fully Implemented**
- **Location:** 
  - Main dashboard: `/dashboard/` (`myApp/views.py` - `dashboard()`)
  - Premium dashboard: `/dashboard/new/` (`myApp/views.py` - `new_dashboard()`)
- **View Implementation:**
```python
# myApp/views.py lines 1993-2020
@login_required
def dashboard(request):
    care = norm_setting(request.GET.get("care_setting"))
    qs = MedicalSummary.objects.filter(user=request.user).order_by("-created_at")
    if request.GET.get("care_setting"):  # apply only if explicitly filtered
        qs = qs.filter(care_setting=care)
    return render(request, "dashboard.html", {"summaries": qs, "selected_care": care})

@login_required
def new_dashboard(request):
    """Premium dashboard with upgraded UI/UX"""
    try:
        care = norm_setting(request.GET.get("care_setting"))
        qs = MedicalSummary.objects.filter(user=request.user).order_by("-created_at")
        if request.GET.get("care_setting"):  # apply only if explicitly filtered
            qs = qs.filter(care_setting=care)
        context = {
            "summaries": qs,
            "selected_care": care,
        }
        return render(request, "new_dashboard.html", context)
    except Exception as e:
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        error_trace = traceback.format_exc()
        logger.error(f"Error in new_dashboard: {str(e)}\n{error_trace}")
        raise
```
- **URL Configuration:**
```python
# myApp/urls.py
path('dashboard/', views.dashboard, name='dashboard'),
path('dashboard/new/', views.new_dashboard, name='new_dashboard'),
```
- **Features:**
  - Chat interface with AI assistant
  - File upload support (PDF, images, documents)
  - Session management (create, list, rename, archive, delete)
  - Tone selection (6 tones: PlainClinical, Caregiver, Faith, Clinical, Geriatric, EmotionalSupport)
  - Language selection (50+ languages)
  - Care settings (Hospital, Ambulatory, Urgent)
  - Faith settings (6 traditions)
  - Medical summary history
  - Settings modal
- **Templates:**
  - `myApp/templates/dashboard.html` (2,465 lines)
  - `myApp/templates/new_dashboard.html` (3,551 lines)
- **API Endpoints Used:**
  - `POST /api/send-chat/` - Send chat messages
  - `GET /api/chat/sessions/` - List chat sessions
  - `POST /api/chat/sessions/new/` - Create new session
  - `POST /api/chat/sessions/<id>/rename/` - Rename session
  - `POST /api/chat/sessions/<id>/archive/` - Archive session
  - `POST /api/chat/sessions/<id>/delete/` - Delete session
  - `GET /api/user/settings/` - Get user settings
  - `POST /api/user/settings/update/` - Update user settings

---

## Notification bell button (top right) — needs NotificationsView

### ❌ **NotificationsView**
- **Status:** ❌ **Not Implemented**
- **What exists:** No notification system found in the codebase
- **What's needed:** 
  - Notification model/database
  - Notification bell UI component
  - Notification list view
  - Notification API endpoints

---

## SettingsView (6)

### ✅ **SettingsView**
- **Status:** ✅ **Partially Implemented**
- **Location:** Settings modal in dashboard (`myApp/templates/dashboard.html` lines 546-572)
- **Template Code:**
```html
<!-- Settings Modal -->
<div id="settingsModal" class="fixed inset-0 z-50 hidden items-center justify-center bg-black/50 backdrop-blur-sm transition-opacity duration-300">
  <div class="bg-white rounded-2xl shadow-2xl max-w-lg w-full p-8 relative ring-1 ring-gray-200 animate-fadeInUp">
    <button onclick="closeSettingsModal()" class="absolute top-5 right-6 text-gray-400 hover:text-gray-600 text-2xl transition">&times;</button>
    <div class="mb-6 flex items-center gap-3">
      <i class="fa-solid fa-sliders text-2xl text-[#236092]"></i>
      <h2 class="text-3xl font-bold text-gray-800 tracking-tight">Settings</h2>
    </div>
    <div class="mb-5">
      <label for="displayName" class="block text-sm font-semibold text-gray-700 mb-1">Display Name</label>
      <input type="text" id="displayName" placeholder="e.g. Maria Gregory" class="w-full px-4 py-3 border rounded-lg shadow-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#28926D] bg-gray-50 transition" />
    </div>
    <div class="mb-5">
      <label for="profession" class="block text-sm font-semibold text-gray-700 mb-1">Profession</label>
      <input type="text" id="profession" placeholder="e.g. Healthcare Advocate, Tech Founder" class="w-full px-4 py-3 border rounded-lg shadow-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#28926D] bg-gray-50 transition" />
    </div>
    <div class="mb-6 text-sm text-gray-500 italic">
      <i class="fa-solid fa-image-portrait mr-2 text-gray-400"></i> Profile photo upload coming soon...
    </div>
    <div class="flex justify-between items-center mt-6">
      <button onclick="saveSettings()" class="bg-[#236092] hover:bg-[#1B5A8E] text-white font-semibold px-6 py-2.5 rounded-full shadow-md transition flex items-center gap-2">
        <i class="fa-solid fa-check-circle text-white text-lg"></i> Save Changes
      </button>
      <button onclick="logoutUser()" class="text-sm text-red-600 hover:underline">Logout</button>
    </div>
  </div>
</div>
```
- **JavaScript Implementation:**
```javascript
// myApp/templates/dashboard.html lines 2171-2213
async function openSettingsModal() {
  const modal = document.getElementById("settingsModal");
  const nameEl = document.getElementById("displayName");
  const profEl = document.getElementById("profession");

  // 1) Open the modal first so the user sees something immediately
  if (modal) { modal.classList.remove("hidden"); modal.classList.add("flex"); }

  try {
    const res = await fetch("/api/user/settings/", {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });

    const ct = res.headers.get("content-type") || "";
    if (!res.ok || !ct.includes("application/json")) {
      throw new Error(`Unexpected response (${res.status}); content-type=${ct}`);
    }

    const data = await res.json();

    if (nameEl) nameEl.value = data.display_name || "";
    if (profEl) profEl.value = data.profession || "";
  } catch (err) {
    console.warn("Settings fetch failed:", err);
  }
}

function saveSettings() {
  const name = document.getElementById("displayName").value.trim();
  const profession = document.getElementById("profession").value.trim();
  fetch("/api/user/settings/update/", {
    method:"POST",
    headers:{ "Content-Type":"application/json","X-CSRFToken":getCSRFToken() },
    body: JSON.stringify({ display_name:name, profession })
  }).then(r=>r.json()).then(()=>{ alert("Settings updated successfully!"); closeSettingsModal(); });
}

function closeSettingsModal(){
  const modal = document.getElementById("settingsModal");
  modal.classList.remove("flex"); modal.classList.add("hidden");
}
```
- **Backend API Endpoints:**
  - `GET /api/user/settings/` - Get user settings (`myApp/views.py` lines 2483-2490)
  - `POST /api/user/settings/update/` - Update user settings (`myApp/views.py` lines 2492-2513)
- **Backend Implementation:**
```python
# myApp/views.py lines 2483-2513
@login_required
def get_user_settings(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return JsonResponse({
        "display_name": profile.display_name or request.user.first_name or request.user.username,
        "profession": profile.profession or "",
        "language": profile.language,  # ✅ include language
    })

@login_required
def update_user_settings(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            profile, _ = Profile.objects.get_or_create(user=request.user)
            profile.display_name = data.get("display_name", profile.display_name)
            profile.profession = data.get("profession", profile.profession)

            if "language" in data:  # ✅ allow updates
                profile.language = data["language"]

            profile.save()
            return JsonResponse({"status": "success"})
        except Exception:
            return JsonResponse({
                "message": "Hi! Our system is busy right now. Please try again in a few minutes."
            }, status=500)

    return JsonResponse({
        "message": "Hi! That action isn't available right now. Please try again in a few minutes."
    }, status=400)
```
- **Mobile API Endpoints (Token-based):**
```python
# mobile_api/compat_views.py lines 184-225
@api_view(['GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings(request):
    """
    Get user settings/profile.
    GET /api/user/settings/
    """
    return Response(user_payload(request.user), status=200)

@api_view(['POST'])
@parser_classes([JSONParser])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def user_settings_update(request):
    """
    Update user settings/profile.
    POST /api/user/settings/update/
    """
    user = request.user
    changed = False
    
    # Update fields from request
    if 'first_name' in request.data:
        user.first_name = request.data['first_name']
        changed = True
    if 'last_name' in request.data:
        user.last_name = request.data['last_name']
        changed = True
    if 'email' in request.data:
        new_email = request.data['email'].lower()
        if new_email != user.email:
            # Check if email is already taken
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                return Response({"error": "Email already in use"}, status=400)
            user.email = new_email
            changed = True
    
    if changed:
        user.save()
    
    return Response(user_payload(user), status=200)
```
- **Request/Response Format:**
  - **GET Request:** `GET /api/user/settings/`
  - **GET Response:**
```json
{
  "display_name": "Maria Gregory",
  "profession": "Healthcare Advocate",
  "language": "en-US"
}
```
  - **POST Request:** `POST /api/user/settings/update/`
```json
{
  "display_name": "Maria Gregory",
  "profession": "Healthcare Advocate",
  "language": "es-ES"
}
```
  - **POST Response:**
```json
{
  "status": "success"
}
```
- **Current Features:**
  - Display name editing
  - Profession editing
  - Language preference (stored in Profile model)
  - Logout functionality
- **What's missing:**
  - Profile picture upload (UI shows "Profile photo upload coming soon...")
  - Additional settings options

### ✅ **Edit Profile Picture Button — needs EditProfileView**
- **Status:** ⚠️ **UI Placeholder Only**
- **Location:** `myApp/templates/dashboard.html` line 563
- **Current State:** 
  - UI shows: "Profile photo upload coming soon..."
  - No backend implementation for profile picture upload
  - No `EditProfileView` exists
- **What exists:**
  - User model has standard Django user fields
  - Profile model exists (`myApp/models.py` - `Profile`)
  - Media handling infrastructure exists (`USER_MEDIA_SUBDIR` in `myApp/views.py`)
- **What's needed:**
  - Profile picture upload endpoint
  - Image processing/storage
  - EditProfileView implementation

### ✅ **Language Selection — needs LanguageSelectionView**
- **Status:** ✅ **Fully Implemented**
- **Location:** 
  - Dashboard language picker (`myApp/templates/dashboard.html` lines 1398-1417)
  - Landing page language selector (`myApp/templates/landing_page.html` lines 534-595)
- **Complete Language List (50+ languages):**
```javascript
// myApp/templates/dashboard.html lines 1398-1410
const LANGUAGE_CHOICES = [
  ['en-US','English'],['ja-JP','Japanese'],['es-ES','Spanish'],['fr-FR','French'],['de-DE','German'],
  ['it-IT','Italian'],['pt-PT','Portuguese (Portugal)'],['pt-BR','Portuguese (Brazil)'],['ru-RU','Russian'],
  ['zh-CN','Chinese (Simplified)'],['zh-TW','Chinese (Traditional)'],['ko-KR','Korean'],['ar-SA','Arabic (Saudi Arabia)'],
  ['tr-TR','Turkish'],['nl-NL','Dutch'],['sv-SE','Swedish'],['pl-PL','Polish'],['da-DK','Danish'],['no-NO','Norwegian'],
  ['fi-FI','Finnish'],['he-IL','Hebrew'],['th-TH','Thai'],['hi-IN','Hindi'],['cs-CZ','Czech'],['ro-RO','Romanian'],
  ['hu-HU','Hungarian'],['sk-SK','Slovak'],['bg-BG','Bulgarian'],['uk-UA','Ukrainian'],['vi-VN','Vietnamese'],['id-ID','Indonesian'],
  ['ms-MY','Malay'],['sr-RS','Serbian'],['hr-HR','Croatian'],['el-GR','Greek'],['lt-LT','Lithuanian'],['lv-LV','Latvian'],
  ['et-EE','Estonian'],['sl-SI','Slovenian'],['is-IS','Icelandic'],['sq-AL','Albanian'],['mk-MK','Macedonian'],
  ['bs-BA','Bosnian'],['ca-ES','Catalan'],['gl-ES','Galician'],['eu-ES','Basque'],['hy-AM','Armenian'],['fa-IR','Persian'],
  ['sw-KE','Swahili'],['ta-IN','Tamil'],['te-IN','Telugu'],['kn-IN','Kannada'],['ml-IN','Malayalam'],['mr-IN','Marathi'],
  ['pa-IN','Punjabi'],['gu-IN','Gujarati'],['or-IN','Odia'],['as-IN','Assamese'],['ne-NP','Nepali'],['si-LK','Sinhala'],
];
```
- **JavaScript Functions:**
```javascript
// myApp/templates/dashboard.html lines 1411-1427
function guessBrowserLang(){
  const nav = (navigator.languages && navigator.languages[0]) || navigator.language || 'en-US';
  return LANGUAGE_CHOICES.find(([code]) => code === nav) ? nav : 'en-US';
}
function loadLang(){ return localStorage.getItem('nm_lang') || guessBrowserLang(); }
function saveLang(code){ localStorage.setItem('nm_lang', code); }
function labelForLang(code){ const found = LANGUAGE_CHOICES.find(([c])=>c===code); return found ? found[1] : code; }
function applyLangUI(code){
  const label = labelForLang(code);
  const b1 = document.getElementById('langBtnLabel');
  const b2 = document.getElementById('mLangBtnLabel');
  if (b1) b1.textContent = label;
  if (b2) b2.textContent = label;
  document.querySelectorAll('#mLangList [data-lang]').forEach(el=>{
    el.querySelector('.fa-check')?.classList.toggle('hidden', el.dataset.lang !== code);
  });
}
```
- **Backend Model:**
```python
# myApp/models.py lines 6-67
LANGUAGE_CHOICES = [
    ('en-US', 'English'),
    ('ja-JP', 'Japanese'),
    ('es-ES', 'Spanish'),
    ('fr-FR', 'French'),
    ('de-DE', 'German'),
    # ... 50+ more languages
]

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en-US'
    )
    # ... other fields
```
- **API Support:**
  - Language stored in `Profile.language` field
  - Updated via `POST /api/user/settings/update/` with `language` parameter
- **Features:**
  - 50+ languages supported
  - Browser language auto-detection (`guessBrowserLang()`)
  - LocalStorage persistence (`nm_lang`)
  - Language codes: en-US, es-ES, fr-FR, ja-JP, zh-CN, ar-SA, etc.
- **Backend:**
  - Language preference saved to user Profile
  - Used in AI chat responses via `lang` parameter
- **Note:** While the functionality exists, there's no dedicated `LanguageSelectionView` page - it's integrated into the dashboard

### ✅ **Privacy Policy — needs PrivacyPolicyView**
- **Status:** ✅ **Fully Implemented**
- **Location:**
  - `/privacy/` - Privacy policy redirect (`myApp/views.py` - `privacy_redirect()`)
  - `/legal/` - Combined legal page (`myApp/views.py` - `LegalView`)
- **Backend Implementation:**
```python
# myApp/views.py lines 2666-2686
class LegalView(TemplateView):
    """
    Renders the single-page 'Terms of Use & Privacy Policy' template.
    """
    template_name = "legal/terms_privacy.html"

    # Optional: pass an effective date from server-side
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["effective_date"] = date.today()  # or a fixed date, e.g., date(2025, 8, 11)
        return ctx

def terms_redirect(_request):
    # Django can't append fragments via reverse(), so use a raw redirect.
    return HttpResponseRedirect("/legal/#terms")

def privacy_redirect(_request):
    return HttpResponseRedirect("/legal/#privacy")
```
- **URL Configuration:**
```python
# myApp/urls.py
path("legal/", LegalView.as_view(), name="legal"),
path("terms/", terms_redirect, name="terms"),
path("privacy/", privacy_redirect, name="privacy"),
```
- **Templates:**
  - `myApp/templates/legal/terms_privacy.html` - Combined Terms & Privacy page (367 lines)
- **Features:**
  - Full privacy policy content
  - Terms of Use included
  - Print-friendly styling
  - Mobile-responsive
  - Table of contents navigation
  - Anchor links for direct navigation to sections
- **Note:** Privacy policy is part of the combined legal page, not a separate dedicated view

### ✅ **Terms of Service — needs TermsOfServiceView**
- **Status:** ✅ **Fully Implemented**
- **Location:**
  - `/terms/` - Terms redirect (`myApp/views.py` - `terms_redirect()`)
  - `/legal/` - Combined legal page (`myApp/views.py` - `LegalView`)
- **Templates:**
  - `myApp/templates/legal/terms_privacy.html` - Combined Terms & Privacy page
- **Features:**
  - Full terms of service content
  - Privacy policy included
  - Print-friendly styling
  - Mobile-responsive
  - Table of contents navigation
- **Note:** Terms are part of the combined legal page, not a separate dedicated view

### ⚠️ **Export My Data — needs ExportDataView**
- **Status:** ⚠️ **Staff-Only Export Exists**
- **Location:** 
  - `/dashboard/analytics/export/` - Analytics export (`myApp/views.py` lines 2143-2259)
  - User list export: `export_users_list()` function (`myApp/views.py` lines 2262-2333)
- **Backend Implementation:**
```python
# myApp/views.py lines 2143-2259
@login_required
def analytics_export(request):
    """Export analytics data as PDF or CSV"""
    from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
    from django.db.models import Count
    from .models import Visitor, PageView, UserSignup, UserSignin
    from .analytics_views import get_analytics_data
    from django.utils import timezone
    from datetime import timedelta, datetime
    import csv
    import json
    
    # Only staff can export
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to export analytics.")
    
    export_format = request.GET.get('export', 'csv')
    
    # Handle user export
    if 'users_' in export_format:
        format_type = export_format.replace('users_', '')
        return export_users_list(request, format_type)
    
    # ... date range handling ...
    
    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analytics_{start_date}_{end_date}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Period', f'{start_date} to {end_date}'])
        writer.writerow(['Unique Visitors', data['unique_visitors']])
        writer.writerow(['Page Views', data['page_views']])
        # ... more rows ...
        
        return response
    
    elif export_format == 'pdf':
        from django.template.loader import render_to_string
        html_content = render_to_string('analytics/export_pdf.html', {
            'data': data,
            'start_date': start_date,
            'end_date': end_date,
            'exported_at': timezone.now()
        })
        # ... PDF generation ...
```

```python
# myApp/views.py lines 2262-2333
@login_required
def export_users_list(request, format_type='csv'):
    """Export user list as CSV or PDF"""
    from django.http import HttpResponse, HttpResponseForbidden
    from django.contrib.auth import get_user_model
    from .models import Profile
    from django.db.models import Count, Max, Q
    import csv
    from django.utils import timezone
    
    # Only staff can export
    if not request.user.is_staff:
        return HttpResponseForbidden("You do not have permission to export user data.")
    
    User = get_user_model()
    
    # Get all users with stats
    users = User.objects.select_related('profile').annotate(
        total_summaries=Count('summaries', distinct=True),
        total_chat_sessions=Count('chatsession', distinct=True),
        total_signins=Count('signin_records', filter=Q(signin_records__success=True), distinct=True),
        last_signin=Max('signin_records__created_at', filter=Q(signin_records__success=True))
    ).order_by('-date_joined')
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="users_export_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Username', 'Email', 'Display Name', 'First Name', 'Last Name',
            'Profession', 'Language', 'Signup Date', 'Last Login', 'Total Signins',
            'Total Summaries', 'Total Chat Sessions', 'Status', 'Is Staff',
            'Signup IP', 'Signup Country', 'Last Login IP', 'Last Login Country'
        ])
        
        for user in users:
            profile = getattr(user, 'profile', None)
            writer.writerow([
                user.username,
                user.email,
                profile.display_name if profile else '',
                user.first_name or '',
                user.last_name or '',
                profile.profession if profile else '',
                profile.language if profile else 'en-US',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else '',
                user.total_signins or 0,
                user.total_summaries or 0,
                user.total_chat_sessions or 0,
                'Active' if user.is_active else 'Inactive',
                'Yes' if user.is_staff else 'No',
                profile.signup_ip if profile else '',
                profile.signup_country if profile else '',
                profile.last_login_ip if profile else '',
                profile.last_login_country if profile else '',
            ])
        
        return response
```
- **URL Configuration:**
```python
# myApp/urls.py
path('dashboard/analytics/export/', views.analytics_export, name='analytics_export'),
```
- **Current Features:**
  - CSV export for analytics data
  - PDF export for analytics reports
  - User list export (CSV/PDF) - **Staff only**
  - Date range filtering
  - Comprehensive user statistics
- **What exists:**
  - Export functionality for staff/admin users
  - CSV and PDF generation
  - User data export (username, email, profile data, activity stats)
  - Analytics data export
- **What's missing:**
  - User-facing "Export My Data" feature
  - GDPR-compliant personal data export
  - Individual user data export endpoint
  - No `ExportDataView` for regular users
  - No API endpoint for mobile apps

### ❌ **Backend Debug — needs BackendDebugView**
- **Status:** ❌ **Not Implemented**
- **What exists:** No debug view found in the codebase
- **What's needed:**
  - Debug information display
  - API status/health check
  - Configuration display
  - BackendDebugView implementation

---

## SupportView (6)

### ⚠️ **SupportView**
- **Status:** ⚠️ **Partial Implementation**
- **Location:** Help card in dashboard sidebar (`myApp/templates/dashboard/_sidebar.html` lines 99-105)
- **Template Code:**
```html
<!-- myApp/templates/dashboard/_sidebar.html lines 99-105 -->
<!-- Help card -->
<div class="mt-auto p-4 text-xs text-slate-500">
  <div class="rounded-xl border border-slate-200 p-3 bg-white/80">
    <div class="font-semibold text-slate-700">Need help?</div>
    <p class="mt-1">Email <a class="underline hover:no-underline" href="mailto:support@neuromedai.org">support@neuromedai.org</a></p>
  </div>
</div>
```
- **Email Infrastructure:**
```python
# myApp/emailer.py - Email sending infrastructure exists
def send_via_resend(to, subject, html_body, text_body=None, reply_to=None):
    """Send email via Resend API"""
    # ... implementation ...
```
- **Current Features:**
  - Email support link: `support@neuromedai.org`
  - Displayed in dashboard sidebar
  - Email sending infrastructure available
- **What exists:**
  - Support email address displayed
  - Help card UI component
  - Email sending backend (`myApp/emailer.py`)
- **What's missing:**
  - Dedicated support page/view
  - Support contact form
  - Support ticket system
  - Support API endpoints
  - Support history/tracking

### ❌ **FAQ — needs FAQView**
- **Status:** ❌ **Not Implemented**
- **What exists:** No FAQ page found in the codebase
- **What's needed:**
  - FAQ content
  - FAQView implementation
  - FAQ page template

### ❌ **User Guide — needs UserGuideView**
- **Status:** ❌ **Not Implemented**
- **What exists:** No user guide found in the codebase
- **What's needed:**
  - User guide content
  - UserGuideView implementation
  - User guide page template

### ❌ **Video Tutorials — needs VideoTutorialsView**
- **Status:** ❌ **Not Implemented**
- **What exists:** No video tutorials found in the codebase
- **What's needed:**
  - Video content/links
  - VideoTutorialsView implementation
  - Video tutorial page template

### ⚠️ **Email Support — needs EmailSupportView**
- **Status:** ⚠️ **Email Address Only**
- **Location:** 
  - Dashboard sidebar help card (`myApp/templates/dashboard/_sidebar.html` line 103)
  - Email: `support@neuromedai.org`
- **What exists:**
  - Support email address displayed
  - Email sending infrastructure (`myApp/emailer.py` - `send_via_resend()`)
- **What's missing:**
  - Support contact form
  - EmailSupportView implementation
  - Support ticket submission

### ❌ **Live Chat — needs LiveChatView**
- **Status:** ❌ **Not Implemented**
- **What exists:** 
  - AI chat system exists (`/api/send-chat/`)
  - Chat sessions management
- **What's missing:**
  - Human support chat
  - Live chat widget
  - LiveChatView implementation
  - Real-time chat infrastructure (WebSockets)

### ✅ **HIPAA Info — needs HIPAAInfoView**
- **Status:** ✅ **Fully Implemented**
- **Location:**
  - `/trust` - Trust & Privacy page (`myApp/templates/trust_privacy.html`)
- **Template Structure:**
```html
<!-- myApp/templates/trust_privacy.html -->
<section id="legal" class="bg-white border nm-card p-5 mb-5">
  <h2 class="text-xl font-semibold flex items-center gap-2">
    <i class="fa-solid fa-scale-balanced text-[#236092]" aria-hidden="true"></i>
    1. Legal & Compliance Framework
  </h2>
  <ul class="mt-2 list-disc pl-5 space-y-1">
    <li><b>HIPAA (U.S.)</b>: Safeguards for Protected Health Information (PHI) across storage, transmission, and access.</li>
    <li><b>GDPR (EU)</b>: Consent, transparency, and user rights (access, deletion, portability).</li>
  </ul>
</section>

<section id="security" class="bg-white border nm-card p-5 mb-5">
  <h2 class="text-xl font-semibold flex items-center gap-2">
    <i class="fa-solid fa-lock text-[#236092]" aria-hidden="true"></i>
    2. Data Security Architecture
  </h2>
  <div class="mt-2 grid sm:grid-cols-2 gap-4">
    <div>
      <h3 class="font-medium">Encryption</h3>
      <ul class="list-disc pl-5 text-sm space-y-1">
        <li>AES-256 at rest</li>
        <li>TLS 1.3+ in transit</li>
      </ul>
    </div>
    <div>
      <h3 class="font-medium">Access Controls</h3>
      <ul class="list-disc pl-5 text-sm space-y-1">
        <li>Role-based access (RBAC)</li>
        <li>Multi-factor authentication (MFA)</li>
      </ul>
    </div>
  </div>
</section>
```
- **Features:**
  - Comprehensive trust & privacy information
  - HIPAA compliance information
  - Data security architecture
  - Legal & compliance framework
  - Consent & transparency
  - Operational safeguards
  - Technical best practices for AI
  - User trust features
- **Content Sections:**
  1. Legal & Compliance Framework (HIPAA, GDPR)
  2. Data Security Architecture (Encryption, Access Controls, Data Minimization)
  3. Consent & Transparency (Explicit consent, Audit trails, Right to be forgotten)
  4. Operational Safeguards (BAAs, Incident response, Regular audits)
  5. Technical Best Practices for AI (Model training, Output validation, Bias mitigation)
  6. User Trust Features (Transparency, Control, Communication)
- **Navigation:**
  - Table of contents with anchor links
  - Quick navigation sidebar
  - Print-friendly styling
  - Mobile-responsive design
- **Note:** HIPAA information is part of the Trust & Privacy page, not a separate dedicated view

---

## Summary

### ✅ Fully Implemented (5)
1. HomeView / Dashboard
2. Language Selection (integrated)
3. Privacy Policy
4. Terms of Service
5. HIPAA Info

### ⚠️ Partially Implemented (4)
1. SettingsView (missing profile picture upload)
2. Edit Profile Picture (UI placeholder only)
3. Export My Data (staff-only, no user-facing export)
4. SupportView (email only, no dedicated page)
5. Email Support (email address only, no form)

### ❌ Not Implemented (7)
1. NotificationsView
2. BackendDebugView
3. FAQView
4. UserGuideView
5. VideoTutorialsView
6. LiveChatView

---

## Complete API Endpoints Reference

### User Settings Endpoints

#### GET /api/user/settings/
**Description:** Get current user's settings/profile information  
**Authentication:** Required (Session-based for web, Token-based for mobile)  
**Request:**
```http
GET /api/user/settings/
Headers:
  Accept: application/json
  Cookie: sessionid=... (for web)
  Authorization: Token <token> (for mobile)
```
**Response (200 OK):**
```json
{
  "display_name": "Maria Gregory",
  "profession": "Healthcare Advocate",
  "language": "en-US"
}
```
**Mobile API Response:**
```json
{
  "id": 1,
  "username": "mariag",
  "email": "maria@example.com",
  "first_name": "Maria",
  "last_name": "Gregory",
  "date_joined": "2025-01-15T10:30:00Z",
  "last_login": "2025-01-20T14:22:00Z"
}
```

#### POST /api/user/settings/update/
**Description:** Update user settings/profile  
**Authentication:** Required  
**Request:**
```http
POST /api/user/settings/update/
Content-Type: application/json
Headers:
  X-CSRFToken: <token> (for web)
  Authorization: Token <token> (for mobile)

Body:
{
  "display_name": "Maria Gregory",
  "profession": "Healthcare Advocate",
  "language": "es-ES"
}
```
**Response (200 OK):**
```json
{
  "status": "success"
}
```
**Mobile API Response:**
```json
{
  "id": 1,
  "username": "mariag",
  "email": "maria@example.com",
  "first_name": "Maria",
  "last_name": "Gregory",
  "date_joined": "2025-01-15T10:30:00Z",
  "last_login": "2025-01-20T14:22:00Z"
}
```

### Legal Pages Endpoints

#### GET /privacy/
**Description:** Redirects to privacy policy section  
**Authentication:** Not required  
**Response:** HTTP 302 Redirect to `/legal/#privacy`

#### GET /terms/
**Description:** Redirects to terms of service section  
**Authentication:** Not required  
**Response:** HTTP 302 Redirect to `/legal/#terms`

#### GET /legal/
**Description:** Combined Terms of Use & Privacy Policy page  
**Authentication:** Not required  
**Response:** HTML page with full legal content

#### GET /trust
**Description:** Trust & Privacy page (includes HIPAA information)  
**Authentication:** Not required  
**Response:** HTML page with comprehensive trust/privacy/HIPAA information

### Export Endpoints (Staff Only)

#### GET /dashboard/analytics/export/
**Description:** Export analytics data as CSV or PDF  
**Authentication:** Required (Staff only)  
**Query Parameters:**
- `export`: Format type (`csv`, `pdf`, `users_csv`, `users_pdf`)
- `period`: Time period (`today`, `yesterday`, `7d`, `30d`, `custom`)
- `start`: Start date (YYYY-MM-DD, for custom period)
- `end`: End date (YYYY-MM-DD, for custom period)

**Request:**
```http
GET /dashboard/analytics/export/?export=csv&period=7d
```

**Response:**
- CSV: `Content-Type: text/csv` with CSV file download
- PDF: `Content-Type: application/pdf` with PDF file download

**Error Response (403 Forbidden):**
```
You do not have permission to export analytics.
```

### Dashboard Endpoints

#### GET /dashboard/
**Description:** Main dashboard page  
**Authentication:** Required  
**Query Parameters:**
- `care_setting`: Filter by care setting (`hospital`, `ambulatory`, `urgent`)

**Response:** HTML dashboard page

#### GET /dashboard/new/
**Description:** Premium dashboard page  
**Authentication:** Required  
**Query Parameters:**
- `care_setting`: Filter by care setting

**Response:** HTML premium dashboard page

### Chat Endpoints

#### POST /api/send-chat/
**Description:** Send chat message to AI assistant  
**Authentication:** Required  
**Request:**
```http
POST /api/send-chat/
Content-Type: multipart/form-data

Fields:
- message: string (optional)
- tone: string (PlainClinical, Caregiver, Faith, Clinical, Geriatric, EmotionalSupport)
- lang: string (language code, e.g., "en-US")
- care_setting: string (hospital, ambulatory, urgent) - optional
- faith_setting: string (general, christian, muslim, hindu, buddhist, jewish) - optional
- files[]: File[] (optional) - PDF, images, documents
```

**Response (200 OK):**
```json
{
  "reply": "AI response text",
  "session_id": 123
}
```

#### GET /api/chat/sessions/
**Description:** List user's chat sessions  
**Authentication:** Required  
**Response:**
```json
[
  {
    "id": 1,
    "title": "Headache consultation",
    "tone": "PlainClinical",
    "lang": "en-US",
    "created_at": "2025-01-20T10:00:00Z",
    "updated_at": "2025-01-20T10:15:00Z",
    "archived": false,
    "messages": [...]
  }
]
```

#### POST /api/chat/sessions/new/
**Description:** Create new chat session  
**Authentication:** Required  
**Response:**
```json
{
  "id": 123,
  "title": "New chat",
  "created_at": "2025-01-20T10:00:00Z"
}
```

### Mobile API Endpoints (Token-based)

#### GET /api/config/
**Description:** Get API configuration (public)  
**Authentication:** Not required  
**Response:**
```json
{
  "api_version": "1.0",
  "base_url": "http://localhost:8000/api/",
  "features": {
    "signup": true,
    "login": true,
    "chat": true,
    "summarize": true
  }
}
```

#### POST /api/login/
**Description:** User login (mobile API)  
**Authentication:** Not required  
**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
**Response (200 OK):**
```json
{
  "id": 1,
  "username": "user",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-01-15T10:30:00Z",
  "last_login": "2025-01-20T14:22:00Z",
  "token": "abc123def456..."
}
```

#### POST /api/signup/
**Description:** User registration (mobile API)  
**Authentication:** Not required  
**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "language": "en-US"
}
```
**Response (200 OK):**
```json
{
  "id": 1,
  "username": "john",
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "date_joined": "2025-01-20T14:22:00Z",
  "last_login": null,
  "token": "abc123def456..."
}
```

#### GET /api/auth/status/
**Description:** Check authentication status  
**Authentication:** Optional (returns different data if authenticated)  
**Response (Authenticated):**
```json
{
  "authenticated": true,
  "user": {
    "id": 1,
    "username": "user",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "status": "ok",
  "time": "2025-01-20T14:22:00Z"
}
```
**Response (Not Authenticated):**
```json
{
  "authenticated": false,
  "status": "ok",
  "time": "2025-01-20T14:22:00Z"
}
```

---

## Database Models Reference

### Profile Model
```python
# myApp/models.py lines 94-129
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    profession = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        default='en-US'
    )
    signup_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    signup_country = models.CharField(max_length=2, blank=True, null=True)
    last_login_country = models.CharField(max_length=2, blank=True, null=True)
    personal_referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='referrals'
    )
```

### ChatSession Model
```python
# myApp/models.py lines 132-145
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    messages = models.JSONField(default=list)  # [{role, content, ts, meta?}]
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=200, blank=True, default="")
    tone = models.CharField(max_length=50, blank=True, default="PlainClinical")
    lang = models.CharField(max_length=10, blank=True, default="en-US")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']
```

### MedicalSummary Model
```python
# myApp/models.py lines 69-86
class MedicalSummary(models.Model):
    CARE_CHOICES = [
        ("hospital", "Hospital/Discharge"),
        ("ambulatory", "Ambulatory/Clinic"),
        ("urgent", "Urgent Care"),
    ]
    care_setting = models.CharField(
        max_length=16, choices=CARE_CHOICES, default="hospital", db_index=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="summaries")
    uploaded_filename = models.CharField(max_length=255)
    tone = models.CharField(max_length=50)
    raw_text = models.TextField()
    summary = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
```

## Data Structures

### User Payload Format (Mobile API)
```python
# mobile_api/compat_views.py lines 18-28
def user_payload(user):
    """User payload matching frontend User model expectations"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }
```

### Chat Message Format
```python
# Chat message structure in ChatSession.messages
{
    "role": "user" | "assistant" | "system",
    "content": "Message text content",
    "ts": "2025-01-20T10:00:00Z",  # ISO 8601 timestamp
    "meta": {  # Optional metadata
        "context": "files",
        "tone": "PlainClinical",
        "lang": "en-US"
    }
}
```

### Language Choices (Complete List)
```python
# myApp/models.py lines 6-67
LANGUAGE_CHOICES = [
    ('en-US', 'English'),
    ('ja-JP', 'Japanese'),
    ('es-ES', 'Spanish'),
    ('fr-FR', 'French'),
    ('de-DE', 'German'),
    ('it-IT', 'Italian'),
    ('pt-PT', 'Portuguese (Portugal)'),
    ('pt-BR', 'Portuguese (Brazil)'),
    ('ru-RU', 'Russian'),
    ('zh-CN', 'Chinese (Simplified)'),
    ('zh-TW', 'Chinese (Traditional)'),
    ('ko-KR', 'Korean'),
    ('ar-SA', 'Arabic (Saudi Arabia)'),
    # ... 40+ more languages
]
```

## Notes

1. **Language Selection:** While fully functional, it's integrated into the dashboard rather than being a separate view
2. **Privacy/Terms:** Combined into a single legal page rather than separate views
3. **HIPAA Info:** Part of the Trust & Privacy page, not a separate view
4. **Profile Picture:** UI placeholder exists but no backend implementation
5. **Export Data:** Only available for staff users, not regular users
6. **Support:** Email address exists but no support form or dedicated page
7. **Mobile API:** Uses token-based authentication (`TokenAuthentication`) while web uses session-based
8. **Data Format:** Mobile API returns ISO 8601 timestamps, snake_case field names
9. **Error Handling:** All endpoints return appropriate HTTP status codes (200, 400, 401, 403, 500)
10. **CORS:** Mobile API has CORS enabled for cross-origin requests

