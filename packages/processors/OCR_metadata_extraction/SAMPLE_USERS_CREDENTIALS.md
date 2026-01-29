# Sample User Credentials for Testing

This document contains sample login credentials for testing different user roles in the system.

## Available Users

### 1. Admin User
**Full system access with all permissions**

- **Email:** `admin@example.com`
- **Password:** `admin123`
- **Role:** `admin`
- **Permissions:**
  - Classify documents
  - Run OCR
  - View public and private queues
  - Claim, approve, reject documents
  - View dashboard and audit logs
  - Export documents
  - Manage users and roles

---

### 2. Reviewer User
**Can review and approve/reject documents**

- **Email:** `reviewer@example.com`
- **Password:** `reviewer123`
- **Role:** `reviewer`
- **Permissions:**
  - View public queue
  - Claim documents
  - Approve documents
  - Reject documents

---

### 3. Teacher User
**Can view private queues and classify documents**

- **Email:** `teacher@example.com`
- **Password:** `teacher123`
- **Role:** `teacher`
- **Permissions:**
  - View public and private queues
  - Claim documents
  - Classify documents

---

### 4. Existing User (Your Account)
- **Email:** `bhushan0508@gmail.com`
- **Role:** `reviewer`

---

## Testing Role-Based Access Control (RBAC)

### Admin Features
Login as admin to:
- Access all system features
- Manage other users
- View audit logs
- Access system settings

### Reviewer Features
Login as reviewer to:
- Review documents in the public queue
- Approve or reject documents
- No access to user management

### Teacher Features
Login as teacher to:
- View both public and private document queues
- Classify documents
- Claim documents for review

---

## Security Note

⚠️ **Important:** These are test credentials for development/demo purposes only. 

**For Production:**
- Change all default passwords
- Use strong, unique passwords
- Enable 2FA if available
- Remove or disable test accounts

---

## How to Create Additional Users

Run the following script inside the backend container:

```bash
docker exec gvpocr-backend python /tmp/create_sample_users.py
```

Or add users manually via MongoDB:

```javascript
db.users.insertOne({
    email: "newuser@example.com",
    password: "<hashed_password>",
    name: "New User",
    roles: ["reviewer"],  // or ["admin"], ["teacher"]
    is_active: true
})
```

---

**Last Updated:** 2026-01-26
