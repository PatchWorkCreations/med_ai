# Making Google OAuth Public - Deployment Guide

This guide explains how to configure your Google OAuth app to allow public users to sign in.

## 🎯 Overview

By default, Google OAuth apps are in "Testing" mode and only allow specific test users. To allow **anyone** to use your app, you need to:

1. Configure the OAuth Consent Screen
2. Add your production domain
3. Publish the app (make it public)
4. Verify your domain (if required)

---

## Step 1: Configure OAuth Consent Screen

### 1.1 Go to OAuth Consent Screen

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **NeuroMedAI**
3. Navigate to **APIs & Services** → **OAuth consent screen**

### 1.2 Choose User Type

- **External** (for public users) ✅ **Select this**
- Internal (only for Google Workspace users)

Click **Create** or **Edit App**

### 1.3 Fill in App Information

**App name:**
```
NeuroMed AI
```

**User support email:**
```
Your email address (e.g., hello@neuromedai.org)
```

**App logo (optional):**
- Upload your NeuroMed AI logo if you have one

**App domain:**
```
neuromedai.org
```

**Application home page:**
```
https://neuromedai.org
```

**Application privacy policy link:**
```
https://neuromedai.org/privacy
```

**Application terms of service link:**
```
https://neuromedai.org/terms
```

**Authorized domains:**
```
neuromedai.org
```

**Developer contact information:**
```
Your email address
```

Click **Save and Continue**

---

## Step 2: Configure Scopes

### 2.1 Add Scopes

You'll see a list of scopes. Make sure these are added:

- ✅ `email` - See your primary Google Account email address
- ✅ `profile` - See your personal info, including any personal info you've made publicly available
- ✅ `openid` - Associate you with your personal info on Google

**Note:** These scopes are usually added automatically. If not, click **Add or Remove Scopes** and add them.

Click **Save and Continue**

---

## Step 3: Add Test Users (Testing Phase)

### 3.1 Add Test Users (Optional - for Testing)

While in "Testing" mode, you can add specific test users:

1. Click **Add Users**
2. Add email addresses of people who can test the app
3. Click **Add**

**Note:** In Testing mode, only these users can sign in. Skip this if you want to go straight to public.

Click **Save and Continue**

---

## Step 4: Review and Publish

### 4.1 Review Summary

Review all the information you've entered:
- App information ✅
- Scopes ✅
- Test users (if any) ✅

### 4.2 Publish the App (Make it Public)

**Important:** To allow **anyone** to use your app:

1. Click **Back to Dashboard**
2. At the top of the OAuth consent screen, you'll see:
   - **Publishing status:** Testing
   - **Publish App** button

3. Click **Publish App**

4. You'll see a warning:
   > "Your app will be available to any user with a Google Account"

5. Click **Confirm**

### 4.3 App Verification (May Be Required)

Google may require app verification if:
- You're requesting sensitive scopes
- Your app has a high number of users
- Your app is flagged for review

**If verification is required:**
- You'll see a banner saying "App verification required"
- Click **Start Verification**
- Follow Google's verification process
- This can take a few days to weeks

**If verification is NOT required:**
- Your app is immediately available to all users! ✅

---

## Step 5: Update OAuth Credentials

### 5.1 Verify Authorized Domains

1. Go to **APIs & Services** → **Credentials**
2. Click on your OAuth 2.0 Client ID
3. Verify these are set correctly:

**Authorized JavaScript origins:**
```
http://localhost:8000
http://127.0.0.1:8000
https://neuromedai.org
https://medai-production-21ae.up.railway.app
```

**Authorized redirect URIs:**
```
http://localhost:8000/auth/google/callback/
http://127.0.0.1:8000/auth/google/callback/
https://neuromedai.org/auth/google/callback/
https://medai-production-21ae.up.railway.app/auth/google/callback/
```

4. Click **Save**

---

## Step 6: Domain Verification (If Required)

### 6.1 Verify Your Domain

If Google requires domain verification:

1. Go to **APIs & Services** → **OAuth consent screen**
2. Under **Authorized domains**, you'll see your domain
3. If it shows "Not verified", click **Verify domain**
4. Follow Google's domain verification steps:
   - Add a TXT record to your DNS
   - Or upload an HTML file to your website
   - Or add a meta tag to your homepage

**For neuromedai.org:**
- Add the TXT record to your DNS provider
- Wait for DNS propagation (can take up to 48 hours)
- Google will verify automatically

---

## Step 7: Test Public Access

### 7.1 Test with Different Google Accounts

1. **Before Publishing:**
   - Only test users can sign in
   - Others will see: "This app isn't verified"

2. **After Publishing:**
   - Anyone with a Google account can sign in
   - They'll see the consent screen
   - After accepting, they can use your app

### 7.2 Test Flow

1. Go to: `https://neuromedai.org/signup/`
2. Click **Continue with Google**
3. Sign in with any Google account (not just test users)
4. Should redirect back to your app ✅

---

## Common Issues & Solutions

### Issue: "This app isn't verified"

**Solution:**
- Publish the app (Step 4.2)
- If still showing, complete app verification (Step 4.3)

### Issue: "Access blocked: This app's request is invalid"

**Solution:**
- Check redirect URIs match exactly (including trailing slash)
- Verify authorized domains are correct
- Make sure you're using HTTPS in production

### Issue: "Error 400: redirect_uri_mismatch"

**Solution:**
- The redirect URI in your code doesn't match Google Console
- Check `myApp/views.py` - `google_oauth_callback` function
- Verify redirect URI in Google Console matches exactly

### Issue: Domain verification pending

**Solution:**
- Wait for DNS propagation (up to 48 hours)
- Check DNS records are correct
- Try alternative verification method (HTML file or meta tag)

---

## Production Checklist

Before going live, verify:

- [ ] OAuth consent screen configured
- [ ] App published (not in Testing mode)
- [ ] Authorized domains added
- [ ] Redirect URIs configured correctly
- [ ] Domain verified (if required)
- [ ] Environment variables set in production:
  - `GOOGLE_OAUTH_CLIENT_ID`
  - `GOOGLE_OAUTH_CLIENT_SECRET`
- [ ] Tested with multiple Google accounts
- [ ] Privacy policy and Terms of Service links work

---

## Security Best Practices

1. **Keep Client Secret Secure**
   - Never commit to Git
   - Store in environment variables only
   - Rotate if compromised

2. **Use HTTPS in Production**
   - Required for OAuth
   - Update redirect URIs to use `https://`

3. **Monitor Usage**
   - Check Google Cloud Console for OAuth usage
   - Set up alerts for unusual activity

4. **Regular Reviews**
   - Review OAuth scopes periodically
   - Remove unused scopes
   - Keep app information updated

---

## Quick Reference

**OAuth Consent Screen:**
- URL: `https://console.cloud.google.com/apis/credentials/consent`
- Status: Should show "Published" (not "Testing")

**OAuth Credentials:**
- URL: `https://console.cloud.google.com/apis/credentials`
- Check: Authorized domains and redirect URIs

**App Status:**
- Testing = Only test users can access
- Published = Anyone with Google account can access
- Verification Required = May need additional steps

---

## Support

If you encounter issues:

1. Check Google Cloud Console for error messages
2. Review OAuth consent screen configuration
3. Verify domain and redirect URIs
4. Check Google's OAuth documentation: https://developers.google.com/identity/protocols/oauth2

---

**Note:** After publishing, it may take a few minutes to a few hours for changes to propagate globally.

