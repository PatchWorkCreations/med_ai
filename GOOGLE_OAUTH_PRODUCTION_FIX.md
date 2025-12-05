# Google OAuth Production Fix - redirect_uri_mismatch

## Problem

Error: `Error 400: redirect_uri_mismatch`

The redirect URI in production doesn't match what's registered in Google Cloud Console.

## Common Causes

1. **HTTP vs HTTPS mismatch**
   - Production must use `https://`
   - Google Console must have `https://` URLs

2. **www vs non-www mismatch**
   - `www.neuromedai.org` vs `neuromedai.org`
   - Must match exactly in Google Console

3. **Query parameters**
   - Redirect URI shouldn't have query parameters
   - Must be clean: `https://domain.com/auth/google/callback/`

4. **Trailing slash**
   - Must match exactly (with or without trailing slash)
   - Usually: `https://domain.com/auth/google/callback/` (with trailing slash)

## Solution Steps

### Step 1: Check Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Click on your OAuth 2.0 Client ID
4. Check **Authorized redirect URIs**

**Must have exactly:**
```
https://neuromedai.org/auth/google/callback/
https://www.neuromedai.org/auth/google/callback/  (if using www)
```

**Important:**
- Use `https://` (not `http://`)
- Include trailing slash `/`
- No query parameters
- Match domain exactly (www or non-www)

### Step 2: Verify Code Changes

The code has been updated to:
- Force HTTPS in production
- Normalize domain (remove www)
- Remove query parameters
- Ensure trailing slash

### Step 3: Update Google Console (If Needed)

**Option A: If you want to use `neuromedai.org` (no www):**

1. In Google Console, add:
   ```
   https://neuromedai.org/auth/google/callback/
   ```

2. Remove any `www.` versions if not needed

**Option B: If you want to use `www.neuromedai.org`:**

1. In Google Console, add:
   ```
   https://www.neuromedai.org/auth/google/callback/
   ```

2. Update the code to keep `www.` instead of removing it

### Step 4: Test

1. Deploy the updated code
2. Test OAuth flow in production
3. Check browser console for any errors
4. Verify redirect URI in error messages matches Google Console

## Code Changes Made

The redirect URI is now built as:

```python
# Production: always HTTPS, normalized domain, clean URI
redirect_uri = f"https://{host}{callback_path}"
# Result: https://neuromedai.org/auth/google/callback/
```

## Verification Checklist

- [ ] Google Console has exact redirect URI (with trailing slash)
- [ ] Using `https://` (not `http://`)
- [ ] Domain matches (www or non-www)
- [ ] No query parameters in redirect URI
- [ ] Code deployed to production
- [ ] Tested OAuth flow

## If Still Not Working

1. **Check the exact error message:**
   - Look for the `redirect_uri` value in the error
   - Compare it character-by-character with Google Console

2. **Verify domain configuration:**
   - Check if your domain redirects www to non-www (or vice versa)
   - Update Google Console to match your actual domain behavior

3. **Check for proxy/load balancer:**
   - If behind a proxy, the host might be different
   - May need to use `X-Forwarded-Host` header

4. **Wait for propagation:**
   - Google changes can take 5 minutes to a few hours
   - Clear browser cache and try again

## Quick Fix

If you need to match `www.neuromedai.org` instead:

Update the code to keep `www.`:

```python
# In google_oauth_login and google_oauth_callback functions
# Change this line:
if host.startswith('www.'):
    host = host[4:]  # Remove www

# To this (to keep www):
# if not host.startswith('www.'):
#     host = f"www.{host}"  # Add www
```

Then update Google Console to match.

