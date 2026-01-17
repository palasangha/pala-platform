#!/bin/bash

# Analyze Enrichment Results
# Comprehensive analysis of enrichment completeness, costs, and quality metrics

set -e

MONGO_USER="${MONGO_USER:-enrichment_user}"
MONGO_PASSWORD="${MONGO_PASSWORD:-changeMe123}"
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-gvpocr}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo "================================"
echo "Enrichment Results Analysis"
echo "================================"
echo ""

# Check MongoDB connection
echo "[1/6] Checking MongoDB connection..."
if ! mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "db.adminCommand('ping')" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to MongoDB"
    exit 1
fi
echo "✓ MongoDB connection successful"
echo ""

# Overall Statistics
echo "[2/6] Gathering overall statistics..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');

        // Overall stats
        var totalDocs = db.enriched_documents.countDocuments({});
        var approved = db.enriched_documents.countDocuments({review_status: 'approved'});
        var reviewPending = db.enriched_documents.countDocuments({review_status: 'pending'});
        var notRequired = db.enriched_documents.countDocuments({review_status: 'not_required'});

        print('\n=== DOCUMENT PROCESSING SUMMARY ===');
        print('Total Documents Enriched: ' + totalDocs);
        print('Approved (Auto): ' + approved);
        print('Pending Review: ' + reviewPending);
        print('No Review Required: ' + notRequired);

        if (totalDocs > 0) {
            var approveRate = ((approved + notRequired) / totalDocs * 100).toFixed(1);
            print('Auto-Approval Rate: ' + approveRate + '%');
        }
    "

echo ""

# Completeness Analysis
echo "[3/6] Analyzing completeness metrics..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');

        var docs = db.enriched_documents.find({}, {quality_metrics: 1}).toArray();

        if (docs.length === 0) {
            print('No documents found');
            quit();
        }

        print('\n=== COMPLETENESS ANALYSIS ===');

        // Calculate statistics
        var scores = docs.map(d => d.quality_metrics?.completeness_score || 0);
        scores.sort((a,b) => a - b);

        var sum = scores.reduce((a,b) => a + b, 0);
        var avg = sum / scores.length;
        var min = scores[0];
        var max = scores[scores.length - 1];
        var median = scores[Math.floor(scores.length / 2)];

        print('Average Completeness: ' + avg.toFixed(3));
        print('Median Completeness: ' + median.toFixed(3));
        print('Min: ' + min.toFixed(3) + ', Max: ' + max.toFixed(3));

        // Distribution
        var bins = {
            'perfect (100%)': 0,
            '95-99%': 0,
            '85-94%': 0,
            '70-84%': 0,
            '<70%': 0
        };

        scores.forEach(s => {
            if (s === 1) bins['perfect (100%)']++;
            else if (s >= 0.95) bins['95-99%']++;
            else if (s >= 0.85) bins['85-94%']++;
            else if (s >= 0.70) bins['70-84%']++;
            else bins['<70%']++;
        });

        print('\nCompleteness Distribution:');
        for (var bin in bins) {
            print('  ' + bin + ': ' + bins[bin]);
        }

        // Missing fields analysis
        print('\nMissing Fields Analysis:');
        var missingFields = {};
        docs.forEach(doc => {
            var missing = doc.quality_metrics?.missing_fields || [];
            missing.forEach(field => {
                missingFields[field] = (missingFields[field] || 0) + 1;
            });
        });

        var sortedFields = Object.entries(missingFields)
            .sort((a,b) => b[1] - a[1])
            .slice(0, 10);

        if (sortedFields.length === 0) {
            print('  No missing fields!');
        } else {
            sortedFields.forEach(([field, count]) => {
                var pct = (count / docs.length * 100).toFixed(1);
                print('  ' + field + ': ' + count + ' docs (' + pct + '%)');
            });
        }
    "

echo ""

# Cost Analysis
echo "[4/6] Analyzing cost metrics..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');

        var costRecords = db.cost_records.find({}).toArray();
        var enrichedDocs = db.enriched_documents.countDocuments({});

        print('\n=== COST ANALYSIS ===');
        print('Total API Calls: ' + costRecords.length);

        if (costRecords.length === 0) {
            print('No cost records found');
            quit();
        }

        // Group by model
        var byModel = {};
        var totalCost = 0;
        var totalTokens = { input: 0, output: 0 };

        costRecords.forEach(r => {
            var model = r.model || 'unknown';
            if (!byModel[model]) {
                byModel[model] = { calls: 0, cost: 0, tokens: {input: 0, output: 0} };
            }
            byModel[model].calls++;
            byModel[model].cost += r.cost_usd || 0;
            byModel[model].tokens.input += r.input_tokens || 0;
            byModel[model].tokens.output += r.output_tokens || 0;

            totalCost += r.cost_usd || 0;
            totalTokens.input += r.input_tokens || 0;
            totalTokens.output += r.output_tokens || 0;
        });

        print('Total Cost: \$' + totalCost.toFixed(2));
        print('Total Tokens: ' + (totalTokens.input + totalTokens.output));

        if (enrichedDocs > 0) {
            print('Cost per Document: \$' + (totalCost / enrichedDocs).toFixed(3));
        }

        print('\nCost by Model:');
        for (var model in byModel) {
            var m = byModel[model];
            var pct = (m.cost / totalCost * 100).toFixed(1);
            print('  ' + model + ':');
            print('    Calls: ' + m.calls);
            print('    Cost: \$' + m.cost.toFixed(3) + ' (' + pct + '%)');
            print('    Tokens: ' + (m.tokens.input + m.tokens.output));
        }

        // Task breakdown
        print('\nCost by Task:');
        var byTask = {};
        costRecords.forEach(r => {
            var task = r.task_name || 'unknown';
            if (!byTask[task]) {
                byTask[task] = { calls: 0, cost: 0 };
            }
            byTask[task].calls++;
            byTask[task].cost += r.cost_usd || 0;
        });

        var tasks = Object.entries(byTask)
            .sort((a,b) => b[1].cost - a[1].cost)
            .slice(0, 10);

        tasks.forEach(([task, t]) => {
            var pct = (t.cost / totalCost * 100).toFixed(1);
            print('  ' + task + ': \$' + t.cost.toFixed(3) + ' (' + pct + '%)');
        });
    "

echo ""

# Quality Issues
echo "[5/6] Identifying quality issues..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');

        print('\n=== QUALITY ISSUES ===');

        // Low confidence fields
        var lowConfidence = db.enriched_documents.find(
            {'quality_metrics.low_confidence_fields': {\$exists: true, \$ne: []}}
        ).toArray();

        print('Documents with Low Confidence Fields: ' + lowConfidence.length);

        if (lowConfidence.length > 0) {
            var fieldCounts = {};
            lowConfidence.forEach(doc => {
                (doc.quality_metrics?.low_confidence_fields || []).forEach(field => {
                    var fieldPath = field.field;
                    fieldCounts[fieldPath] = (fieldCounts[fieldPath] || 0) + 1;
                });
            });

            var sortedFields = Object.entries(fieldCounts)
                .sort((a,b) => b[1] - a[1])
                .slice(0, 5);

            print('Top Low Confidence Fields:');
            sortedFields.forEach(([field, count]) => {
                print('  ' + field + ': ' + count + ' docs');
            });
        }

        // Review queue analysis
        var reviewPending = db.review_queue.countDocuments({status: 'pending'});
        var reviewInProgress = db.review_queue.countDocuments({status: 'in_progress'});

        print('\nReview Queue Status:');
        print('  Pending: ' + reviewPending);
        print('  In Progress: ' + reviewInProgress);

        // Review reasons
        if (reviewPending > 0 || reviewInProgress > 0) {
            var reasons = {};
            db.review_queue.find({status: {'\$in': ['pending', 'in_progress']}}).forEach(r => {
                var reason = r.reason || 'unknown';
                reasons[reason] = (reasons[reason] || 0) + 1;
            });

            print('Review Reasons:');
            for (var reason in reasons) {
                print('  ' + reason + ': ' + reasons[reason]);
            }
        }
    "

echo ""

# Performance Summary
echo "[6/6] Calculating performance metrics..."
mongosh \
    --username "$MONGO_USER" \
    --password "$MONGO_PASSWORD" \
    --host "$MONGO_HOST:$MONGO_PORT" \
    --authenticationDatabase admin \
    --quiet \
    --eval "
        db = db.getSiblingDB('$MONGO_DB');

        print('\n=== PERFORMANCE METRICS ===');

        var jobs = db.enrichment_jobs.find({}).toArray();
        if (jobs.length === 0) {
            print('No jobs found');
            quit();
        }

        var totalDuration = 0;
        var completedJobs = 0;

        jobs.forEach(job => {
            if (job.completed_at && job.created_at) {
                var duration = (new Date(job.completed_at) - new Date(job.created_at)) / 1000;
                totalDuration += duration;
                completedJobs++;
            }
        });

        if (completedJobs > 0) {
            var avgDuration = totalDuration / completedJobs;
            print('Average Job Duration: ' + avgDuration.toFixed(1) + ' seconds');

            var totalDocs = db.enriched_documents.countDocuments({});
            var avgPerDoc = avgDuration / (totalDocs / completedJobs);
            print('Average Time per Document: ' + avgPerDoc.toFixed(1) + ' seconds');
        }

        // Success rate
        var successfulJobs = db.enrichment_jobs.countDocuments({status: 'completed'});
        var totalJobs = db.enrichment_jobs.countDocuments({});
        var successRate = ((successfulJobs / totalJobs) * 100).toFixed(1);

        print('Job Success Rate: ' + successRate + '%');
    "

echo ""
echo "================================"
echo "✓ Analysis Complete"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Review completeness metrics and identify areas for improvement"
echo "2. Check missing fields to optimize agent prompts"
echo "3. Monitor costs and compare to budget"
echo "4. Process more documents to validate results at scale"
echo ""
