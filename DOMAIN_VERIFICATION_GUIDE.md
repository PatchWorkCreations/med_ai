# Domain Verification Guide for Google OAuth

Based on: [Google OAuth App Homepage Requirements](https://support.google.com/cloud/answer/13807376)

## Current Status

✅ **Homepage Updated:**
- Privacy Policy link added (footer and hero section)
- App purpose clearly explained
- Google data usage transparently explained
- All accessible without login

⚠️ **Pending:**
- Domain verification in Google Cloud Console

## Domain Verification Steps

### Step 1: Access OAuth Consent Screen

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **NeuroMedAI**
3. Navigate to **APIs & Services** → **OAuth consent screen**
4. Scroll down to **Authorized domains** section

### Step 2: Add Domain

1. Click **+ Add Domain** button
2. Enter: `neuromedai.org`
3. Click **Add**

### Step 3: Choose Verification Method

Google will offer one of these methods:

#### Method 1: DNS TXT Record (Recommended)

**Steps:**
1. Google will provide a TXT record value (looks like: `google-site-verification=xxxxx`)
2. Go to your domain registrar/DNS provider (where you manage `neuromedai.org`)
3. Add a DNS TXT record:
   - **Type:** TXT
   - **Name/Host:** `@` or `neuromedai.org` (or leave blank)
   - **Value:** (the value Google provided)
   - **TTL:** 3600 (or default)
4. Save the DNS record
5. Wait 5-30 minutes for DNS propagation
6. Go back to Google Cloud Console
7. Click **Verify** button

**Common DNS Providers:**
- **Cloudflare:** DNS → Records → Add record → Type: TXT
- **GoDaddy:** DNS Management → Add → Type: TXT
- **Namecheap:** Advanced DNS → Add New Record → Type: TXT
- **Google Domains:** DNS → Custom records → Add → Type: TXT

#### Method 2: HTML File Upload

**Steps:**
1. Download the HTML file from Google
2. Upload it to your website root directory
3. Make it accessible at: `https://www.neuromedai.org/google-verification.html`
4. Verify the file is publicly accessible (no login required)
5. Click **Verify** in Google Cloud Console

**For Railway/Django:**
- Add the HTML file to `myApp/static/` directory
- Or create a simple view that serves the verification file

#### Method 3: HTML Meta Tag

**Steps:**
1. Google provides a meta tag (looks like: `<meta name="google-site-verification" content="xxxxx" />`)
2. Add it to your landing page `<head>` section
3. Deploy the updated page
4. Click **Verify** in Google Cloud Console

### Step 4: Wait for Verification

- DNS TXT: 5 minutes to 48 hours (usually 30 minutes)
- HTML File: Usually instant after upload
- Meta Tag: Usually instant after deployment

### Step 5: Verify Status

1. Check Google Cloud Console
2. Status should change to "Verified" ✅
3. Green checkmark next to domain

## Troubleshooting

### DNS Record Not Working

**Check:**
1. DNS record is saved correctly
2. TTL has passed (wait longer)
3. Use `dig` or online DNS checker to verify:
   ```bash
   dig TXT neuromedai.org
   ```
4. Make sure record name is correct (`@` or `neuromedai.org`)

### HTML File Not Accessible

**Check:**
1. File is in the correct location
2. File is publicly accessible (no authentication)
3. URL is exactly: `https://www.neuromedai.org/google-verification.html`
4. No redirects interfering

### Meta Tag Not Working

**Check:**
1. Meta tag is in `<head>` section (not `<body>`)
2. Page is deployed and live
3. Meta tag matches exactly what Google provided
4. No caching issues (clear browser cache)

## After Domain Verification

Once domain is verified:

1. ✅ Domain shows as "Verified" in Google Cloud Console
2. ✅ Homepage requirements should be met
3. ✅ Privacy policy link is visible
4. ✅ App purpose is explained
5. ✅ Google data usage is transparent

## Resubmit for Verification

1. Go to OAuth consent screen
2. Verify all information is correct:
   - Homepage URL: `https://www.neuromedai.org`
   - Privacy Policy: `https://www.neuromedai.org/privacy`
   - Terms of Service: `https://www.neuromedai.org/terms`
3. Click **Prepare for verification**
4. Review all sections
5. Click **Submit for verification**
6. Reply to the email from Google Trust & Safety team confirming fixes

## Quick Checklist

- [ ] Domain `neuromedai.org` added to Authorized domains
- [ ] Domain verification method chosen (DNS TXT recommended)
- [ ] DNS TXT record added (or HTML file uploaded, or meta tag added)
- [ ] Domain shows as "Verified" in Google Console
- [ ] Homepage has privacy policy link ✅ (Done)
- [ ] Homepage explains app purpose ✅ (Done)
- [ ] Homepage explains Google data usage ✅ (Done)
- [ ] All URLs match between homepage and OAuth consent screen
- [ ] Resubmitted for verification

## What's Been Fixed

✅ **Privacy Policy Link:**
- Added in footer (prominently displayed)
- Added in hero section
- Links to `/privacy` route

✅ **App Purpose:**
- Added "About NeuroMed AI" section
- Explains functionality clearly
- Describes features and capabilities

✅ **Google Data Usage:**
- Added "How We Use Google Account Information" section
- Explains what data is collected (email, name, profile)
- Explains why it's collected (account creation, personalization)
- Explains how it's used (not shared, secure storage)
- Transparent about purpose (medical document summarization)

## Next Action

**Verify domain ownership:**
1. Go to Google Cloud Console → OAuth consent screen
2. Add `neuromedai.org` to Authorized domains
3. Follow verification steps (DNS TXT record is easiest)
4. Wait for verification
5. Resubmit for OAuth verification

Once domain is verified and you resubmit, Google should approve your OAuth app!


