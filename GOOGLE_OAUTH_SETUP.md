# Google OAuth Setup Guide

This guide explains how to configure Google OAuth for NeuroMed Aira signup and login.

## ✅ Implementation Complete

The following has been implemented:
- ✅ Google OAuth login views (`google_oauth_login` and `google_oauth_callback`)
- ✅ OAuth URLs added to `myApp/urls.py`
- ✅ "Continue with Google" buttons added to signup and login pages
- ✅ Settings configuration placeholders added

## 🔧 Configuration Steps

### 1. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **NeuroMedAI**
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Configure:
   - **Application type:** Web application
   - **Name:** NeuroMed Aira
   - **Authorized JavaScript origins:**
     - `http://localhost:8000`
     - `http://127.0.0.1:8000`
     - `https://neuromedai.org`
     - `https://medai-production-21ae.up.railway.app`
   - **Authorized redirect URIs:**
     - `http://localhost:8000/auth/google/callback/`
     - `http://127.0.0.1:8000/auth/google/callback/`
     - `https://neuromedai.org/auth/google/callback/`
     - `https://medai-production-21ae.up.railway.app/auth/google/callback/`
6. Click **Create**
7. Copy the **Client ID** and **Client Secret**

### 2. Add Environment Variables

Add these to your `.env` file (local) and production environment variables:

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
```

### 3. Settings Configuration

The settings are already configured in `myProject/settings.py`:

```python
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
```

Just add the environment variables and you're done!

## 🎯 How It Works

### Signup Flow
1. User clicks "Continue with Google" on signup page
2. Redirected to Google OAuth consent screen
3. User authorizes the app
4. Google redirects back to `/auth/google/callback/`
5. System:
   - Creates new user account (if doesn't exist)
   - Creates user profile
   - Generates referral code (if new user)
   - Sends welcome email (if new user)
   - Logs user in automatically
   - Redirects to dashboard

### Login Flow
1. User clicks "Continue with Google" on login page
2. Same OAuth flow as signup
3. If user exists → logs in
4. If user doesn't exist → creates account and logs in
5. Redirects to dashboard

## 📋 Features

- **Automatic Account Creation:** Creates user account from Google profile
- **Profile Sync:** Updates first/last name from Google profile
- **Referral Code:** New users get referral codes automatically
- **Welcome Email:** New users receive welcome email
- **Analytics Tracking:** Signups tracked in UserSignup model
- **IP/Country Tracking:** Captures signup IP and country
- **CSRF Protection:** Uses state token for security
- **Error Handling:** Graceful error messages

## 🔒 Security

- State token validation prevents CSRF attacks
- Secure token exchange via HTTPS
- Client secret stored in environment variables
- No sensitive data in code

## 🐛 Troubleshooting

### "Google OAuth is not configured"
- Check that `GOOGLE_OAUTH_CLIENT_ID` is set in environment variables
- Restart your Django server after adding environment variables

### "Invalid state parameter"
- This usually means the session expired or was cleared
- Try again - the state token is regenerated each time

### Redirect URI mismatch
- Ensure the redirect URI in Google Console exactly matches:
  - `http://localhost:8000/auth/google/callback/` (local)
  - `https://neuromedai.org/auth/google/callback/` (production)
- Note: Must include trailing slash and exact path

### Email not provided
- User must grant email permission in Google consent screen
- Check OAuth scopes include `email` and `profile`

## 📝 Files Modified

- `myApp/views.py` - Added `google_oauth_login()` and `google_oauth_callback()` functions
- `myApp/urls.py` - Added OAuth routes
- `myProject/settings.py` - Added Google OAuth configuration
- `myApp/templates/signup.html` - Added Google button
- `myApp/templates/login.html` - Added Google button

## 🚀 Next Steps

1. Create OAuth client in Google Cloud Console
2. Add environment variables to `.env` file
3. Test locally: `http://localhost:8000/signup/`
4. Test login: `http://localhost:8000/login/`
5. Deploy to production with environment variables set

---

**Note:** It may take 5 minutes to a few hours for Google OAuth settings to take effect after creation.

