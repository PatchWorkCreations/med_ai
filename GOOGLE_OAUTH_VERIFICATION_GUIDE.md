# Google OAuth App Verification Guide

Based on: [Google OAuth App Verification Help Center](https://support.google.com/cloud/answer/13463073)

## Overview

When you publish your OAuth app, Google may require verification if your app uses **sensitive** or **restricted** scopes. Until verification is complete, you can disable Google OAuth in production.

## Current Scopes Used

Your app currently uses these scopes:
- `openid` - Basic OpenID Connect (non-sensitive)
- `email` - User's email address (non-sensitive)
- `profile` - User's basic profile (non-sensitive)

**Good News:** These are all **non-sensitive** scopes, so verification may not be required!

## When Verification is Required

### Sensitive Scopes
- Apps requesting sensitive scopes must complete verification
- Examples: Gmail API, Drive API, Calendar API

### Restricted Scopes
- Apps requesting restricted scopes must complete verification
- Examples: YouTube Data API, Google Cloud Platform APIs

### Your Case
Since you're only using `openid`, `email`, and `profile` (all non-sensitive), verification may not be required. However, Google may still require verification if:
- Your app has a high number of users
- Your app is flagged for review
- You want to display app name/logo on consent screen (requires brand verification)

## Quick Solution: Disable Until Verified

### Step 1: Add Environment Variable

**Local (.env file):**
```bash
GOOGLE_OAUTH_ENABLED=true
```

**Production (Railway environment variables):**
```bash
GOOGLE_OAUTH_ENABLED=false
```

### Step 2: Deploy

The "Continue with Google" button will:
- ✅ Show in local development
- ❌ Hide in production until you set `GOOGLE_OAUTH_ENABLED=true`

## How to Submit for Verification (If Required)

### Step 1: Check OAuth Consent Screen

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Check the status:
   - **Testing** = Only test users can access
   - **Published** = Available to all users (may require verification)
   - **Verification Required** = Must complete verification

### Step 2: Complete App Information

1. **App Information:**
   - App name: Your app name
   - User support email: Your support email
   - App logo: Upload your logo
   - App domain: `neuromedai.org`
   - Application home page: `https://www.neuromedai.org`
   - Privacy policy: `https://www.neuromedai.org/privacy`
   - Terms of service: `https://www.neuromedai.org/terms`
   - Authorized domains: `neuromedai.org`

2. **Scopes:**
   - Verify only necessary scopes are listed
   - Remove any unused scopes

3. **Test Users (if in Testing mode):**
   - Add test user emails
   - Only these users can sign in during testing

### Step 3: Submit for Verification

1. Click **Submit for Verification** (if required)
2. Fill out the verification form:
   - App type
   - Use case description
   - Data access justification
   - Security practices
3. Submit and wait for review (can take days to weeks)

### Step 4: Brand Verification (Optional)

If you only want to display app name/logo (not full verification):
1. Complete basic app information
2. Submit for brand verification (lighter process)
3. Faster approval than full verification

## Verification Requirements

### What You Need

1. **Privacy Policy:**
   - Must be publicly accessible
   - Must explain data collection and use
   - URL: `https://www.neuromedai.org/privacy`

2. **Terms of Service:**
   - Must be publicly accessible
   - URL: `https://www.neuromedai.org/terms`

3. **App Information:**
   - Complete all required fields
   - Accurate descriptions
   - Valid contact information

4. **Security Practices:**
   - Describe how you protect user data
   - Explain data storage and access
   - Outline security measures

### Common Issues

1. **Missing Privacy Policy:**
   - Solution: Create and publish privacy policy
   - Must be accessible at the URL you provide

2. **Incomplete App Information:**
   - Solution: Fill out all required fields
   - Provide accurate descriptions

3. **Unjustified Scope Requests:**
   - Solution: Explain why each scope is needed
   - Remove unnecessary scopes

## After Verification

Once verified:

1. **Enable Google OAuth in Production:**
   ```bash
   GOOGLE_OAUTH_ENABLED=true
   ```

2. **Test the OAuth Flow:**
   - Should work without errors
   - Users can sign in with Google

3. **Monitor Usage:**
   - Check Google Cloud Console for usage stats
   - Monitor for any issues

## Annual Re-Verification

If your app uses **restricted** scopes:
- Must complete re-verification annually
- Google will notify you when it's due

## Current Status

**Your App:**
- Uses non-sensitive scopes only ✅
- May not require full verification
- May only need brand verification (if you want logo/name)

**Action:**
1. Set `GOOGLE_OAUTH_ENABLED=false` in production
2. Test locally with `GOOGLE_OAUTH_ENABLED=true`
3. Submit for verification if required
4. Enable in production after verification

## Resources

- [OAuth App Verification Help Center](https://support.google.com/cloud/answer/13463073)
- [OAuth 2.0 Scopes for Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes)
- [Submitting your app for verification](https://support.google.com/cloud/answer/9110914)

## Quick Reference

**Environment Variables:**
```bash
# Local development
GOOGLE_OAUTH_ENABLED=true

# Production (until verified)
GOOGLE_OAUTH_ENABLED=false

# Production (after verification)
GOOGLE_OAUTH_ENABLED=true
```

**What Happens:**
- `GOOGLE_OAUTH_ENABLED=true` → "Continue with Google" button shows
- `GOOGLE_OAUTH_ENABLED=false` → "Continue with Google" button hidden

