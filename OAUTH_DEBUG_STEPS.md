# Google OAuth redirect_uri_mismatch - Debug Steps

## The Problem

Even though Google Console is configured correctly, we're still getting `redirect_uri_mismatch` error.

## What I Just Fixed

1. **Added X-Forwarded-Host handling** - Railway/proxies might send different host headers
2. **Improved host normalization** - Better handling of www prefix
3. **Added logging** - To see exactly what redirect_uri is being generated

## Critical Steps to Fix This

### Step 1: Deploy the Updated Code

The code now:
- Handles proxy headers (X-Forwarded-Host)
- Better host normalization
- Logs the exact redirect_uri being generated

**Deploy this to production NOW.**

### Step 2: Check Production Logs

After deploying, check your production logs when someone tries to sign in:

Look for this line:
```
Google OAuth redirect_uri: https://www.neuromedai.org/auth/google/callback/
```

**Copy the EXACT redirect_uri from the logs.**

### Step 3: Verify Google Console Match

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Click your OAuth Client ID
3. Check **Authorized redirect URIs**
4. **Compare character-by-character** with the logged redirect_uri

**They must match EXACTLY:**
- Same protocol (`https://`)
- Same domain (`www.neuromedai.org`)
- Same path (`/auth/google/callback/`)
- Same trailing slash (`/` at the end)
- No extra spaces or characters

### Step 4: Common Mismatches to Check

1. **Trailing slash:**
   - ✅ Correct: `https://www.neuromedai.org/auth/google/callback/`
   - ❌ Wrong: `https://www.neuromedai.org/auth/google/callback` (no trailing slash)

2. **www prefix:**
   - ✅ Correct: `https://www.neuromedai.org/auth/google/callback/`
   - ❌ Wrong: `https://neuromedai.org/auth/google/callback/` (no www)

3. **Protocol:**
   - ✅ Correct: `https://`
   - ❌ Wrong: `http://`

4. **Hidden characters:**
   - Check for spaces, tabs, or special characters
   - Copy from logs and paste into Google Console

### Step 5: If Still Not Working

**Option A: Hardcode the Redirect URI (Temporary Fix)**

If the dynamic generation is still causing issues, temporarily hardcode it:

```python
# In google_oauth_login function, replace the redirect_uri building with:
if settings.DEBUG:
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    if '?' in redirect_uri:
        redirect_uri = redirect_uri.split('?')[0]
    redirect_uri = redirect_uri.rstrip('/') + '/'
else:
    # Production: hardcode to match Google Console exactly
    redirect_uri = "https://www.neuromedai.org/auth/google/callback/"
```

**Option B: Check Railway/Proxy Configuration**

If you're using Railway or another proxy:
1. Check if there are any URL rewrites
2. Verify the domain configuration
3. Check if there's a redirect from non-www to www (or vice versa)

### Step 6: Verify in Browser DevTools

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Click "Continue with Google"
4. Find the request to `accounts.google.com`
5. Check the `redirect_uri` parameter in the URL
6. Compare it with Google Console

## Quick Checklist

- [ ] Updated code deployed to production
- [ ] Production server restarted
- [ ] Checked production logs for redirect_uri
- [ ] Compared logged redirect_uri with Google Console (character-by-character)
- [ ] Verified trailing slash matches
- [ ] Verified www prefix matches
- [ ] Verified https protocol
- [ ] Cleared browser cache
- [ ] Tried in incognito window
- [ ] Waited 10-15 minutes after Google Console changes

## Most Likely Issue

Based on the error, the most likely issue is:

1. **Code not deployed** - The updated code with www handling needs to be on production
2. **Host header issue** - Railway/proxy might be sending a different host header
3. **Character mismatch** - There might be a hidden character or space

## Next Action

1. **Deploy the updated code** (with X-Forwarded-Host handling)
2. **Check production logs** to see the exact redirect_uri
3. **Compare with Google Console** character-by-character
4. **Report back** what the logged redirect_uri shows

The logging will tell us exactly what's being sent to Google, which will help us fix the mismatch.

