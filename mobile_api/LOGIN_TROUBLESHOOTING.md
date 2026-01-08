# Login Troubleshooting Guide

**Issue:** Can't log in after recent changes

## Quick Checks

1. **Restart Django Server**
   - The server needs to be restarted after code changes
   - Stop the server (Ctrl+C) and restart it

2. **Check Server Logs**
   - Look for any import errors or syntax errors
   - Check if the module loads correctly

3. **Test Login Endpoint Directly**
   ```bash
   curl -X POST http://localhost:8000/api/login/ \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@gmail.com","password":"admin"}' \
     | jq '.'
   ```

4. **Check URL Routing**
   - Verify `myProject/urls.py` has the login route
   - Make sure mobile_api routes are processed first

## Common Issues

### Issue 1: Module Not Loading
- **Symptom:** Server won't start or shows import errors
- **Fix:** Check for syntax errors in `mobile_api/views.py`
- **Check:** Run `python manage.py check`

### Issue 2: URL Not Found (404)
- **Symptom:** 404 error when calling `/api/login/`
- **Fix:** Verify URL routing in `myProject/urls.py`
- **Check:** Make sure `path('api/login/', mobile_views.login, ...)` exists

### Issue 3: 500 Server Error
- **Symptom:** 500 error when calling `/api/login/`
- **Fix:** Check server logs for the actual error
- **Check:** Look for traceback in Django console

### Issue 4: 401 Unauthorized
- **Symptom:** Login returns 401 even with correct credentials
- **Fix:** Check authentication logic in `mobile_api/views.py` login function
- **Check:** Verify user exists and password is correct

## Current Login Function Location

**File:** `mobile_api/views.py`  
**Function:** `login()` (line 165)  
**Route:** `/api/login/` (defined in `myProject/urls.py` line 13)

## Test Commands

```bash
# Test 1: Check if endpoint exists
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}'

# Test 2: Check with valid credentials
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@gmail.com","password":"admin"}'

# Test 3: Check server status
curl http://localhost:8000/api/config/
```

## Next Steps

1. Check Django server console for errors
2. Verify the server is running
3. Test the login endpoint with curl
4. Check if other endpoints work (e.g., `/api/config/`)

