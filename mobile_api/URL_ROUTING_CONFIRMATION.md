# URL Routing Confirmation - mobile_api

**Date:** January 6, 2026  
**Status:** ✅ Confirmed - All routes use mobile_api views

---

## ✅ CONFIRMATION: We ARE Using mobile_api

### Views Location
- **All views are in:** `mobile_api/views.py` ✅
- **All functions are:** `mobile_api.views.*` ✅

### URL Routing
- **Main routes defined in:** `myProject/urls.py` ✅
- **All routes point to:** `mobile_api.views.*` ✅
- **Internal URL patterns:** `mobile_api/urls.py` (for reference only, not used directly)

---

## 📍 Route Definitions

### File: `myProject/urls.py`

```python
# iOS API routes - direct access at /api/ prefix for iOS app
# These routes override/complement existing routes for iOS compatibility
from mobile_api import views as mobile_views  # ← Using mobile_api views
urlpatterns += [
    # Auth endpoints
    path('api/login/', mobile_views.login, name='mobile_api_login'),
    path('api/signup/', mobile_views.signup, name='mobile_api_signup'),
    path('api/auth/status/', mobile_views.auth_status, name='mobile_api_auth_status'),
    
    # User endpoints
    path('api/user/settings/', mobile_views.user_settings, name='mobile_api_user_settings'),
    path('api/user/settings/update/', mobile_views.user_settings_update, name='mobile_api_user_settings_update'),
    path('api/user/preferences/', mobile_views.user_preferences, name='mobile_api_user_preferences'),
    path('api/user/preferences/update/', mobile_views.user_preferences_update, name='mobile_api_user_preferences_update'),
    
    # Chat endpoints
    path('api/chat/sessions/', mobile_views.chat_sessions, name='mobile_api_chat_sessions'),
    path('api/chat/sessions/new/', mobile_views.create_chat_session, name='mobile_api_create_session'),
    path('api/chat/clear-session/', mobile_views.clear_session, name='mobile_api_clear_session'),
    path('api/send-chat/', mobile_views.send_chat, name='mobile_api_send_chat'),
    
    # Tone management
    path('api/tones/', mobile_views.tones, name='mobile_api_tones'),
    path('api/tones/<str:tone_id>/', mobile_views.tone_detail, name='mobile_api_tone_detail'),
    
    # Medical summaries
    path('api/summarize/', mobile_views.summarize, name='mobile_api_summarize'),
    
    # App configuration
    path('api/config/', mobile_views.config, name='mobile_api_config'),
]
```

**✅ All routes use `mobile_views.*` which is `mobile_api.views.*`**

---

## ⚠️ Potential URL Conflict

### Conflict with myApp/urls.py

**myApp/urls.py has:**
```python
path('api/login/', views.api_login, name='api_login'),
```

**Our mobile_api route:**
```python
path('api/login/', mobile_views.login, name='mobile_api_login'),
```

### Resolution

Django processes URLs in order. Since `myProject/urls.py` includes `myApp.urls` FIRST:

```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include("myApp.urls")),  # ← myApp routes processed first
]

# Then our mobile_api routes are added AFTER
urlpatterns += [
    path('api/login/', mobile_views.login, ...),  # ← This will match first for /api/login/
]
```

**However:** Since both routes have the same pattern `api/login/`, Django will use the **FIRST match** it finds. This means `myApp.urls` route will be matched first, NOT our mobile_api route.

### Solution Options

**Option 1: Remove conflicting route from myApp/urls.py** (Recommended)
- Remove or comment out `path('api/login/', views.api_login, ...)` from `myApp/urls.py`
- This ensures our mobile_api route is used

**Option 2: Use different URL pattern**
- Change mobile_api route to something like `api/mobile/login/`
- But this doesn't match iOS expectations

**Option 3: Reorder URLs** (Not recommended)
- Put mobile_api routes BEFORE myApp.urls
- But this might break existing web app functionality

### Recommended Action

**Check if `myApp/urls.py` route is still needed:**
- If the web app uses `api/login/`, we need to decide which one to keep
- If mobile_api is the primary API, remove the myApp route
- If both are needed, use different URL patterns

---

## ✅ All Other Routes Are Safe

All other routes (`/api/signup/`, `/api/chat/sessions/`, etc.) don't have conflicts because:
- They don't exist in `myApp/urls.py`
- They're unique to mobile_api
- They will work correctly

---

## 📋 Complete View Function List

All functions in `mobile_api/views.py`:

1. ✅ `health()` - Health check
2. ✅ `signup()` - User registration
3. ✅ `login()` - User login
4. ✅ `auth_status()` - Auth status check
5. ✅ `user_settings()` - Get user settings
6. ✅ `user_settings_update()` - Update user settings
7. ✅ `user_preferences()` - Get user preferences
8. ✅ `user_preferences_update()` - Update user preferences
9. ✅ `chat_sessions()` - Get all chat sessions
10. ✅ `create_chat_session()` - Create new session
11. ✅ `clear_session()` - Clear chat session
12. ✅ `send_chat()` - Send chat message
13. ✅ `tones()` - Get all tones
14. ✅ `tone_detail()` - Get tone detail
15. ✅ `summarize()` - Summarize text
16. ✅ `config()` - Get app configuration

**All 16 functions are in `mobile_api/views.py` ✅**

---

## 🎯 Summary

**✅ Confirmed:**
- All views are in `mobile_api/views.py`
- All routes in `myProject/urls.py` use `mobile_api.views.*`
- All endpoints are correctly configured

**⚠️ Action Needed:**
- Check for URL conflict with `myApp/urls.py` route `api/login/`
- Decide which route to keep (recommend keeping mobile_api route)

**✅ Everything else is correctly aligned with mobile_api**

