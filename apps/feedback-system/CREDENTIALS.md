# 🔐 ADMIN CREDENTIALS - GLOBAL VIPASSANA PAGODA FEEDBACK SYSTEM

**Last Updated:** 2026-01-24

---

## 🌟 SUPER ADMIN

**Purpose:** Access to all departments, full system control

```
Email:    superadmin@globalpagoda.org
Password: SuperAdmin@2026!
Role:     super_admin
Access:   All departments
```

**Capabilities:**
- ✅ View all department feedbacks
- ✅ Generate reports for any department
- ✅ Manage admin users
- ✅ View department statistics
- ✅ Export data
- ✅ System configuration

---

## 🏢 DEPARTMENT ADMINS

### 1. 🛍️ SHOP

```
Email:    shop@globalpagoda.org
Password: ShopAdmin@2026!
Role:     dept_admin
Department: shop
```

**Access:** Shop feedback only

---

### 2. 🕉️ DHAMMA LANE

```
Email:    dhammalane@globalpagoda.org
Password: DhammaLane@2026!
Role:     dept_admin
Department: dhamma_lane
```

**Access:** Dhamma Lane feedback only

---

### 3. 🍽️ FOOD COURT

```
Email:    foodcourt@globalpagoda.org
Password: FoodCourt@2026!
Role:     dept_admin
Department: food_court
```

**Access:** Food Court feedback only

---

### 4. 🧘 DPVC (Dhammapattana Vipassana Centre)

```
Email:    dpvc@globalpagoda.org
Password: DPVC@2026!
Role:     dept_admin
Department: dpvc
```

**Access:** DPVC feedback only

---

### 5. 🏛️ GLOBAL VIPASSANA PAGODA

```
Email:    head@globalpagoda.org
Password: Pagoda@2026!
Role:     dept_admin
Department: global_pagoda
```

**Access:** Global Pagoda feedback only

---

## 📋 DEPARTMENT ADMIN CAPABILITIES

Each department admin can:
- ✅ View their department's feedback
- ✅ Filter by week/month/year
- ✅ View individual feedback entries
- ✅ Receive weekly email reports
- ✅ Export their department's data
- ❌ Cannot access other departments
- ❌ Cannot manage users
- ❌ Cannot see system-wide statistics

---

## 🔒 SECURITY NOTES

1. **Change Default Passwords:**
   - All passwords should be changed on first login
   - Use strong passwords (min 12 characters)
   - Include uppercase, lowercase, numbers, symbols

2. **Access Control:**
   - Department admins are restricted to their department
   - Super admin has full access
   - All actions are logged

3. **Session Security:**
   - JWT tokens expire after 24 hours
   - Logout clears all session data

---

## 🚀 LOGIN INSTRUCTIONS

### Web Admin Panel:
1. Navigate to: `http://localhost:3030/admin` (or production URL)
2. Enter email and password
3. Click "Sign In"
4. Dashboard will load based on your role

---

**⚠️ IMPORTANT: Keep these credentials secure and confidential!**
