# Google OAuth Verification Fixes - Homepage Requirements

Based on: [Google OAuth App Homepage Requirements](https://support.google.com/cloud/answer/13807376)

## Issues to Fix

1. ✅ **Homepage domain verification** - Need to verify domain ownership
2. ✅ **Privacy policy link** - Added to landing page

## What I've Added to Landing Page

### 1. Privacy Policy Link
- ✅ Added prominent privacy policy link in footer
- ✅ Added privacy policy link in hero section
- ✅ Links to `/privacy` which should match your OAuth consent screen

### 2. App Purpose & Google Data Usage
- ✅ Added "About NeuroMed Aira" section explaining app functionality
- ✅ Added "How We Use Google Account Information" section
- ✅ Clearly explains:
  - What data is collected (email, name, profile)
  - Why it's collected (account creation, personalization, support)
  - How it's used (not shared with third parties, secure storage)
  - Purpose (medical document summarization)

### 3. Footer Section
- ✅ Privacy Policy link (prominently displayed)
- ✅ Terms of Use link
- ✅ About link
- ✅ Copyright notice

## Domain Verification Steps

### Step 1: Verify Domain in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **OAuth consent screen**
3. Scroll to **Authorized domains** section
4. Click **Add Domain** or **Verify Domain**
5. Enter: `neuromedai.org`
6. Follow Google's verification instructions

### Step 2: Domain Verification Methods

Google will provide one of these methods:

**Option A: DNS TXT Record (Recommended)**
1. Google will provide a TXT record value
2. Add it to your DNS provider:
   - Go to your domain registrar (where you bought neuromedai.org)
   - Add DNS TXT record:
     - Name: `@` or `neuromedai.org`
     - Value: (provided by Google)
     - TTL: 3600 (or default)
3. Wait for DNS propagation (can take up to 48 hours)
4. Click "Verify" in Google Console

**Option B: HTML File Upload**
1. Download the HTML file from Google
2. Upload it to your website root: `https://www.neuromedai.org/google-verification.html`
3. Make sure it's publicly accessible
4. Click "Verify" in Google Console

**Option C: HTML Meta Tag**
1. Google provides a meta tag
2. Add it to your landing page `<head>` section
3. Click "Verify" in Google Console

### Step 3: Verify Homepage URL Matches

1. In OAuth consent screen, ensure:
   - **Application home page:** `https://www.neuromedai.org` or `https://neuromedai.org`
   - **Privacy policy link:** `https://www.neuromedai.org/privacy` or `https://neuromedai.org/privacy`
   - **Terms of service link:** `https://www.neuromedai.org/terms` or `https://neuromedai.org/terms`

2. Make sure these URLs:
   - Are accessible without login
   - Match exactly (www or non-www) with what's in Google Console
   - Don't redirect to different domains

## Homepage Requirements Checklist

Based on [Google's requirements](https://support.google.com/cloud/answer/13807376):

- [x] **Accurately represent and identify your app or brand** ✅
- [x] **Fully describe your app's functionality** ✅ (Added in footer)
- [x] **Explain with transparency the purpose for which your app requests user data** ✅ (Added Google data usage section)
- [x] **Hosted on a verified domain you own** ⚠️ (Need to verify domain)
- [x] **Include a link to your privacy policy** ✅ (Added in footer and hero)
- [x] **Visible to users without requiring them to log-in** ✅ (Landing page is public)

## Next Steps

### 1. Verify Domain Ownership

1. Go to Google Cloud Console → OAuth consent screen
2. Add `neuromedai.org` to Authorized domains
3. Follow verification steps (DNS TXT record recommended)
4. Wait for verification (up to 48 hours)

### 2. Update OAuth Consent Screen

1. Go to OAuth consent screen
2. Verify these URLs match your actual pages:
   - Homepage: `https://www.neuromedai.org` (or `https://neuromedai.org`)
   - Privacy Policy: `https://www.neuromedai.org/privacy`
   - Terms of Service: `https://www.neuromedai.org/terms`

### 3. Test Homepage

1. Visit `https://www.neuromedai.org` in incognito mode
2. Verify:
   - ✅ Page loads without login
   - ✅ Privacy Policy link is visible
   - ✅ App purpose is explained
   - ✅ Google data usage is explained
   - ✅ Links work correctly

### 4. Resubmit for Verification

1. After domain is verified
2. After homepage has all required elements
3. Go to OAuth consent screen
4. Click **Prepare for verification**
5. Review all information
6. Click **Submit for verification**

## Common Issues & Solutions

### Issue: "Homepage is not registered to you"

**Solution:**
- Verify domain ownership in Google Cloud Console
- Add DNS TXT record or upload HTML file
- Wait for verification (can take up to 48 hours)

### Issue: "Homepage does not include privacy policy link"

**Solution:**
- ✅ Fixed: Added privacy policy link in footer and hero section
- Verify link works: `https://www.neuromedai.org/privacy`
- Make sure link matches what's in OAuth consent screen

### Issue: "Homepage does not explain app functionality"

**Solution:**
- ✅ Fixed: Added "About NeuroMed Aira" section
- ✅ Fixed: Added "How We Use Google Account Information" section
- Both sections clearly explain app purpose and data usage

### Issue: "Homepage redirects to different domain"

**Solution:**
- Ensure `www.neuromedai.org` doesn't redirect to `neuromedai.org` (or vice versa)
- Use the same domain in OAuth consent screen as your actual homepage
- Make sure no redirects interfere

## Verification Checklist

Before resubmitting:

- [ ] Domain `neuromedai.org` is verified in Google Cloud Console
- [ ] Homepage (`https://www.neuromedai.org`) is accessible without login
- [ ] Privacy Policy link is visible and works
- [ ] App purpose is clearly explained
- [ ] Google data usage is transparently explained
- [ ] OAuth consent screen URLs match actual pages
- [ ] No redirects to different domains
- [ ] All links work correctly

## After Verification

Once Google verifies:

1. You'll receive an email confirmation
2. OAuth consent screen status will change to "Published"
3. You can enable Google OAuth in production:
   ```bash
   GOOGLE_OAUTH_ENABLED=true
   ```
4. Users can sign in with Google

## Resources

- [App Homepage Requirements](https://support.google.com/cloud/answer/13807376)
- [Domain Verification Guide](https://support.google.com/cloud/answer/9110914)
- [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)


