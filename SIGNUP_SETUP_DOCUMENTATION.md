# NeuroMed AI Signup Setup Documentation

**Last Updated:** Generated from codebase analysis  
**Purpose:** Complete documentation of the user signup/registration system

---

## Table of Contents
1. [Overview](#overview)
2. [URL Routing](#url-routing)
3. [Form Structure](#form-structure)
4. [Signup Process Flow](#signup-process-flow)
5. [Data Models](#data-models)
6. [Email System](#email-system)
7. [Template Structure](#template-structure)
8. [Validation Rules](#validation-rules)
9. [Analytics Tracking](#analytics-tracking)

---

## Overview

The NeuroMed AI signup system allows new users to create accounts with email, username, password, and optional profession information. The system includes automatic login, welcome emails, and comprehensive analytics tracking.

**Key Features:**
- Email-based registration with uniqueness validation
- Automatic user profile creation
- IP address and country tracking
- Welcome email delivery via Resend API
- Analytics tracking for signup events
- Terms of Service acceptance requirement

---

## URL Routing

**Route:** `/signup/`  
**View:** `views.signup_view`  
**Name:** `signup`

```python
# Location: myApp/urls.py, line 15
path('signup/', views.signup_view, name='signup'),
```

**Access:** Public (no authentication required)

---

## Form Structure

### CustomSignupForm

**Location:** `myApp/forms.py`  
**Base Class:** `django.contrib.auth.forms.UserCreationForm`

#### Required Fields
- **first_name** (CharField, max_length=150)
- **last_name** (CharField, max_length=150)
- **email** (EmailField) - Validated for uniqueness
- **username** (CharField) - Standard Django username
- **password1** (CharField) - Password input
- **password2** (CharField) - Password confirmation

#### Optional Fields
- **profession** (CharField, max_length=100) - Saved to Profile model, not User model

#### Form Meta Configuration
```python
class Meta(UserCreationForm.Meta):
    model = User
    fields = ["first_name", "last_name", "email", "username", "password1", "password2"]
    # Note: 'profession' is NOT in fields list (it's saved to Profile separately)
```

#### Email Validation
- Email is normalized to lowercase
- Stripped of whitespace
- Checked for uniqueness (case-insensitive)
- Raises `ValidationError` if email already exists

---

## Signup Process Flow

### Step-by-Step Process

**Location:** `myApp/views.py`, function `signup_view()`

#### 1. Form Submission (POST)
- Form is instantiated with `request.POST` data
- Form validation is performed

#### 2. User Creation
```python
user = form.save()
```
- Creates Django `User` object
- Sets email (lowercased and stripped)
- Sets first_name and last_name
- Hashes and stores password
- Creates associated `Profile` object with profession (if provided)

#### 3. Profile Enhancement
```python
profile, _ = Profile.objects.get_or_create(user=user)
profile.signup_ip = get_client_ip(request)
profile.signup_country = getattr(request, "country_code", None) or profile.signup_country
profile.save()
```
- Retrieves or creates Profile for user
- Captures signup IP address
- Captures signup country (from middleware if available)

#### 4. Analytics Tracking
```python
UserSignup.objects.get_or_create(
    user=user,
    defaults={
        'ip_address': get_client_ip(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'referer': request.META.get('HTTP_REFERER', '')
    }
)
```
- Creates `UserSignup` record for analytics
- Tracks IP address, user agent, and referer URL

#### 5. Automatic Login
- Attempts authentication with username/email and password
- Falls back to manual login if authentication fails
- Sets authentication backend if needed

#### 6. Welcome Email (Async)
```python
transaction.on_commit(_send)
```
- Sends welcome email after database transaction commits
- Uses Resend API for delivery
- Does not block signup flow if email fails

#### 7. Redirect
- Redirects to `/dashboard/`
- Sets `just_logged_in` cookie (expires in 60 seconds)

### GET Request Handling
- Displays empty signup form
- Renders `signup.html` template

---

## Data Models

### User Model
**Type:** Django's built-in `django.contrib.auth.models.User`  
**Fields Used:**
- `username`
- `email`
- `first_name`
- `last_name`
- `password` (hashed)

### Profile Model
**Location:** `myApp/models.py`  
**Relationship:** OneToOne with User

**Fields:**
- `user` (OneToOneField to User)
- `profession` (CharField, max_length=100, optional)
- `display_name` (CharField, max_length=100, optional)
- `language` (CharField, default='en-US')
- `signup_ip` (GenericIPAddressField) - Captured during signup
- `last_login_ip` (GenericIPAddressField)
- `signup_country` (CharField, max_length=2) - ISO country code
- `last_login_country` (CharField, max_length=2)

### UserSignup Model
**Location:** `myApp/models.py`  
**Purpose:** Analytics tracking for signup events

**Fields:**
- `user` (OneToOneField to User)
- `ip_address` (GenericIPAddressField)
- `user_agent` (TextField)
- `referer` (URLField)
- `created_at` (DateTimeField, auto_now_add=True)

**Ordering:** `-created_at` (newest first)

---

## Email System

### Welcome Email Function
**Location:** `myApp/views.py`, function `send_welcome_email()`

**Parameters:**
- `email` (str) - Recipient email address
- `first_name` (str) - User's first name
- `login_url` (str) - Fully qualified login URL

**Subject:** "Welcome to NeuroMed AI Beta – You're Helping Shape the Future 🌿"

**Content Includes:**
- Welcome message
- Beta features overview:
  - Plain Mode
  - Caregiver Mode
  - Faith Mode
  - Clinical Mode
  - Multiple Languages
- Getting started instructions
- Login link button
- Contact information (hello@neuromedai.org)
- Inspirational quote (Habakkuk 2:2)

**Delivery:**
- Uses Resend API (`send_via_resend()` from `myApp/emailer.py`)
- Sends both HTML and plain text versions
- Fails silently (doesn't block signup if email fails)
- Sent asynchronously via `transaction.on_commit()`

### Email Configuration
**Location:** `myApp/emailer.py`

**Settings Required:**
- `RESEND.API_KEY` - Resend API key
- `RESEND.BASE_URL` - Resend API base URL (default: https://api.resend.com)
- `RESEND.FROM` - Sender email address
- `RESEND.REPLY_TO` - Reply-to email address (optional)

---

## Template Structure

**Location:** `myApp/templates/signup.html`

### Design Features
- Tailwind CSS styling
- NeuroMed AI branding (logo from Cloudinary)
- Responsive grid layout (1 column mobile, 2 columns desktop)
- Font Awesome icons for form fields
- Password visibility toggle
- Terms of Service checkbox (required)

### Form Fields Layout
1. **First Name** - Left column (desktop)
2. **Last Name** - Right column (desktop)
3. **Email** - Left column (desktop)
4. **Profession** - Right column (desktop), optional
5. **Username** - Left column (desktop)
6. **Password** - Right column (desktop), with visibility toggle
7. **Password Confirmation** - Left column (desktop), with visibility toggle
8. **Terms Checkbox** - Full width, required
9. **Submit Button** - Full width

### Branding Elements
- Logo: `https://res.cloudinary.com/djzks0atj/image/upload/v1759412135/NeuroMed_AI_Logo-10_yassi6.png`
- Tagline: "Because Every Patient Deserves Clarity"
- Subtitle: "Simplify your care journey with AI that has both heart and intelligence."
- Primary color: `#236092` (blue)
- Accent color: `teal-700` (submit button)

### JavaScript Features
- Password visibility toggle function
- Overlay cleanup script (removes blocking modals)

---

## Validation Rules

### Email Validation
- **Required:** Yes
- **Format:** Must be valid email format
- **Uniqueness:** Case-insensitive check against existing users
- **Normalization:** Lowercased and stripped of whitespace
- **Error Message:** "This email is already registered."

### Password Validation
- Inherits Django's `UserCreationForm` password validation
- Minimum length: 8 characters (Django default)
- Must include mix of letters, numbers, and symbols (recommended)
- Password confirmation must match password1

### Username Validation
- Inherits Django's standard username validation
- Required field
- Must be unique

### Name Fields
- **first_name:** Required, max_length=150
- **last_name:** Required, max_length=150
- Both are stripped of whitespace

### Profession Field
- **Required:** No (optional)
- **Max Length:** 100 characters
- Stored in Profile model, not User model

---

## Analytics Tracking

### UserSignup Record
Created for every successful signup:
- **IP Address:** Captured via `get_client_ip(request)`
- **User Agent:** Browser/client information
- **Referer:** Source URL that led to signup page
- **Timestamp:** Auto-created on record creation

### Profile Tracking
- **signup_ip:** IP address at time of signup
- **signup_country:** ISO country code (from middleware if available)

### Usage
Analytics data can be accessed via:
- `User.signup_record` (OneToOne relationship)
- `Profile.signup_ip` and `Profile.signup_country`
- Admin interface or analytics dashboard

---

## Dependencies

### Required Django Components
- `django.contrib.auth` - User authentication
- `django.contrib.auth.forms.UserCreationForm` - Base form
- `django.db.transaction` - Transaction management

### External Services
- **Resend API** - Email delivery service
- **Cloudinary** - Logo/image hosting (for template)

### Utility Functions
- `get_client_ip(request)` - Extracts client IP from request
- `send_via_resend()` - Resend API wrapper

---

## Security Considerations

1. **CSRF Protection:** Form includes `{% csrf_token %}`
2. **Password Hashing:** Django automatically hashes passwords
3. **Email Uniqueness:** Prevents duplicate accounts
4. **IP Tracking:** Logged for security/analytics purposes
5. **Terms Acceptance:** Required checkbox for legal compliance
6. **Transaction Safety:** Email sent after DB commit to ensure user exists

---

## Referral Code System (Optional Signup Referrals)

### Purpose

The referral code system introduces a light, non-intrusive referral mechanism that supports:

- Users entering an optional referral code during signup
- Every user having their own personal referral code that can be shared with others
- Both referral fields are nullable to ensure:
  - Users can sign up without referral codes
  - Existing users (pre-referral system) don't break and don't require automatic migration
  - The system gracefully supports new + existing users without creating friction

### Referral Code Components

There are two independent referral concepts:

#### 1. Referral Code Entered at Signup (Optional)

**Form Field:** `referral_code` in `CustomSignupForm`

**Behavior:**
- Optional field in the signup form labeled "Referral Code (optional)"
- Users may:
  - Enter a valid referral code from another user, OR
  - Leave it blank
- If left blank: System stores nothing (true null, not a placeholder)
- If filled:
  - System attempts to find which user owns that code
  - If found → stores that relationship in `Profile.referred_by`
  - If not found → signup still succeeds (does not block registration)

**Location:** `myApp/forms.py`, `CustomSignupForm.referral_code`

#### 2. User's Own Referral Code (Automatically Generated)

**Model Field:** `Profile.personal_referral_code`

**Behavior:**
- Each new user automatically receives a unique personal code
- Generated only for new users created after the referral system goes live
- Must be nullable, so old users can exist without one
- Format: 8-character alphanumeric code (uppercase letters + digits)
- Uniqueness: Enforced at database level

**Generation:** `myApp/utils.py`, `generate_referral_code()` function

### Nullability Requirements (Critical Behavior)

Both referral fields allow NULL:

**Signup referral code (entered by user):**
- Many users will never enter a code
- Not required
- Accepts empty input without breaking validation

**User's own referral code:**
- Existing accounts may never receive referral codes
- System does not assume all users have one
- Referral code generation happens only for new users moving forward

**Benefits:**
- Smooth rollout without data migration
- No retroactive validation
- Zero signup friction

### Implementation Details

#### Model Fields

**Location:** `myApp/models.py`, `Profile` model

```python
personal_referral_code = models.CharField(
    max_length=20,
    unique=True,
    blank=True,
    null=True,
    help_text="User's personal referral code that they can share with others"
)
referred_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name='referrals',
    help_text="User who referred this account (via referral code)"
)
```

#### Form Field

**Location:** `myApp/forms.py`, `CustomSignupForm`

```python
referral_code = forms.CharField(
    max_length=20,
    required=False,
    label="Referral Code",
    help_text="(optional) Enter a referral code if you have one"
)
```

#### Signup Process Integration

**Location:** `myApp/views.py`, `signup_view()`

**Process Flow:**
1. User submits signup form with optional referral code
2. After user creation, referral code is processed:
   - Code is normalized (uppercase, stripped)
   - System searches for Profile with matching `personal_referral_code`
   - If found: `Profile.referred_by` is set to the referring user
   - If not found: Signup continues (no error, no blocking)
3. Personal referral code is generated for new user:
   - Only if `personal_referral_code` is empty
   - Uses `generate_referral_code()` utility function
   - Ensures uniqueness before assignment

#### Template Field

**Location:** `myApp/templates/signup.html`

- Placed between "Profession" and "Username" fields
- Styled consistently with other form fields
- Includes help text: "Have a referral code? Enter it here to support the person who referred you."
- Uses gift icon (Font Awesome `fa-gift`)
- Input automatically converts to uppercase

#### Code Generation Utility

**Location:** `myApp/utils.py`, `generate_referral_code()`

**Function:**
- Generates 8-character codes (default length)
- Format: Mix of uppercase letters (A-Z) and digits (0-9)
- Ensures uniqueness by checking against existing codes
- Retries if collision occurs (extremely rare)

### User Experience

#### Signup Page
- New field: "Referral Code (optional)"
- No mandatory referral input
- Signup always completes regardless of referral validity
- Field is clearly marked as optional

#### For Existing Users
- Nothing changes for them
- They initially appear with no personal referral code (`NULL`)
- No migration required
- Can be assigned codes later if needed

#### For New Users
- After signup:
  - They automatically receive a unique personal referral code
  - Code is stored in their Profile
  - They can share it with others
  - Code can be accessed via `user.profile.personal_referral_code`

### Database Migration

**Migration File:** `myApp/migrations/0016_profile_referral_code_fields.py`

**Operations:**
- Adds `personal_referral_code` field (CharField, unique, nullable)
- Adds `referred_by` field (ForeignKey, nullable)

**Backward Compatibility:**
- All fields are nullable
- No data migration required
- Existing users unaffected

### Analytics & Tracking

**Referral Relationships:**
- Access referring user: `user.profile.referred_by`
- Access all referrals: `user.referrals.all()` (via reverse relation)
- Check if user has referral code: `user.profile.personal_referral_code is not None`

**Use Cases:**
- Track which users referred others
- Calculate referral statistics
- Reward referrers (future enhancement)
- Analyze referral effectiveness

### System Behavior Summary

| Behavior | Requirement | Status |
|----------|-------------|--------|
| Referral entry is optional | Must allow empty/null | ✅ Implemented |
| User's own referral code is optional | Must allow empty/null | ✅ Implemented |
| Backwards compatible with existing users | No migration needed | ✅ Implemented |
| Signup must never fail because of referral field | Required | ✅ Implemented |
| Tracking of referrals | Flexible, nullable | ✅ Implemented |
| Unique user-generated referral codes | For new users only | ✅ Implemented |

### Impact on Existing Signup Flow

**No Breaking Changes:**
- All existing signup functionality remains intact
- Welcome email unchanged
- Auto-login unchanged
- IP/country tracking unchanged
- Analytics tracking unchanged
- TOS acceptance unchanged
- Resend Email integration unchanged

**Additions Only:**
- One new optional form field
- Two new nullable Profile fields
- Referral code generation for new users
- Referral relationship tracking

### Related Files

- `myApp/models.py` - Profile model with referral fields
- `myApp/forms.py` - CustomSignupForm with referral_code field
- `myApp/views.py` - signup_view with referral processing
- `myApp/templates/signup.html` - Signup form template with referral field
- `myApp/utils.py` - generate_referral_code() function
- `myApp/migrations/0016_profile_referral_code_fields.py` - Database migration

---

## Error Handling

### Form Validation Errors
- Displayed inline below each field
- Non-field errors displayed at top of form
- Styled with red text and borders

### Email Delivery Failures
- Fail silently (don't block signup)
- Logged for debugging
- User still successfully registered

### Authentication Failures
- Falls back to manual login with backend assignment
- User is still logged in successfully

---

## Future Enhancement Opportunities

1. **Email Verification:** Add email confirmation step before account activation
2. **Social Login:** OAuth integration (Google, Facebook, etc.)
3. **Password Strength Meter:** Visual indicator for password strength
4. **CAPTCHA:** Bot protection for signup form
5. **Multi-step Form:** Break signup into multiple steps
6. **Organization Signup:** Allow users to sign up with organization codes
7. ~~**Referral System:** Track referral sources and codes~~ ✅ **IMPLEMENTED** - See Referral Code System section above

---

## Related Files

- `myApp/urls.py` - URL routing
- `myApp/views.py` - Signup view and email function
- `myApp/forms.py` - CustomSignupForm definition
- `myApp/models.py` - Profile and UserSignup models
- `myApp/templates/signup.html` - Signup form template
- `myApp/emailer.py` - Email sending utilities
- `myApp/utils.py` - Utility functions (get_client_ip, generate_referral_code)

---

## Notes

- The signup form creates both a User and Profile automatically
- Profession is stored in Profile, not User model
- Welcome email is sent asynchronously to avoid blocking
- All signups are tracked for analytics purposes
- The system automatically logs users in after successful signup
- Terms of Service acceptance is required via checkbox

---

**Document Version:** 2.0  
**Last Updated:** Added Referral Code System  
**Generated:** From codebase analysis  
**Maintained By:** Development Team

