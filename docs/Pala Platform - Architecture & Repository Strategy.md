# **Pala Platform \- Architecture & Repository Strategy**

---

## **Table of Contents**

1. [Executive Summary](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#executive-summary)  
2. [High-Level Architecture](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#high-level-architecture)  
3. [Architecture Components](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#architecture-components)  
4. [Data Flow](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#data-flow)  
5. [Repository Strategy](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#repository-strategy)  
6. [Implementation Plan](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#implementation-plan)  
7. [Technology Stack](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#technology-stack)  
8. [Next Steps](https://claude.ai/chat/98cb4f99-f261-4b71-af32-b56e6abbced6#next-steps)

---

## **Executive Summary**

Pala is a comprehensive digital preservation platform designed for the Vipassana Research Institute to digitize, authenticate, enrich, and provide intelligent access to historical content including physical letters, audio/video recordings, and digital materials.

### **Key Objectives**

* **Digitization**: Convert physical and analog content to digital formats  
* **Authentication**: Ensure data integrity through digital signing  
* **Enrichment**: Add comprehensive metadata for discoverability  
* **Intelligence**: Provide AI-powered access through multiple agents  
* **Accessibility**: Enable various consumer applications to access content


---

## **High-Level Architecture**

<img width="2052" height="1128" alt="Pala Architecture" src="https://github.com/user-attachments/assets/e4821231-6534-4e0c-89d9-45366ff8601d" />


---

## **Architecture Components**

### **1\. Data Sources Layer**

**Purpose**: Entry point for all content into the system

**Components:**

* **Physical Letters**: Scanned documents, handwritten materials  
* **Audio/Video Files**: Recorded discourses, talks, interviews  
* **Digital Content**: Existing digital documents, emails, text files  
* **Others**: Additional source types (images, manuscripts, etc.)

**Data Format**: Raw, unstructured data in various formats (images, audio, video, text)

---

### **2\. Processors Layer**

**Purpose**: Convert raw data into structured digital text with basic metadata

**Components:**

#### **a) OCR Engine**

* Converts scanned text and images to digital text  
* Supports multiple languages and scripts  
* Handles handwritten and typed content

#### **b) PalaScribe**

* Transcribes audio and video content to text  
* Speaker identification and timestamps  
* Supports multiple audio formats  
* Language detection and translation capabilities

#### **c) Custom Processors**

* Specialized processors for unique content types  
* Extensible architecture for community contributions

#### **d) Others**

* Additional processing capabilities as needed

**Output**: Digital text \+ basic metadata (source, date, format, language)

---

### **3\. Enrichment Layer**

**Purpose**: Add rich metadata and ensure content authenticity

**Components:**

#### **a) Metadata Enricher**

* Extracts contextual information from content  
* Identifies actors, locations, dates, topics  
* Categorizes and tags content  
* Generates searchable metadata

#### **b) Schema Manager**

* Defines and maintains metadata schemas  
* Ensures consistency across content types  
* Validates metadata completeness  
* Version control for schemas

#### **c) Digital Signing**

* Creates cryptographic signatures for content  
* Ensures authenticity and integrity  
* Timestamp verification  
* Chain of custody tracking

#### **d) Others**

* Custom enrichment workflows  
* Integration with external reference data

**Output**: Digitized content \+ rich metadata \+ digital signatures

---

### **4\. Storage Layer**

**Purpose**: Persist data securely and efficiently with cost optimization

**Components:**

#### **a) Cloud Storage**

* Primary storage in cloud infrastructure (AWS S3, Google Cloud Storage)  
* Geographic redundancy  
* Scalable and durable

#### **b) Local Storage**

* On-premises storage for sensitive content  
* Faster access for frequently used data  
* Compliance with data sovereignty requirements

#### **c) Storage API**

* Unified interface for all storage operations  
* Abstraction over different storage backends  
* Access control and permissions  
* Query and retrieval operations

#### **d) Cost Optimizer**

* Intelligent tiering (hot/warm/cold storage)  
* Compression and deduplication  
* Lifecycle policies  
* Usage analytics

**Features:**

* Bidirectional communication with MCP Server  
* Version control and history  
* Backup and disaster recovery  
* Audit logging

---

### **5\. MCP Server & AI Agents Layer**

**Purpose**: Central orchestration hub for intelligent operations via Model Context Protocol

#### **MCP Orchestrator (Core)**

* **Central coordination and routing layer**  
* Agent registry and discovery  
* Request routing and load balancing  
* Protocol implementation (MCP)  
* Error handling and retry logic  
* Logging and observability

#### **AI Agents**

The platform includes multiple specialized agents that communicate via MCP protocol:

**Currently Planned:**

1. **Verification Agent** ✅

   * Validates generated data against source  
   * Cross-references with reference databases  
   * Quality assurance checks  
2. **Formatter Agent** 📝

   * Standardizes content formats  
   * Applies style guidelines  
   * Converts between formats  
3. **Signing Agent** 🔏

   * Handles digital signature operations  
   * Certificate management  
   * Verification workflows  
4. **Metadata Agent** 🏷️

   * Extracts metadata from content  
   * Enriches existing metadata  
   * Schema validation  
   * **Status**: Starting development with MCP server  
5. **Scribe Agent** 🎤

   * Transcription services  
   * Audio/video processing  
   * Language detection  
6. **OCR Agent** 👁️

   * Image-to-text conversion  
   * Handwriting recognition  
   * Layout analysis  
7. **Search Agent** 🔍

   * Full-text search  
   * Semantic search  
   * Query optimization  
8. **Analysis Agent** 🧠

   * Content analysis  
   * Topic modeling  
   * Insights generation  
9. **Query Agent** 📊

   * Natural language queries  
   * Data aggregation  
   * Report generation  
10. **Custom Agents** 🔧

    * Community-contributed agents  
    * Specialized workflows  
    * Domain-specific processing

**Agent Communication:**

* All agents communicate via standardized MCP protocol  
* Asynchronous message passing  
* Event-driven architecture  
* Pluggable agent system

---

### **6\. Consumers/Clients Layer**

**Purpose**: Provide access interfaces for various user types and use cases

**Components:**

#### **a) Web Portal 🖥️**

* Primary management interface  
* Content upload and management  
* Workflow monitoring  
* User administration  
* Dashboard and analytics  
* **Technology**: Next.js, React

#### **b) Archipelago 🏛️**

* Integration with external digital archive system  
* Cultural heritage platform integration  
* Interoperability with museum/library systems  
* Metadata exchange

#### **c) AI Chatbots 🤖**

* Intelligent conversational interface  
* Natural language queries  
* Content discovery and exploration  
* Context-aware responses  
* **Technology**: LangChain, Claude API

#### **d) Mobile Apps 📱**

* iOS and Android applications  
* On-the-go content access  
* Offline capabilities  
* Push notifications  
* **Technology**: React Native

#### **e) Third-Party Apps 🔌**

* External API integrations  
* Custom tools and applications  
* Partner integrations  
* Developer ecosystem  
* **Technology**: REST API, GraphQL, SDK

**Access Method**: All consumers interact via MCP Protocol

---

### **7\. Shared Services Layer**

**Purpose**: Provide cross-cutting infrastructure capabilities

**Service Categories:**

#### **a) Observability & Monitoring 📊**

* **Centralized Logging**: Application and system logs  
* **Metrics Collection**: Performance, usage, errors  
* **Alerting & Notifications**: Real-time alerts, escalation  
* **Audit Trails**: Compliance and security logging  
* **Tools**: Prometheus, Grafana, ELK Stack

#### **b) Security & Infrastructure 🔒**

* **Authentication**: User identity management (OAuth, JWT)  
* **Authorization**: Role-based access control (RBAC)  
* **Encryption**: Data at rest and in transit  
* **API Gateway**: Rate limiting, throttling, API keys  
* **Backup & Disaster Recovery**: Automated backups, RPO/RTO  
* **Tools**: Auth0, Vault, Kong

#### **c) Other Services ⚡**

* **Caching**: Redis for performance optimization  
* **Message Queue**: Async processing (RabbitMQ, Kafka)  
* **Search Index**: Elasticsearch for full-text search  
* **CDN**: Content delivery network  
* **Notifications**: Email and SMS services  
* **DevOps CI/CD**: Automated build and deployment  
* **Tools**: Redis, Kafka, Elasticsearch, CloudFlare

---

## **Data Flow**

### **Complete Processing Pipeline**

1\. INGESTION  
   Physical Letter → Scanner → Image File  
                                  ↓  
2\. PROCESSING  
   Image File → OCR Engine → Digital Text \+ Basic Metadata  
                                  ↓  
3\. ENRICHMENT  
   Digital Text → Metadata Agent → Extract metadata  
                → Schema Manager → Validate against schema  
                → Digital Signing → Add cryptographic signature  
                                  ↓  
4\. STORAGE  
   Signed Content \+ Rich Metadata → Storage API → Cloud/Local Storage  
                                  ↓  
5\. ACCESS (via MCP)  
   User Query → Web Portal → MCP Server → Query Agent  
                                  ↓  
   Query Agent → Storage API → Retrieve Content  
                                  ↓  
   Retrieved Content → MCP Server → Web Portal → User

### **Key Data Flow Patterns**

#### **Pattern 1: Document Digitization**

Physical Document → OCR Processor → Enrichment → Storage  
                    ↓ (feeds into)  
                 Metadata Agent (via MCP)

#### **Pattern 2: Audio Transcription**

Audio File → PalaScribe → Enrichment → Storage  
             ↓ (feeds into)  
          Scribe Agent (via MCP)

#### **Pattern 3: User Query**

User → Client → MCP Server → Multiple Agents → Storage → Response

#### **Pattern 4: Agent Collaboration**

MCP Server orchestrates:  
1\. Search Agent → Finds relevant content  
2\. Metadata Agent → Enriches results  
3\. Formatter Agent → Standardizes output  
4\. Verification Agent → Validates response

---

## **Repository Strategy**

### **Recommended Approach: Monorepo with Strategic Separation**

Given the team size (2-3 core members) and architecture requirements, we recommend a **monorepo for core platform** with **separate repositories for community contributions**.

---

### **Primary Repository: `pala-platform` (Monorepo)**

pala-platform/  
├── packages/  
│   ├── processors/  
│   │   ├── ocr-engine/              \# ← Currently in development  
│   │   ├── palascribe/  
│   │   └── processor-utils/  
│   │  
│   ├── enrichment/  
│   │   ├── metadata-enricher/  
│   │   ├── schema-manager/  
│   │   ├── digital-signing/  
│   │   └── enrichment-utils/  
│   │  
│   ├── storage/  
│   │   ├── storage-api/  
│   │   ├── cloud-adapter/  
│   │   ├── local-adapter/  
│   │   └── storage-utils/  
│   │  
│   ├── mcp-server/                  \# ← Starting now  
│   │   ├── core/  
│   │   ├── protocol/  
│   │   ├── orchestrator/  
│   │   └── registry/  
│   │  
│   ├── agents/  
│   │   ├── metadata-agent/          \# ← Starting now  
│   │   ├── verification-agent/  
│   │   ├── formatter-agent/  
│   │   ├── signing-agent/  
│   │   ├── scribe-agent/  
│   │   ├── ocr-agent/  
│   │   ├── search-agent/  
│   │   ├── analysis-agent/  
│   │   ├── query-agent/  
│   │   └── agent-sdk/               \# For community agent dev  
│   │  
│   └── shared/  
│       ├── types/                   \# Common TypeScript types  
│       ├── utils/                   \# Shared utilities  
│       ├── config/                  \# Configuration management  
│       └── constants/  
│  
├── apps/  
│   ├── web-portal/                  \# Next.js application  
│   │   ├── src/  
│   │   ├── public/  
│   │   └── package.json  
│   │  
│   ├── mobile/                      \# React Native  
│   │   ├── ios/  
│   │   ├── android/  
│   │   ├── src/  
│   │   └── package.json  
│   │  
│   └── api-gateway/                 \# External API wrapper  
│       ├── src/  
│       └── package.json  
│  
├── integrations/  
│   └── archipelago/  
│       ├── adapter/  
│       └── sync/  
│  
├── services/  
│   ├── observability/  
│   │   ├── logging/  
│   │   └── monitoring/  
│   ├── security/  
│   │   ├── auth/  
│   │   └── encryption/  
│   └── infrastructure/  
│  
├── infrastructure/  
│   ├── docker/  
│   │   ├── Dockerfile.mcp-server  
│   │   ├── Dockerfile.web  
│   │   └── docker-compose.yml  
│   ├── kubernetes/  
│   │   ├── deployments/  
│   │   └── services/  
│   └── terraform/  
│       ├── aws/  
│       └── gcp/  
│  
├── docs/  
│   ├── architecture/  
│   │   ├── overview.md  
│   │   ├── mcp-protocol.md  
│   │   └── data-flow.md  
│   ├── api-reference/  
│   │   ├── mcp-api.md  
│   │   ├── storage-api.md  
│   │   └── agent-api.md  
│   ├── development-guide/  
│   │   ├── setup.md  
│   │   ├── contributing.md  
│   │   └── testing.md  
│   └── user-guide/  
│  
├── examples/  
│   ├── basic-workflow/  
│   ├── custom-agent/  
│   └── integration/  
│  
├── tools/  
│   ├── scripts/  
│   │   ├── setup.sh  
│   │   ├── dev.sh  
│   │   └── deploy.sh  
│   └── generators/  
│  
├── tests/  
│   ├── integration/  
│   ├── e2e/  
│   └── fixtures/  
│  
├── .github/  
│   └── workflows/  
│       ├── ci.yml  
│       ├── cd.yml  
│       └── release.yml  
│  
├── package.json                     \# Root package.json  
├── turbo.json                       \# Turborepo configuration  
├── tsconfig.json                    \# Shared TypeScript config  
├── .eslintrc.js                     \# Linting rules  
├── .prettierrc                      \# Code formatting  
├── README.md  
└── LICENSE

---

### **Community Repositories (Separate) \- potentially in future**

Its tbd whether the community contributions can go directly in the above repo’s than creating separate repos below. We will delay this decision to future

#### **1\. `pala-community-agents`**

pala-community-agents/  
├── agents/  
│   ├── translation-agent/  
│   ├── summarization-agent/  
│   ├── classification-agent/  
│   └── \[community-contributed-agents\]/  
├── templates/  
│   └── agent-template/  
├── docs/  
│   ├── creating-agents.md  
│   └── testing-agents.md  
└── examples/

**Purpose**: Community-contributed AI agents **Why Separate**: Encourages innovation, independent versioning, lower barrier to entry

#### **2\. `pala-community-processors`**

pala-community-processors/  
├── processors/  
│   ├── ancient-script-ocr/  
│   ├── audio-enhancement/  
│   ├── video-segmentation/  
│   └── \[community-contributed-processors\]/  
├── models/  
│   └── ml-models/  
└── docs/

**Purpose**: Community-contributed processors and ML models **Why Separate**: Heavy ML dependencies, independent development cycles

#### **3\. `pala-templates`**

pala-templates/  
├── metadata-schemas/  
│   ├── discourse-schema.json  
│   ├── letter-schema.json  
│   └── manuscript-schema.json  
├── workflow-templates/  
│   ├── digitization-workflow.yml  
│   └── enrichment-workflow.yml  
└── docs/

**Purpose**: Schema templates, workflow templates, non-code contributions **Why Separate**: Non-technical contributors, versioned separately from code

---

### **Repository Strategy: Pros & Cons**

#### **✅ Pros of Monorepo for Core Platform**

**1\. Technical Benefits**

* **Atomic Changes**: Single PR updates backend \+ frontend \+ agents  
* **Type Safety**: Shared TypeScript types across all packages  
* **Code Reuse**: Common utilities, validation, constants shared  
* **Simplified Dependencies**: Single `package.json`, no version conflicts  
* **Integrated Testing**: E2E tests across entire stack

**2\. Team Benefits**

* **Single Source of Truth**: Entire codebase in one place  
* **Faster Code Reviews**: See full impact of changes  
* **Easier Onboarding**: One `git clone` gets everything  
* **Reduced Context Switching**: No jumping between repos  
* **Better for Small Teams**: 2-3 developers see entire platform

**3\. MCP-Specific Benefits**

* **Protocol Changes**: Update MCP \+ all agents simultaneously  
* **Agent Testing**: Easy to test agent interactions  
* **Visibility**: Clear view of agent dependencies  
* **Debugging**: Easier to trace issues across services

**4\. Client Integration Benefits**

* **Shared Types**: API types automatically sync with clients  
* **Coordinated Releases**: Deploy stack together  
* **Shared Components**: Web and mobile share React components  
* **Single Dev Environment**: `npm run dev` starts everything

#### **❌ Cons of Monorepo**

**1\. Technical Challenges**

* **Build Performance**: Building entire repo can be slow  
  * *Mitigation*: Turborepo caching, build only changed packages  
* **Git Repository Size**: Grows large over time  
  * *Mitigation*: Git shallow clones, LFS for assets  
* **Tooling Complexity**: Requires sophisticated build tools  
  * *Mitigation*: Good documentation, gradual learning

**2\. Workflow Challenges**

* **Merge Conflicts**: Shared files conflict frequently  
  * *Mitigation*: Trunk-based development, frequent commits  
* **Version Management**: Complex semantic versioning  
  * *Mitigation*: Single version for entire platform  
* **Testing Overhead**: Long test suites  
  * *Mitigation*: Smart test selection, parallel execution

**3\. Team Challenges**

* **Onboarding Complexity**: New developers see entire codebase  
  * *Mitigation*: Clear documentation, package boundaries  
* **Community Friction**: Higher barrier to entry  
  * *Mitigation*: Separate repos for community contributions  
* **Access Control**: All-or-nothing access  
  * *Mitigation*: CODEOWNERS, careful PR review

---

### **Why Clients Should Be in Monorepo**

#### **Strong Reasons to Include:**

1. **Type Safety Across Stack**

// Backend defines API types  
// packages/shared/types/api.ts  
export interface Metadata {  
  id: string;  
  source: string;  
  language: string;  
}

// Frontend automatically uses same types  
// apps/web-portal/src/api/metadata.ts  
import { Metadata } from '@pala/shared/types';

// TypeScript catches breaking changes immediately\!

2. **Coordinated Releases**  
* API schema change \+ UI update in single PR  
* No version mismatches between frontend/backend  
* Deploy stack together atomically  
3. **Shared Component Library**

// packages/ui-components/  
export { Button, Input, Card, Modal };

// Used in:  
// \- apps/web-portal/  
// \- apps/mobile/  
// Same design system, consistent UX

4. **Simplified Development**

\# Single command starts everything  
npm run dev

\# Starts:  
\# \- MCP Server (localhost:3000)  
\# \- Web Portal (localhost:3001)  
\# \- Mobile (Expo DevTools)  
\# \- Mock Services

#### **When to Separate Clients:**

* Different team owns frontend (not the case for Pala)  
* Completely different tech stack (e.g., Python Django)  
* Independent release cycles required  
* External contractors building client only

**Decision for Pala**: ✅ **Include clients in monorepo**

---

[image1]: <data:image/png;base64,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>
