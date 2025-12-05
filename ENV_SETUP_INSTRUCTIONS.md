# Adding Google OAuth to Your .env File

## Quick Steps

1. **Open your `.env` file** (in the project root directory)

2. **Add these two lines** at the end of the file:

```bash
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
```

3. **Replace the placeholder values** with your actual credentials from Google Cloud Console:
   - Download the JSON file from Google Cloud Console
   - Copy the `client_id` value → paste as `GOOGLE_OAUTH_CLIENT_ID`
   - Copy the `client_secret` value → paste as `GOOGLE_OAUTH_CLIENT_SECRET`

4. **Save the .env file**

5. **Restart your Django development server**:
   ```bash
   # Stop the server (Ctrl+C)
   # Then start it again
   python manage.py runserver
   ```

## Example .env File

Your `.env` file should look something like this:

```bash
# Existing variables
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
RESEND_API_KEY=re_...

# Google OAuth (ADD THESE)
GOOGLE_OAUTH_CLIENT_ID=123456789-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-abcdefghijklmnopqrstuvwxyz
```

## Important Notes

- ✅ The `.env` file is already in `.gitignore` (won't be committed)
- ✅ `load_dotenv()` is already called in `settings.py` (line 38)
- ✅ After adding variables, **restart the server** for changes to take effect
- ✅ No quotes needed around the values in .env file
- ✅ No spaces around the `=` sign

## Troubleshooting

**Still getting "Google OAuth is not configured"?**

1. Check that the variable names are **exactly**:
   - `GOOGLE_OAUTH_CLIENT_ID` (all caps, underscores)
   - `GOOGLE_OAUTH_CLIENT_SECRET` (all caps, underscores)

2. Make sure there are **no spaces** around the `=` sign:
   - ✅ Correct: `GOOGLE_OAUTH_CLIENT_ID=value`
   - ❌ Wrong: `GOOGLE_OAUTH_CLIENT_ID = value`

3. **Restart your Django server** after adding the variables

4. Verify the values are correct (no extra quotes, no trailing spaces)

## Testing

After adding the variables and restarting:

1. Go to: `http://localhost:8000/signup/`
2. Click "Continue with Google"
3. You should be redirected to Google's login page (not see the error)

If you still see the error, check the Django console output for any error messages.

