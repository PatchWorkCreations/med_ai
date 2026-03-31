# Account review — Manzanita79 (afmalilio@gmail.com)

**Date prepared:** 2026-04-01  
**Purpose:** Explain the internal user report row and respond to the user’s concern that they are seeing “email already in use” / duplicate signals even though they believe this was their **first** time creating an account.

---

## 1. Report row (as shown in admin export)

| Field | Value shown |
|--------|-------------|
| Username | Manzanita79 |
| Email | afmalilio@gmail.com |
| Joined (`date_joined`) | 2026-03-31 18:46 |
| Last login (Django `last_login`) | 2026-03-31 18:46 |
| Last sign-in (tracked / `UserSignin`) | — |
| Tracked sign-ins | 0 |
| Summaries / chats | 0 / 0 |

---

## 2. Is this consistent with a **first-time, successful** signup?

**Yes.** The data is consistent with **one** account created for this email on that date/time, with an immediate logged-in session.

### Same time for “Joined” and “Last login”

After a successful signup, the app calls Django’s `login()` so the user lands in the product without signing in again. Django updates **`last_login`** at that moment. For a brand-new user, **`date_joined`** and **`last_login`** are often **the same minute** (sometimes the same second). That is **not** evidence of an older account—it means the account was created and the session started in one flow.

### “Email already registered” after refresh or a second submit

Signup uses server-side validation: **`CustomSignupForm.clean_email`** rejects the email if **any** user already exists with that address (case-insensitive).

Flow that confuses people:

1. First **POST** succeeds → user row is created → browser redirects to the dashboard.
2. User hits **refresh** on the signup page, or the form **submits again**, or they open signup in another tab and submit again.
3. Second request sees the email **already in the database**—because **their own** first signup succeeded.
4. They see **“This email is already registered.”** That can feel like “someone else used my email,” but it usually means **the first attempt already completed**.

**Conclusion for this case:** If the only `User` row for `afmalilio@gmail.com` was created at **2026-03-31 18:46**, the duplicate-email message on a later attempt is **expected** and points to **that same account**, not a pre-existing stranger account.

---

## 3. Why “Last sign-in (tracked)” is blank and sign-ins = 0

This is a **reporting limitation**, not proof they never logged in.

- **Django `last_login`** is updated whenever `login()` runs (including **during signup**).
- **`UserSignin`** rows (used for “tracked” sign-ins in analytics) are created on **email/password login** (`WarmLoginView`) and **API login** paths, **not** in the **web signup** view after `login()`.

So a user who has **only** completed **signup** (and not used the standalone login page / API login) can correctly show:

- **`last_login`** set (from signup `login()`),
- **`UserSignin` count = 0** and **last tracked sign-in = —**.

**Optional product improvement:** Record a successful `UserSignin` when `login()` runs after signup, so analytics matches user expectations. (Code change in `signup_view`, not required to resolve this support case.)

---

## 4. Process review — is “our report” correct?

| Question | Answer |
|----------|--------|
| Does one row mean one account for that email? | **Yes** (one `User` per email in our signup rules). |
| Does same timestamp for joined + last login imply they had an account before? | **No** — normal for signup + immediate `login()`. |
| Does 0 tracked sign-ins mean they never authenticated? | **No** — they authenticated via signup; we don’t always write `UserSignin` for that path. |
| If they saw “email already registered” after refreshing, is the first signup still “first time”? | **Yes** — the first POST likely succeeded; the message is from a **second** request after the user already existed. |

---

## 5. Suggested wording for the user (short)

> We looked up your account. There is **one** NeuroMed Aira account for **afmalilio@gmail.com**, created on **March 31, 2026**. Your “joined” and “last login” times match because you were **logged in automatically right after signing up**, which is normal.  
>  
> If the site said the email was **already registered** after you went back or refreshed the signup page, that usually means **the first signup had already gone through**—so the system correctly saw your email as taken **by the account you had just created**.  
>  
> The “0” sign-ins in one of our internal reports only tracks certain login events; it doesn’t mean you didn’t complete signup.

---

## 6. References (codebase)

- Email uniqueness: `CustomSignupForm.clean_email` in `myApp/forms.py`.
- Signup + `login()`: `signup_view` in `myApp/views.py`.
- `UserSignin` on login page: `WarmLoginView.form_valid` in `myApp/views.py` (not called from signup flow).

---

*Internal use — redact before sharing externally if needed.*
