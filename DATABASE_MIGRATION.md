# OCR RBAC System - Database Migration Guide

**Document Version**: 1.0
**Date**: 2026-01-22

---

## Overview

This guide contains MongoDB migration scripts to set up the database schema for the RBAC system.

---

## Migration: Create Core Collections

### Step 1: Connect to MongoDB

```bash
mongosh "mongodb://localhost:27017"
use ocr_rbac_db
```

### Step 2: Create Users Collection

```javascript
// Create collection with validation
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["email", "name", "password_hash", "roles", "active"],
      properties: {
        _id: { bsonType: "objectId" },
        email: {
          bsonType: "string",
          pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
        },
        name: { bsonType: "string" },
        password_hash: { bsonType: "string" },
        google_id: { bsonType: "string" },
        roles: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        active: { bsonType: "bool" },
        security_clearance: {
          bsonType: "string",
          enum: ["standard", "elevated", "sensitive"]
        },
        assigned_project_ids: {
          bsonType: "array",
          items: { bsonType: "objectId" }
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
        last_login: { bsonType: ["date", "null"] },
        created_by: { bsonType: ["objectId", "null"] }
      }
    }
  }
})

// Create indexes
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ roles: 1 });
db.users.createIndex({ active: 1 });
db.users.createIndex({ created_at: -1 });
db.users.createIndex({ security_clearance: 1 });
```

### Step 3: Create Roles Collection

```javascript
db.createCollection("roles", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "description", "permissions"],
      properties: {
        _id: { bsonType: "objectId" },
        name: {
          bsonType: "string",
          enum: ["admin", "reviewer", "teacher"]
        },
        description: { bsonType: "string" },
        permissions: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        data_access_level: {
          bsonType: "string",
          enum: ["all", "public_only", "assigned_only"]
        },
        created_at: { bsonType: "date" }
      }
    }
  }
})

// Create indexes
db.roles.createIndex({ name: 1 }, { unique: true });

// Insert default roles
db.roles.insertMany([
  {
    _id: ObjectId(),
    name: "admin",
    description: "Administrator with full system access",
    permissions: [
      "create_project", "manage_users", "classify_document", "run_ocr",
      "view_all_documents", "review_document", "edit_metadata", "approve_final",
      "export_data", "view_dashboards", "view_audit_logs", "override_state"
    ],
    data_access_level: "all",
    created_at: new Date()
  },
  {
    _id: ObjectId(),
    name: "reviewer",
    description: "Reviews public documents only",
    permissions: [
      "view_public_documents", "review_document", "edit_metadata"
    ],
    data_access_level: "public_only",
    created_at: new Date()
  },
  {
    _id: ObjectId(),
    name: "teacher",
    description: "Reviews public and private documents",
    permissions: [
      "view_all_documents", "review_document", "edit_metadata"
    ],
    data_access_level: "all",
    created_at: new Date()
  }
])
```

### Step 4: Create Projects Collection

```javascript
db.createCollection("projects", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "name"],
      properties: {
        _id: { bsonType: "objectId" },
        user_id: { bsonType: "objectId" },
        name: { bsonType: "string" },
        description: { bsonType: "string" },
        collaborators: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              user_id: { bsonType: "objectId" },
              role: { bsonType: "string" },
              assigned_at: { bsonType: "date" }
            }
          }
        },
        state: {
          bsonType: "string",
          enum: ["active", "paused", "archived"]
        },
        total_documents: { bsonType: "int" },
        processed_documents: { bsonType: "int" },
        reviewed_documents: { bsonType: "int" },
        approved_documents: { bsonType: "int" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
})

// Create indexes
db.projects.createIndex({ user_id: 1 });
db.projects.createIndex({ "collaborators.user_id": 1 });
db.projects.createIndex({ state: 1 });
db.projects.createIndex({ created_at: -1 });
```

### Step 5: Create Documents Collection

```javascript
db.createCollection("documents", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["project_id", "filename", "status"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: "objectId" },
        filename: { bsonType: "string" },
        filepath: { bsonType: "string" },
        file_type: { bsonType: "string" },
        file_size: { bsonType: "int" },
        checksum: { bsonType: "string" },

        // Classification
        classification: {
          bsonType: ["string", "null"],
          enum: [null, "PUBLIC", "PRIVATE"]
        },
        classified_by: { bsonType: ["objectId", "null"] },
        classified_at: { bsonType: ["date", "null"] },

        // Status & History
        status: { bsonType: "string" },
        status_history: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              status: { bsonType: "string" },
              changed_by: { bsonType: "objectId" },
              changed_at: { bsonType: "date" },
              reason: { bsonType: "string" }
            }
          }
        },

        // Processing
        processed_by: { bsonType: ["objectId", "null"] },
        processed_at: { bsonType: ["date", "null"] },

        // OCR
        ocr_status: {
          bsonType: "string",
          enum: ["pending", "processing", "completed", "failed"]
        },
        ocr_provider: { bsonType: "string" },
        ocr_text: { bsonType: "string" },
        ocr_confidence: { bsonType: "double" },
        ocr_processed_at: { bsonType: ["date", "null"] },
        ocr_error: { bsonType: "string" },
        ocr_retry_count: { bsonType: "int" },

        // Review
        reviewed_by: { bsonType: ["objectId", "null"] },
        reviewed_at: { bsonType: ["date", "null"] },
        review_notes: { bsonType: "string" },
        manual_edits: {
          bsonType: "array",
          items: {
            bsonType: "object",
            properties: {
              field_name: { bsonType: "string" },
              original_value: { bsonType: "string" },
              edited_value: { bsonType: "string" },
              edited_by: { bsonType: "objectId" },
              edited_at: { bsonType: "date" }
            }
          }
        },

        // Enrichment
        enrichment_status: {
          bsonType: "string",
          enum: ["pending", "processing", "completed", "failed"]
        },
        enriched_metadata: { bsonType: "object" },
        enrichment_confidence: { bsonType: "double" },

        // Final Approval
        final_approved_by: { bsonType: ["objectId", "null"] },
        final_approved_at: { bsonType: ["date", "null"] },
        final_approval_notes: { bsonType: "string" },

        // Export
        exported_at: { bsonType: ["date", "null"] },
        exported_to: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        export_error: { bsonType: "string" },

        // Audit
        audit_log_ids: {
          bsonType: "array",
          items: { bsonType: "objectId" }
        },

        // Timestamps
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  }
})

// Create indexes
db.documents.createIndex({ project_id: 1 });
db.documents.createIndex({ status: 1 });
db.documents.createIndex({ classification: 1 });
db.documents.createIndex({ processed_by: 1 });
db.documents.createIndex({ reviewed_by: 1 });
db.documents.createIndex({ created_at: -1 });
db.documents.createIndex({ project_id: 1, status: 1 });
db.documents.createIndex({ classification: 1, status: 1 });
db.documents.createIndex({ status: 1, processed_at: 1 });
```

### Step 6: Create Audit Logs Collection (Capped)

```javascript
// Create capped collection for immutable audit logs
db.createCollection("audit_logs", {
  capped: true,
  size: 1073741824,  // 1GB
  max: 10000000  // 10 million documents
})

// Create indexes on capped collection
db.audit_logs.createIndex({ action_type: 1 });
db.audit_logs.createIndex({ actor_id: 1 });
db.audit_logs.createIndex({ document_id: 1 });
db.audit_logs.createIndex({ created_at: -1 });
db.audit_logs.createIndex({ document_id: 1, created_at: 1 });
db.audit_logs.createIndex({ is_sensitive: 1 });
```

### Step 7: Create Review Queues Collection

```javascript
db.createCollection("review_queues", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["project_id", "document_id", "classification", "assigned_role"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: "objectId" },
        document_id: { bsonType: "objectId" },
        classification: {
          bsonType: "string",
          enum: ["PUBLIC", "PRIVATE"]
        },
        assigned_role: {
          bsonType: "string",
          enum: ["reviewer", "teacher"]
        },
        status: {
          bsonType: "string",
          enum: ["pending", "claimed", "completed", "reassigned"]
        },
        claimed_by: { bsonType: ["objectId", "null"] },
        claimed_at: { bsonType: ["date", "null"] },
        queued_at: { bsonType: "date" },
        due_at: { bsonType: "date" },
        completed_at: { bsonType: ["date", "null"] },
        sla_violated: { bsonType: "bool" },
        escalation_count: { bsonType: "int" },
        escalated_to_admin: { bsonType: "bool" },
        created_at: { bsonType: "date" }
      }
    }
  }
})

// Create indexes
db.review_queues.createIndex({ project_id: 1 });
db.review_queues.createIndex({ status: 1 });
db.review_queues.createIndex({ assigned_role: 1 });
db.review_queues.createIndex({ classification: 1 });
db.review_queues.createIndex({ due_at: 1 });
db.review_queues.createIndex({ document_id: 1 });
```

### Step 8: Create Assignments Collection

```javascript
db.createCollection("assignments", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["project_id", "assignee_id", "document_ids"],
      properties: {
        _id: { bsonType: "objectId" },
        project_id: { bsonType: "objectId" },
        admin_id: { bsonType: "objectId" },
        assignee_id: { bsonType: "objectId" },
        assignee_role: {
          bsonType: "string",
          enum: ["reviewer", "teacher"]
        },
        document_ids: {
          bsonType: "array",
          items: { bsonType: "objectId" }
        },
        document_count: { bsonType: "int" },
        assignment_type: {
          bsonType: "string",
          enum: ["batch", "individual"]
        },
        due_at: { bsonType: "date" },
        priority: {
          bsonType: "string",
          enum: ["low", "normal", "high"]
        },
        status: {
          bsonType: "string",
          enum: ["assigned", "in_progress", "completed", "overdue"]
        },
        completed_count: { bsonType: "int" },
        notes: { bsonType: "string" },
        created_at: { bsonType: "date" },
        completed_at: { bsonType: ["date", "null"] }
      }
    }
  }
})

// Create indexes
db.assignments.createIndex({ project_id: 1 });
db.assignments.createIndex({ assignee_id: 1 });
db.assignments.createIndex({ status: 1 });
db.assignments.createIndex({ due_at: 1 });
db.assignments.createIndex({ created_at: -1 });
```

### Step 9: Create OCR Jobs Collection

```javascript
db.createCollection("ocr_jobs", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["job_id", "admin_id", "document_ids", "provider", "status"],
      properties: {
        _id: { bsonType: "objectId" },
        job_id: { bsonType: "string" },
        admin_id: { bsonType: "objectId" },
        document_ids: {
          bsonType: "array",
          items: { bsonType: "objectId" }
        },
        document_count: { bsonType: "int" },
        provider: { bsonType: "string" },
        settings: { bsonType: "object" },
        status: {
          bsonType: "string",
          enum: ["PROCESSING", "COMPLETED", "FAILED", "PAUSED"]
        },
        progress: {
          bsonType: "object",
          properties: {
            current: { bsonType: "int" },
            total: { bsonType: "int" },
            percentage: { bsonType: "double" }
          }
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" },
        completed_at: { bsonType: ["date", "null"] }
      }
    }
  }
})

// Create indexes
db.ocr_jobs.createIndex({ job_id: 1 }, { unique: true });
db.ocr_jobs.createIndex({ admin_id: 1 });
db.ocr_jobs.createIndex({ status: 1 });
db.ocr_jobs.createIndex({ created_at: -1 });
```

---

## Migration: Create Test Data

```javascript
// Insert test admin user
db.users.insertOne({
  _id: ObjectId(),
  email: "admin@ocr-platform.com",
  name: "Administrator",
  password_hash: "$2b$12$...",  // Hashed password for "admin123"
  roles: ["admin"],
  active: true,
  security_clearance: "sensitive",
  assigned_project_ids: [],
  created_at: new Date(),
  updated_at: new Date(),
  last_login: null,
  created_by: null
})

// Insert test reviewer user
db.users.insertOne({
  _id: ObjectId(),
  email: "reviewer@ocr-platform.com",
  name: "Public Reviewer",
  password_hash: "$2b$12$...",
  roles: ["reviewer"],
  active: true,
  security_clearance: "standard",
  assigned_project_ids: [],
  created_at: new Date(),
  updated_at: new Date(),
  last_login: null,
  created_by: null
})

// Insert test teacher user
db.users.insertOne({
  _id: ObjectId(),
  email: "teacher@ocr-platform.com",
  name: "Senior Teacher",
  password_hash: "$2b$12$...",
  roles: ["teacher"],
  active: true,
  security_clearance: "elevated",
  assigned_project_ids: [],
  created_at: new Date(),
  updated_at: new Date(),
  last_login: null,
  created_by: null
})

// Insert test project
const adminId = db.users.findOne({ email: "admin@ocr-platform.com" })._id
db.projects.insertOne({
  _id: ObjectId(),
  user_id: adminId,
  name: "Test Project",
  description: "Sample project for testing",
  collaborators: [],
  state: "active",
  total_documents: 0,
  processed_documents: 0,
  reviewed_documents: 0,
  approved_documents: 0,
  created_at: new Date(),
  updated_at: new Date()
})
```

---

## Migration: Data Backup & Restore

### Backup Database

```bash
# Backup entire database
mongodump --uri="mongodb://localhost:27017/ocr_rbac_db" --out=/backup/ocr_rbac_backup

# Backup specific collection
mongodump --uri="mongodb://localhost:27017/ocr_rbac_db" --collection=audit_logs --out=/backup/audit_logs_backup
```

### Restore Database

```bash
# Restore entire database
mongorestore --uri="mongodb://localhost:27017" /backup/ocr_rbac_backup

# Restore specific collection
mongorestore --uri="mongodb://localhost:27017" --nsInclude="ocr_rbac_db.audit_logs" /backup/audit_logs_backup
```

---

## Migration: Index Maintenance

### Analyze Index Performance

```javascript
// Get index statistics
db.documents.aggregate([
  { $indexStats: {} }
])

// Find slow queries
db.system.profile.find({
  millis: { $gt: 1000 }
}).sort({ ts: -1 }).limit(10)
```

### Rebuild Indexes

```javascript
// Rebuild all indexes on collection
db.documents.reIndex()

// Drop specific index
db.documents.dropIndex("status_1_created_at_-1")

// Rebuild only changed indexes
db.documents.createIndex({ status: 1 }, { background: true })
```

---

## Migration: Monitoring & Validation

### Verify Collections Created

```javascript
// List all collections
show collections

// Get collection statistics
db.documents.stats()

// Check index sizes
db.documents.aggregate([
  { $indexStats: {} }
])
```

### Verify Data Integrity

```javascript
// Check for missing required fields
db.documents.find({
  $or: [
    { project_id: { $exists: false } },
    { filename: { $exists: false } },
    { status: { $exists: false } }
  ]
})

// Check for invalid status values
db.documents.find({
  status: {
    $not: {
      $in: [
        "UPLOADED", "CLASSIFICATION_PENDING", "CLASSIFIED_PUBLIC",
        "CLASSIFIED_PRIVATE", "OCR_PROCESSING", "OCR_PROCESSED",
        "IN_REVIEW", "REVIEWED_APPROVED", "FINAL_ADMIN_REVIEW",
        "FINAL_APPROVED", "EXPORTED"
      ]
    }
  }
})
```

---

## Rollback Procedure

### If Migration Fails

```bash
# Stop application
systemctl stop ocr-api

# Restore from backup
mongorestore --uri="mongodb://localhost:27017" /backup/pre_migration_backup

# Drop new collections if partial
mongo ocr_rbac_db --eval "db.documents_new.drop()"

# Restart application
systemctl start ocr-api
```

---

## Performance Tuning After Migration

```javascript
// Analyze query performance
db.documents.find({ status: "IN_REVIEW" }).explain("executionStats")

// Optimize slow queries
db.documents.createIndex({ classification: 1, status: 1 })

// Monitor collection size
db.documents.stats().size  // Total size in bytes
db.documents.stats().count  // Number of documents
```

