# Quick Fix for redirect_uri_mismatch

## The Issue

Even though:
- ✅ Environment variables are set correctly
- ✅ Google Console has the correct redirect URIs
- ✅ Code looks correct

We're still getting `redirect_uri_mismatch` error.

## Most Likely Cause

The redirect URI being **sent to Google** doesn't match what's in Google Console **exactly**.

## Immediate Solution: Hardcode the Redirect URI

Since we know the exact URI that should be used, let's temporarily hardcode it to eliminate any dynamic generation issues.

### Step 1: Update the Code

In `myApp/views.py`, find the `google_oauth_login` function and replace the redirect URI building logic with:

```python
# Build redirect URI - HARDCODE for production to match Google Console exactly
if settings.DEBUG:
    # Development: dynamic
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    if '?' in redirect_uri:
        redirect_uri = redirect_uri.split('?')[0]
    redirect_uri = redirect_uri.rstrip('/') + '/'
else:
    # Production: HARDCODE to match Google Console exactly
    redirect_uri = "https://www.neuromedai.org/auth/google/callback/"
```

Do the same in `google_oauth_callback` function:

```python
# Build redirect URI - HARDCODE for production
if settings.DEBUG:
    # Development: dynamic
    redirect_uri = request.build_absolute_uri(reverse('google_oauth_callback'))
    if '?' in redirect_uri:
        redirect_uri = redirect_uri.split('?')[0]
    redirect_uri = redirect_uri.rstrip('/') + '/'
else:
    # Production: HARDCODE to match Google Console exactly
    redirect_uri = "https://www.neuromedai.org/auth/google/callback/"
```

### Step 2: Deploy and Test

1. Deploy the updated code
2. Test the OAuth flow
3. Should work immediately

## Why This Works

By hardcoding the exact URI that's in Google Console, we eliminate:
- Host header detection issues
- Proxy/load balancer complications
- Domain normalization problems
- Any dynamic generation bugs

## After It Works

Once it's working, we can:
1. Check the logs to see what was being generated before
2. Fix the dynamic generation if needed
3. Switch back to dynamic (optional)

## Verification

After deploying, the redirect URI sent to Google will be:
```
https://www.neuromedai.org/auth/google/callback/
```

This **exactly matches** what's in your Google Console, so it should work.

