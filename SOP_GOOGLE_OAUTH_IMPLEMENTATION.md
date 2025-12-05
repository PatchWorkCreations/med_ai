# Standard Operating Procedure: Google OAuth "Continue with Google" Implementation

**Version:** 1.0  
**Last Updated:** [Date]  
**Purpose:** Standardized procedure for implementing Google OAuth authentication in Django applications

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Console Setup](#google-cloud-console-setup)
3. [Django Implementation](#django-implementation)
4. [Frontend Integration](#frontend-integration)
5. [Testing Procedures](#testing-procedures)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)
8. [Security Checklist](#security-checklist)

---

## Prerequisites

### Required Knowledge
- Basic understanding of Django framework
- Familiarity with OAuth 2.0 flow
- Access to Google Cloud Console
- Understanding of environment variables

### Required Access
- Google Cloud Console account with project creation permissions
- Django project with admin access
- Production server access (for deployment)

### Required Packages
- Django (4.0+)
- python-dotenv (for environment variable management)
- requests (for OAuth token exchange)

---

## Google Cloud Console Setup

### Step 1: Create or Select Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project** (or select existing)
3. Enter project name
4. Click **Create**

### Step 2: Enable Google+ API

1. Go to **APIs & Services** → **Library**
2. Search for "Google+ API" or "People API"
3. Click **Enable**

**Note:** For basic OAuth (email, profile), enabling APIs is optional but recommended.

### Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**

2. **Choose User Type:**
   - Select **External** (for public users)
   - Click **Create**

3. **App Information:**
   - **App name:** [Your Application Name]
   - **User support email:** [Support Email]
   - **App logo:** (Optional) Upload logo
   - **App domain:** [yourdomain.com]
   - **Application home page:** `https://yourdomain.com`
   - **Application privacy policy link:** `https://yourdomain.com/privacy`
   - **Application terms of service link:** `https://yourdomain.com/terms`
   - **Authorized domains:** `yourdomain.com`
   - **Developer contact information:** [Developer Email]
   - Click **Save and Continue**

4. **Scopes:**
   - Verify these scopes are present:
     - `email` - See primary email address
     - `profile` - See personal info
     - `openid` - Associate with personal info
   - Click **Save and Continue**

5. **Test Users (Optional):**
   - Add test user emails if app is in Testing mode
   - Click **Save and Continue**

6. **Review:**
   - Review all information
   - Click **Back to Dashboard**

7. **Publish App:**
   - Click **Publish App** button
   - Confirm warning message
   - Status should change to "Published"

### Step 4: Create OAuth 2.0 Client ID

1. Navigate to **APIs & Services** → **Credentials**

2. Click **Create Credentials** → **OAuth client ID**

3. **Application type:** Select **Web application**

4. **Name:** Enter descriptive name (e.g., "Web Client")

5. **Authorized JavaScript origins:**
   Add all environments:
   ```
   http://localhost:8000
   http://127.0.0.1:8000
   https://yourdomain.com
   https://your-production-domain.com
   ```

6. **Authorized redirect URIs:**
   Add callback URLs:
   ```
   http://localhost:8000/auth/google/callback/
   http://127.0.0.1:8000/auth/google/callback/
   https://yourdomain.com/auth/google/callback/
   https://your-production-domain.com/auth/google/callback/
   ```

7. Click **Create**

8. **Save Credentials:**
   - Copy **Client ID**
   - Copy **Client Secret**
   - **OR** Click **Download JSON** to get both values
   - Store securely (do not commit to version control)

---

## Django Implementation

### Step 1: Install Required Packages

```bash
pip install python-dotenv requests
```

**Note:** `requests` is usually already installed with Django projects.

### Step 2: Add Environment Variables

1. Open `.env` file in project root

2. Add Google OAuth credentials:
```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

3. Save file

4. Verify `.env` is in `.gitignore`:
```
.env
```

### Step 3: Update Django Settings

1. Open `settings.py`

2. Ensure `python-dotenv` is loaded (usually at top of file):
```python
import os
from dotenv import load_dotenv

load_dotenv()
```

3. Add Google OAuth configuration (at end of settings file):
```python
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
```

### Step 4: Create OAuth Views

1. Open `views.py` (or create `oauth_views.py`)

2. Add imports at top:
```python
import secrets
import uuid
import requests
from urllib.parse import urlencode
from django.http import HttpResponseRedirect, HttpResponseBadRequest
from django.contrib.auth import login, get_user_model
from django.urls import reverse
from django.conf import settings
from django.db import transaction

User = get_user_model()
```

3. Add OAuth initiation view:
```python
def google_oauth_login(request):
    """
    Initiates Google OAuth flow by redirecting to Google's authorization page.
    """
    google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
    if not google_client_id:
        return HttpResponseBadRequest("Google OAuth is not configured.")
    
    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['google_oauth_state'] = state
    request.session['google_oauth_next'] = request.GET.get('next', '/dashboard/')
    
    # Build Google OAuth URL
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    params = {
        'client_id': google_client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return HttpResponseRedirect(auth_url)
```

4. Add OAuth callback view:
```python
def google_oauth_callback(request):
    """
    Handles Google OAuth callback and creates/logs in user.
    """
    # Verify state token
    state = request.GET.get('state')
    stored_state = request.session.pop('google_oauth_state', None)
    next_url = request.session.pop('google_oauth_next', '/dashboard/')
    
    if not state or state != stored_state:
        return HttpResponseBadRequest("Invalid state parameter.")
    
    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error', 'Unknown error')
        return HttpResponseBadRequest(f"OAuth error: {error}")
    
    google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
    google_client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)
    
    if not google_client_id or not google_client_secret:
        return HttpResponseBadRequest("Google OAuth is not configured.")
    
    # Exchange code for access token
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    token_data = {
        'code': code,
        'client_id': google_client_id,
        'client_secret': google_client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    
    try:
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=10
        )
        token_response.raise_for_status()
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        if not access_token:
            return HttpResponseBadRequest("Failed to obtain access token.")
        
        # Get user info from Google
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
        
        email = user_info.get('email')
        if not email:
            return HttpResponseBadRequest("Email not provided by Google.")
        
        # Get or create user
        email_lower = email.lower()
        user = User.objects.filter(email__iexact=email_lower).first()
        created = False
        
        if not user:
            # Create new user
            base_username = email_lower.split('@')[0]
            username = base_username
            # Ensure username is unique
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            user = User.objects.create(
                email=email_lower,
                username=username,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
            )
            created = True
        else:
            # Update existing user info if needed
            if not user.first_name and user_info.get('given_name'):
                user.first_name = user_info.get('given_name')
            if not user.last_name and user_info.get('family_name'):
                user.last_name = user_info.get('family_name')
            user.save()
        
        # Log the user in
        user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, user)
        
        # Redirect to dashboard or next URL
        resp = HttpResponseRedirect(next_url)
        resp.set_cookie("just_logged_in", "1", max_age=60, samesite="Lax", path="/")
        return resp
        
    except requests.RequestException as e:
        import logging
        log = logging.getLogger(__name__)
        log.exception("Google OAuth error")
        return HttpResponseBadRequest(f"OAuth error: {str(e)}")
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.exception("Unexpected error in Google OAuth")
        return HttpResponseBadRequest(f"An error occurred: {str(e)}")
```

### Step 5: Add URL Routes

1. Open `urls.py`

2. Add imports:
```python
from . import views  # or from .oauth_views import google_oauth_login, google_oauth_callback
```

3. Add URL patterns:
```python
urlpatterns = [
    # ... existing patterns ...
    
    # Google OAuth
    path('auth/google/', views.google_oauth_login, name='google_oauth_login'),
    path('auth/google/callback/', views.google_oauth_callback, name='google_oauth_callback'),
]
```

---

## Frontend Integration

### Step 1: Add Button to Signup Page

1. Open signup template (e.g., `templates/signup.html`)

2. Add Google button after the main form:
```html
<!-- Divider -->
<div class="flex items-center my-4">
  <div class="flex-1 border-t border-gray-200"></div>
  <span class="px-4 text-sm text-gray-500">or</span>
  <div class="flex-1 border-t border-gray-200"></div>
</div>

<!-- Google OAuth Button -->
<a href="{% url 'google_oauth_login' %}" class="w-full flex items-center justify-center gap-3 border-2 border-gray-200 hover:border-gray-300 bg-white text-gray-700 font-medium py-2.5 rounded-md shadow-sm transition">
  <svg class="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
  Continue with Google
</a>
```

### Step 2: Add Button to Login Page

1. Open login template (e.g., `templates/login.html`)

2. Add the same Google button code (as above) after the login form

### Step 3: Style Customization

- Adjust colors to match your brand
- Modify button text if needed
- Ensure button is responsive on mobile devices

---

## Testing Procedures

### Local Testing

1. **Start Development Server:**
   ```bash
   python manage.py runserver
   ```

2. **Test Signup Flow:**
   - Navigate to: `http://localhost:8000/signup/`
   - Click "Continue with Google"
   - Should redirect to Google login page
   - Sign in with test Google account
   - Should redirect back and create account

3. **Test Login Flow:**
   - Navigate to: `http://localhost:8000/login/`
   - Click "Continue with Google"
   - Sign in with existing account
   - Should redirect to dashboard

4. **Test Error Handling:**
   - Test with invalid state token (should fail gracefully)
   - Test with missing credentials (should show error)
   - Test with cancelled OAuth (should handle gracefully)

### Production Testing

1. **Verify Environment Variables:**
   - Confirm `GOOGLE_OAUTH_CLIENT_ID` is set
   - Confirm `GOOGLE_OAUTH_CLIENT_SECRET` is set

2. **Test with Multiple Accounts:**
   - Test with different Google accounts
   - Verify user creation works
   - Verify existing users can log in

3. **Test Redirect URIs:**
   - Verify callback URL matches exactly
   - Test on production domain
   - Verify HTTPS is working

---

## Production Deployment

### Step 1: Update Google Cloud Console

1. **Add Production Domains:**
   - Add production domain to Authorized JavaScript origins
   - Add production callback URL to Authorized redirect URIs

2. **Publish App:**
   - Ensure OAuth consent screen is published
   - Verify app is not in Testing mode

### Step 2: Set Production Environment Variables

1. **Add to Production Server:**
   ```bash
   GOOGLE_OAUTH_CLIENT_ID=your-production-client-id
   GOOGLE_OAUTH_CLIENT_SECRET=your-production-client-secret
   ```

2. **Verify Security:**
   - Environment variables are not in code
   - Variables are stored securely
   - Access is restricted

### Step 3: Verify HTTPS

1. **Ensure HTTPS is Enabled:**
   - OAuth requires HTTPS in production
   - Verify SSL certificate is valid
   - Update redirect URIs to use `https://`

### Step 4: Test Production

1. Navigate to production signup/login pages
2. Test Google OAuth flow
3. Verify user creation and login
4. Check error handling

---

## Troubleshooting

### Issue: "Google OAuth is not configured"

**Cause:** Environment variables not set or not loaded

**Solution:**
1. Verify `.env` file exists and has correct variables
2. Check `load_dotenv()` is called in `settings.py`
3. Restart Django server after adding variables
4. Verify variable names match exactly (case-sensitive)

### Issue: "redirect_uri_mismatch"

**Cause:** Redirect URI in code doesn't match Google Console

**Solution:**
1. Check redirect URI in Google Console
2. Verify it matches exactly (including trailing slash)
3. Check protocol (http vs https)
4. Ensure port numbers match

### Issue: "Invalid state parameter"

**Cause:** Session expired or state token mismatch

**Solution:**
1. Check session middleware is enabled
2. Verify cookies are working
3. Try again (state is regenerated each time)

### Issue: "This app isn't verified"

**Cause:** App is in Testing mode or verification required

**Solution:**
1. Publish the app in OAuth consent screen
2. Complete app verification if required
3. Wait for changes to propagate (can take hours)

### Issue: User not created

**Cause:** Email not provided or user creation failed

**Solution:**
1. Check Google scopes include `email`
2. Verify user model allows email as unique identifier
3. Check Django logs for errors
4. Verify database connection

---

## Security Checklist

### Pre-Deployment

- [ ] Client Secret stored in environment variables only
- [ ] `.env` file in `.gitignore`
- [ ] No credentials in code or version control
- [ ] HTTPS enabled in production
- [ ] State token validation implemented
- [ ] Error messages don't expose sensitive info
- [ ] Session security configured correctly

### Post-Deployment

- [ ] OAuth consent screen published
- [ ] Production domains verified
- [ ] Redirect URIs use HTTPS
- [ ] Environment variables set correctly
- [ ] Error logging configured
- [ ] User data handled securely
- [ ] Privacy policy and terms linked

### Ongoing

- [ ] Monitor OAuth usage in Google Console
- [ ] Review and rotate credentials periodically
- [ ] Keep Django and dependencies updated
- [ ] Review OAuth scopes regularly
- [ ] Monitor for security vulnerabilities

---

## Maintenance

### Regular Tasks

1. **Monthly:**
   - Review OAuth usage statistics
   - Check for any security alerts
   - Verify environment variables are secure

2. **Quarterly:**
   - Review and update OAuth scopes
   - Check Google Cloud Console for changes
   - Update documentation if needed

3. **Annually:**
   - Review and rotate credentials if needed
   - Audit security practices
   - Update dependencies

### Documentation Updates

- Update this SOP when procedures change
- Document any project-specific customizations
- Keep troubleshooting section current

---

## Appendix

### Required OAuth Scopes

- `openid` - Basic OpenID Connect
- `email` - User's email address
- `profile` - User's basic profile information

### Google OAuth Endpoints

- Authorization: `https://accounts.google.com/o/oauth2/v2/auth`
- Token Exchange: `https://oauth2.googleapis.com/token`
- User Info: `https://www.googleapis.com/oauth2/v2/userinfo`

### Common Redirect Paths

- Development: `/auth/google/callback/`
- Production: `/auth/google/callback/`

**Note:** Path can be customized but must match in both code and Google Console.

---

**Document Control:**
- **Owner:** Development Team
- **Review Frequency:** Quarterly
- **Approval Required:** Yes (for major changes)

---

**End of SOP**

