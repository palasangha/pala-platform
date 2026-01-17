# Production Deployment Checklist

Complete checklist for deploying the MCP agent-based enrichment pipeline to production.

## Pre-Deployment Validation (Phase 8)

Essential steps before deploying to production:

### Test Results Validation

- [ ] Run E2E test: `./run-e2e-test.sh`
- [ ] Verify completeness ≥95% average
- [ ] Verify auto-approval rate ≥90%
- [ ] Verify cost per document ≤$0.50
- [ ] All 5 agents healthy and responsive
- [ ] Document all results and metrics
- [ ] Sign off on test results

### Prompt Optimization

- [ ] Analyze test results with `analyze-results.sh`
- [ ] Identify top 3 missing fields
- [ ] Refine agent prompts in `packages/agents/`
- [ ] Re-test with same documents
- [ ] Verify completeness improvement
- [ ] All prompts documented and version controlled
- [ ] Ready for production release

### Code Review & QA

- [ ] All code reviewed by team member
- [ ] No security vulnerabilities found
- [ ] All tests passing (unit + integration)
- [ ] Code coverage ≥80%
- [ ] Documentation complete and accurate
- [ ] Git commits clean and well-documented

## Infrastructure Setup (Phase 9a)

### Database Configuration

- [ ] MongoDB production instance provisioned
- [ ] Authentication configured (username/password)
- [ ] Database backups configured
  - [ ] Daily backups enabled
  - [ ] Backup retention: 30 days minimum
  - [ ] Backup location: Secure storage (S3/GCS/etc)
  - [ ] Backup testing: Restore tested and verified
- [ ] Indexes created:
  - [ ] `ocr_jobs` on `job_id`, `status`, `created_at`
  - [ ] `enriched_documents` on `document_id`, `completeness_score`
  - [ ] `review_queue` on `status`, `created_at`, `document_id`
  - [ ] `cost_records` on `enrichment_job_id`, `created_at`
- [ ] Replication configured (if high availability required)
- [ ] Monitoring enabled (collection size, query times)

### Message Queue Setup

- [ ] NSQ production cluster deployed
- [ ] nsqlookupd highly available (≥3 nodes recommended)
- [ ] nsqd nodes: ≥2 for redundancy
- [ ] Queue topics created: `enrichment`
- [ ] Message retention configured
- [ ] Monitoring enabled (queue depth, message processing)
- [ ] Alerts configured for queue backlog

### LLM Infrastructure

- [ ] Ollama instance deployed and operational
- [ ] Models pulled and available:
  - [ ] `llama3.2` for Phase 1 agents
  - [ ] `mixtral` for structure-agent
  - [ ] Storage: ≥30GB allocated for models
- [ ] GPU acceleration configured (if available)
- [ ] Model serving health checks enabled
- [ ] Auto-restart on failure configured

### API Keys & Secrets

- [ ] Anthropic API key generated and secured
  - [ ] Key stored in secret manager (Vault/K8s Secrets)
  - [ ] Access restricted to enrichment service
  - [ ] API limits configured (if applicable)
- [ ] MCP JWT secret generated (non-default)
  - [ ] Stored securely
  - [ ] Rotated annually
- [ ] MongoDB passwords changed from defaults
  - [ ] Stored in secure configuration
  - [ ] Different passwords for different environments

### SSL/TLS Certificates

- [ ] Certificates obtained (self-signed or CA)
  - [ ] Valid domain names
  - [ ] 2+ year expiration
  - [ ] Intermediate certificates included
- [ ] Certificates configured for APIs:
  - [ ] Review API (port 5001)
  - [ ] Cost API (port 5002)
- [ ] Certificate renewal process automated
- [ ] Certificate rotation tested

### Networking & Security

- [ ] Firewall rules configured:
  - [ ] Inbound: Only required ports exposed
  - [ ] Outbound: Claude API endpoint allowed
  - [ ] Internal: Services communicate on private network
- [ ] Network segmentation:
  - [ ] MongoDB: Not publicly accessible
  - [ ] NSQ: Not publicly accessible
  - [ ] Ollama: Not publicly accessible
  - [ ] APIs only: Publicly accessible
- [ ] DDoS protection configured (if applicable)
- [ ] Rate limiting enabled on APIs
- [ ] CORS configured correctly

## Monitoring & Observability (Phase 9b)

### Prometheus Setup

- [ ] Prometheus instance deployed
- [ ] Scrape jobs configured for all services
- [ ] Prometheus retention: ≥30 days
- [ ] Alert rules loaded: 30+ rules active
- [ ] AlertManager integrated

### Grafana Dashboards

- [ ] Grafana instance deployed
- [ ] 5 dashboards provisioned:
  - [ ] Enrichment Overview
  - [ ] Agent Performance
  - [ ] Cost Tracking
  - [ ] Document Quality
  - [ ] Processing Throughput
- [ ] Datasource: Prometheus configured
- [ ] Default time range: 24 hours
- [ ] Alert notifications configured

### Alerting

- [ ] AlertManager configured
- [ ] Alert channels configured:
  - [ ] Email notifications
  - [ ] Slack integration (if applicable)
  - [ ] PagerDuty integration (if applicable)
- [ ] Alert recipients configured:
  - [ ] Team members listed
  - [ ] Escalation policy defined
  - [ ] On-call schedule configured
- [ ] All 30+ alert rules tested
- [ ] Alert thresholds validated for production

### Logging

- [ ] Centralized logging configured (ELK/DataDog/etc) [optional]
- [ ] Application logs sent to:
  - [ ] Local files (for debugging)
  - [ ] Central aggregation (for monitoring)
- [ ] Log retention: ≥7 days
- [ ] Log search and analysis available
- [ ] Error tracking configured

### Health Checks

- [ ] Health check endpoints verified:
  - [ ] MongoDB: `/health` on port 27017
  - [ ] NSQ: `/stats` on port 4161
  - [ ] Ollama: `/api/tags` on port 11434
  - [ ] Review API: `/health` on port 5001
  - [ ] Cost API: `/health` on port 5002
- [ ] All health checks passing
- [ ] Monitoring tools configured to check health

## Service Deployment (Phase 9c)

### Docker Compose Deployment

- [ ] Production `.env` file created (not `.env.example`)
- [ ] All environment variables set:
  - [ ] Database credentials
  - [ ] API keys
  - [ ] JWT secrets
  - [ ] Feature flags appropriate for production
- [ ] Resource limits configured:
  - [ ] CPU limits per container
  - [ ] Memory limits per container
  - [ ] Disk storage allocated
- [ ] Health checks verified on all services
- [ ] Restart policies configured: `unless-stopped`
- [ ] Networks isolated: Only necessary inter-service communication
- [ ] Volumes persistent: Data survives container restarts

### Service Scaling

- [ ] EnrichmentWorker replicas: ≥2
- [ ] Load testing completed:
  - [ ] 50 documents in parallel
  - [ ] 100 documents in sequence
  - [ ] Verify no bottlenecks
- [ ] Auto-scaling configured (if using Kubernetes)
- [ ] Worker performance baseline established

### Deployment Process

- [ ] Deployment runbook created
- [ ] Rollback procedure documented
- [ ] Deployment tested in staging
- [ ] Blue/green deployment configured (if applicable)
- [ ] Canary deployment strategy defined

## Initial Production Run (Phase 9d)

### Pre-Launch Checklist

- [ ] All infrastructure ready and tested
- [ ] Monitoring active and alerting working
- [ ] Database backups running successfully
- [ ] All APIs responding normally
- [ ] No pending alerts or warnings
- [ ] Team on-call scheduled
- [ ] Incident response plan reviewed

### Soft Launch (Small Batch)

- [ ] Process 10-20 documents first
- [ ] Monitor closely for errors
- [ ] Verify completeness metrics
- [ ] Verify cost tracking accuracy
- [ ] Check API response times
- [ ] Validate data in review queue
- [ ] Get stakeholder approval before scaling

### Gradual Ramp-Up

- [ ] Week 1: 100 documents
  - [ ] Monitor daily metrics
  - [ ] Verify completeness ≥95%
  - [ ] Verify costs ≤$0.50/doc
  - [ ] Check agent performance
  - [ ] Validate review queue workflow

- [ ] Week 2: 500 documents
  - [ ] Same monitoring as Week 1
  - [ ] Verify system scales smoothly
  - [ ] Check for any resource constraints
  - [ ] Optimize if needed

- [ ] Week 3+: Full production load
  - [ ] Monitor daily metrics
  - [ ] Weekly performance reports
  - [ ] Cost analysis and optimization
  - [ ] Incident log and resolution
  - [ ] Continuous improvement

### Post-Launch Validation

- [ ] Completeness metrics meet targets
- [ ] Cost tracking accurate
- [ ] No data loss or corruption
- [ ] All backups working correctly
- [ ] Monitoring and alerting effective
- [ ] Team comfortable with operations
- [ ] Documentation accurate and useful

## Ongoing Operations

### Daily Operations

- [ ] Monitor dashboards: 2x daily (morning, evening)
- [ ] Check for alerts: Immediate response
- [ ] Review completeness metrics
- [ ] Monitor costs vs budget
- [ ] Process new enrichment jobs

### Weekly Operations

- [ ] Review weekly metrics report
- [ ] Analyze completeness by agent
- [ ] Review cost breakdowns
- [ ] Check backup status
- [ ] Performance optimization review
- [ ] Incident review (if any)

### Monthly Operations

- [ ] Database maintenance (index optimization, cleanup)
- [ ] Certificate expiration check (60 days before)
- [ ] API rate limit analysis
- [ ] Cost trend analysis
- [ ] Capacity planning (scale workers if needed)
- [ ] Security review
- [ ] Performance optimization initiatives

### Quarterly Operations

- [ ] Disaster recovery drill (restore from backup)
- [ ] Load testing to verify capacity
- [ ] Security audit and penetration testing
- [ ] Dependency updates and patching
- [ ] Documentation review and updates
- [ ] Architecture review for improvements

## Troubleshooting & Support

### Common Issues & Resolutions

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| Low completeness | <90% docs complete | Review agent logs, optimize prompts |
| High costs | >$0.50/doc | Disable expensive agents, optimize routing |
| Queue backlog | NSQ depth growing | Scale workers, increase parallelism |
| API errors | 500 responses | Check logs, restart affected services |
| Data loss | Missing documents | Verify backups, restore from backup |

### Support Contacts

- [ ] Team lead: _________________
- [ ] On-call engineer: _________
- [ ] Database admin: ___________
- [ ] Cloud infrastructure: _____
- [ ] Security team: ____________

### Escalation Process

1. **Level 1**: On-call engineer investigates
2. **Level 2**: Team lead engaged if unresolved in 30min
3. **Level 3**: Architecture team consulted if unresolved in 2hrs
4. **Level 4**: Executive escalation if business impact critical

## Success Criteria

Production deployment is successful when:

✅ **All infrastructure operational**
- [ ] All services healthy
- [ ] Monitoring active
- [ ] Backups working
- [ ] Alerts configured

✅ **Pipeline performing as expected**
- [ ] Completeness ≥95% average
- [ ] Auto-approval ≥90%
- [ ] Cost ≤$0.50/doc
- [ ] Throughput ≥50 docs/hour

✅ **Team trained and confident**
- [ ] All runbooks documented
- [ ] Team trained on operations
- [ ] Incident response tested
- [ ] On-call schedule established

✅ **Business objectives met**
- [ ] Processing expected volumes
- [ ] Costs within budget
- [ ] Quality metrics achieved
- [ ] Users satisfied

## Sign-Off

- [ ] Deployment lead: _________________________ Date: _______
- [ ] Team lead: ______________________________ Date: _______
- [ ] Security lead: ___________________________ Date: _______
- [ ] Operations lead: ________________________ Date: _______

Production deployment approved and ready for full launch.

