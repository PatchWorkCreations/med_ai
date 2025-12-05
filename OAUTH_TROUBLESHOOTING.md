# OAuth redirect_uri_mismatch Troubleshooting

## Current Status

✅ **Google Console Configuration:**
- Both `https://www.neuromedai.org/auth/google/callback/` ✅
- And `https://neuromedai.org/auth/google/callback/` ✅
- Are registered in Google Cloud Console

✅ **Error Shows:**
- `redirect_uri=https://www.neuromedai.org/auth/google/callback/`
- This matches what's in Google Console

❌ **Still Getting Error:**
- This suggests a deployment or caching issue

## Troubleshooting Steps

### Step 1: Verify Code is Deployed

1. **Check if updated code is live:**
   - The code changes to preserve `www.` need to be deployed
   - Verify the latest code is on production server

2. **Check environment variables:**
   ```bash
   # On production server, verify:
   echo $GOOGLE_OAUTH_CLIENT_ID
   echo $GOOGLE_OAUTH_CLIENT_SECRET
   ```

### Step 2: Clear Caches

1. **Clear browser cache:**
   - Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - Or use incognito/private window

2. **Clear Django cache:**
   ```bash
   python manage.py clear_cache  # If you have this command
   # Or restart the server
   ```

3. **Clear Google's cache:**
   - Try a different browser
   - Try incognito mode
   - Wait 10-15 minutes for Google's cache to clear

### Step 3: Verify Redirect URI Generation

Add temporary logging to see what URI is being generated:

```python
# In google_oauth_login function, after building redirect_uri:
import logging
log = logging.getLogger(__name__)
log.error(f"Generated redirect_uri: {redirect_uri}")
```

Check your production logs to see the exact URI being sent.

### Step 4: Check for Query Parameters

The error might be caused by query parameters being added. Verify:

1. **Check the actual request:**
   - Look at browser Network tab
   - Check the exact URL being sent to Google
   - Ensure no extra query parameters

2. **Verify code removes query params:**
   ```python
   # This should be in your code:
   if '?' in redirect_uri:
       redirect_uri = redirect_uri.split('?')[0]
   ```

### Step 5: Test with Exact Match

1. **Try the exact URI from error:**
   - The error shows: `https://www.neuromedai.org/auth/google/callback/`
   - Verify this EXACT string is in Google Console (character-by-character)

2. **Check for hidden characters:**
   - Copy from Google Console
   - Paste in a text editor
   - Check for any extra spaces or characters

### Step 6: Wait for Propagation

1. **Google changes can take time:**
   - 5 minutes to a few hours
   - If you just added the URI, wait 10-15 minutes

2. **Try again after waiting:**
   - Clear browser cache
   - Try in incognito mode
   - Test again

### Step 7: Verify Domain Configuration

1. **Check DNS/SSL:**
   - Ensure `www.neuromedai.org` resolves correctly
   - Verify SSL certificate is valid
   - Check if there are any redirects happening

2. **Check server configuration:**
   - Ensure server is serving `www.neuromedai.org` correctly
   - No redirects from www to non-www (or vice versa) that might interfere

## Quick Fixes to Try

### Fix 1: Restart Production Server
```bash
# Restart your Django application
# This ensures new code is loaded
```

### Fix 2: Double-Check Google Console
1. Go to Google Cloud Console
2. Click on your OAuth Client ID
3. Verify `https://www.neuromedai.org/auth/google/callback/` is there
4. Click **Save** even if nothing changed (forces refresh)

### Fix 3: Test with Non-WWW First
Temporarily test with `https://neuromedai.org/auth/google/callback/` to see if www is causing issues.

### Fix 4: Check Request Headers
In browser DevTools → Network tab:
- Check the actual request to Google
- Verify the `redirect_uri` parameter
- Ensure it matches exactly

## Common Causes

1. **Code not deployed** - Most common
2. **Browser cache** - Second most common
3. **Google cache** - Can take 10-15 minutes
4. **Hidden characters** - Spaces, special chars in Google Console
5. **Server redirects** - www to non-www redirects interfering
6. **Environment variables** - Wrong client ID/secret

## Verification Checklist

- [ ] Updated code is deployed to production
- [ ] Environment variables are set correctly
- [ ] Google Console has exact URI (checked character-by-character)
- [ ] Browser cache cleared
- [ ] Tried incognito/private window
- [ ] Waited 10-15 minutes after Google Console changes
- [ ] Server restarted after code deployment
- [ ] No server-side redirects interfering
- [ ] SSL certificate is valid for www.neuromedai.org

## Next Steps

1. **Deploy the updated code** (if not already done)
2. **Restart production server**
3. **Wait 10-15 minutes**
4. **Clear browser cache and try again**
5. **Check production logs** for the actual redirect_uri being generated

If still not working after all steps, check the production logs to see what redirect_uri is actually being sent to Google.

