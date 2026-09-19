# Slice 1 — Authentication & Identity

Status: **analysis / design proposal — not yet implemented**

## 1. User-visible behavior today

### Registration

`POST /users/`

Flow:

1. Pydantic validates first name, last name, email and password.
2. `services/users.py` checks whether the email already exists.
3. Password is hashed with bcrypt using a generated salt.
4. `crud/users.py` creates the user ORM object.
5. Service commits and refreshes the user.
6. `UserResponse` returns safe public fields and does not include the password.

### Login

`POST /auth/`

Flow:

1. FastAPI's `OAuth2PasswordRequestForm` accepts username/email and password.
2. User is looked up by email.
3. bcrypt verifies the password.
4. A JWT is issued with:
   - `user_id`
   - `exp` set to 15 minutes
5. API returns `access_token` and `token_type=bearer`.

### Authenticated current user

`GET /users/`

Flow:

1. `OAuth2PasswordBearer` extracts the bearer token.
2. `verify_existing_token()` decodes and validates the JWT.
3. The user ID from the token is passed into `get_current_user()`.
4. The user is loaded from the database.
5. A safe `UserResponse` is returned.

### Admin

`/admin/*` attempts to use both token verification and `check_admin()` as router dependencies.

The current admin dependency is broken and does not reliably deny non-admin users.

---

## 2. Relevant code

- `router/users.py`
- `router/auth.py`
- `dependecies/auth.py`
- `dependecies/users.py`
- `services/users.py`
- `crud/users.py`
- `schemas/users.py`
- `utils.py`
- `router/admin.py`
- `crud/admin.py`
- `models.User`
- `tests/routers/test_users.py`

Relevant history:

- Authentication was originally implemented directly around routes.
- Token/admin verification was later moved into dependencies.
- A later refactor deliberately moved user/account/card validity and ownership checks into dependency modules to reduce route size and centralize security.

That refactor is an intentional design choice worth preserving.

---

## 3. What is already good and should be preserved

### Dependency-based authentication

The current-user pattern is good:

`JWT -> verify token -> user ID -> get current user`

Routes do not ask the caller to provide their own user ID.

### Password hashing

bcrypt with a generated salt is appropriate for this demo. There is no reason to replace it merely for modernization.

### Short-lived access tokens

The 15-minute token lifetime is a valid simple design for a portfolio MVP.

Refresh tokens are **not required** unless we later decide the frontend needs longer-lived sessions.

### Safe response schema

Passwords are not serialized through `UserResponse`.

### Service/CRUD separation

User creation has a sensible split:

- route handles HTTP
- service handles duplicate-check + hashing + transaction
- CRUD creates/query ORM entities

For this project size, this is enough abstraction.

### OAuth2 integration

`OAuth2PasswordBearer` and `OAuth2PasswordRequestForm` integrate naturally with FastAPI/OpenAPI/Swagger and should be retained.

---

## 4. Confirmed problems

### A. Admin authorization is broken — HIGH PRIORITY

Current `check_admin(user_id, db=Depends(get_db))`:

- does not derive `user_id` from the authenticated user/token;
- FastAPI can treat the plain `user_id` parameter as request input;
- returns a boolean instead of raising `403`;
- when used only in `dependencies=[...]`, a returned `False` does not itself deny access.

Target behavior:

`get_current_user -> if not user.is_admin: raise 403 -> return user`

### B. Valid JWT without a usable user ID is handled poorly

`verify_existing_token()` returns `payload.get("user_id")`.

A cryptographically valid token without that claim can produce `None`, which then falls through to a user lookup and may become a 404 instead of an authentication failure.

The token dependency should reject a missing/invalid identity claim as 401.

### C. Login errors reveal whether an email exists

Today:

- unknown email -> 404 "not registered"
- wrong password -> 401 "wrong password"

For a polished public demo, a single `401 Invalid email or password` response is cleaner and avoids account-enumeration behavior.

This is security hardening, not a fundamental architecture change.

### D. Password validation is unnecessarily restrictive

Current password rule:

- 8–20 characters
- only letters, numbers, underscore and hyphen

This rejects many strong passwords containing normal symbols and imposes a short maximum.

Portfolio V2 should validate length without artificially restricting the character set.

### E. Name validation is unnecessarily restrictive

Current names allow only ASCII letters and minimum length 3.

That rejects legitimate names such as `Li`, accented names, hyphenated names, etc.

This is not a security problem, but it is poor product validation.

### F. Type annotation on token verification is inaccurate

`verify_existing_token(...)->dict` actually returns a user ID.

Small cleanup only.

### G. Auth behavior lacks negative tests

Current tests cover:

- registration success
- login success
- current-user success

Missing important tests:

- duplicate email
- wrong password
- unknown email
- invalid token
- expired token
- missing identity claim
- unauthenticated current-user access
- normal user denied admin access
- admin allowed

---

## 5. V2 proposal

Keep the architecture small.

### Registration

`POST /users/`

- Keep bcrypt.
- Keep duplicate-email check.
- Improve name/password validation.
- Return `201 Created`.
- Continue returning `UserResponse`.

### Login

`POST /auth/`

- Keep OAuth2 password form for now.
- Keep 15-minute JWT access token.
- Use a generic 401 for invalid credentials.
- Keep token creation simple.
- Do **not** add refresh tokens in the MVP unless the frontend later requires them.

### Token identity

Keep JWT simple, but make the identity claim explicit and validated.

We can retain `user_id` initially or switch to standard JWT `sub`; this is a cleanup choice, not a necessary rewrite.

### Current user

Keep `get_current_user()` dependency exactly as the central identity resolver.

### Admin

Use the current authenticated user:

```text
token
  -> get_current_user
      -> require_admin
          -> admin route
```

A normal user must receive `403 Forbidden`.

For this portfolio project, the existing `is_admin: bool` field is sufficient. A full roles/permissions framework is unnecessary.

### Refresh tokens

Not part of Slice 1 MVP.

Reason:

- additional state/security complexity;
- little portfolio value right now;
- a 15-minute login session is enough during development/demo;
- can be added later if frontend UX makes it worthwhile.

---

## 6. Proposed acceptance criteria

Slice 1 is complete when:

- registration works and never exposes password hashes;
- duplicate email is rejected;
- passwords are bcrypt-hashed;
- login succeeds with correct credentials;
- invalid credentials return the same 401 response;
- access token expiry is enforced;
- missing/invalid token identity is rejected as 401;
- authenticated `/users/` returns only the current user;
- unauthenticated access is rejected;
- normal user receives 403 from admin endpoints;
- admin user can use admin endpoints;
- focused auth tests are green.

---

## 7. What we intentionally do NOT add

For Portfolio MVP Slice 1:

- no Google/GitHub OAuth
- no MFA
- no email verification
- no password reset email
- no auth microservice
- no external identity provider
- no complex RBAC framework
- no refresh-token system unless later required

These may be useful in other products but do not justify their cost for this portfolio MVP.

---

## 8. Proposed implementation tickets after approval

### Ticket A — Fix authenticated identity and admin authorization

Scope:

- validate JWT identity claim;
- make admin check depend on current authenticated user;
- raise 403 for non-admins;
- add admin/token regression tests.

### Ticket B — Polish registration/login validation and responses

Scope:

- generic invalid-credentials response;
- improve password/name validation;
- normalize response/status codes;
- add duplicate/invalid-login tests.

These can potentially be implemented in one short-lived slice branch because the total change is small, but two logical commits are preferable.

---

## 9. Open decisions

Recommended defaults:

1. **Access token:** keep 15-minute access-only JWT for MVP.
2. **Refresh tokens:** do not add now.
3. **Admin model:** keep simple `is_admin` boolean.
4. **Invalid login:** use generic `401 Invalid email or password`.
5. **Passwords:** minimum length, generous max length, no artificial character whitelist.
6. **Names:** remove ASCII-only restriction and allow realistic names.
7. **JWT identity claim:** either keep `user_id` or migrate to standard `sub`; low-impact decision.

No application code should be changed until these slice decisions are accepted.
