# Quick Reference Guides

This directory contains quick reference guides and visual aids for quick lookup without diving into full documentation.

## Available Guides

### Quick Fixes & Troubleshooting

#### ARCHIPELAGO_QUICK_FIX_REFERENCE.txt
Quick fixes for common Archipelago integration issues:
- API timeout fixes
- Polling mechanism fixes
- Push flow troubleshooting
- Common error codes and solutions

**Use when:** Archipelago integration isn't working as expected

---

### Swarm Management

#### SWARM_QUICK_START.txt
Quick reference for Docker Swarm operations:
- Starting swarm mode
- Deploying services
- Scaling workers
- Monitoring services
- Common troubleshooting

**Use when:** You need quick Swarm commands

---

#### SWARM_INTEGRATION_QUICK_REFERENCE.txt
Quick reference for integrating bulk processing with Docker Swarm:
- Job coordination
- Worker communication
- Result aggregation
- Performance tuning

**Use when:** Setting up swarm-based bulk processing

---

### Testing & Verification

#### TESTING_SUMMARY.txt
Complete testing summary including:
- Test categories and coverage
- Test execution results
- Performance metrics
- Known issues and workarounds

**Use when:** Checking what's been tested and how

---

### Visual Guides

#### METADATA_EXTRACTION_VISUAL_GUIDE.txt
ASCII diagrams and visual representation of:
- Metadata extraction flow
- Data transformation pipeline
- OCR provider integration
- Result formatting

**Use when:** You need to understand the flow visually

---

### Development Notes

#### test.txt
Test notes and updates:
- Latest test results
- Recent changes
- Quick notes on development

**Use when:** Checking development status

---

## Quick Navigation

### By Problem Type

#### Getting Started
- `SWARM_QUICK_START.txt` - Start here for Swarm setup
- `TESTING_SUMMARY.txt` - Understand what works

#### Troubleshooting
- `ARCHIPELAGO_QUICK_FIX_REFERENCE.txt` - Fix Archipelago issues
- `SWARM_INTEGRATION_QUICK_REFERENCE.txt` - Fix Swarm issues

#### Understanding
- `METADATA_EXTRACTION_VISUAL_GUIDE.txt` - Visual overview
- `TESTING_SUMMARY.txt` - Coverage overview

### By System Component

#### Archipelago
- `ARCHIPELAGO_QUICK_FIX_REFERENCE.txt` - Common fixes

#### Docker Swarm
- `SWARM_QUICK_START.txt` - Quick start
- `SWARM_INTEGRATION_QUICK_REFERENCE.txt` - Integration guide

#### Metadata Extraction
- `METADATA_EXTRACTION_VISUAL_GUIDE.txt` - Visual flow

#### Testing
- `TESTING_SUMMARY.txt` - Test overview

## Format Guide

### Text Format (.txt)
- ASCII formatted for easy reading in terminal
- Organized with clear sections
- Quick lookup tables
- Code snippets where applicable

### Viewing

```bash
# View in terminal
cat ARCHIPELAGO_QUICK_FIX_REFERENCE.txt

# View with less for navigation
less SWARM_QUICK_START.txt

# Search within file
grep -i "timeout" ARCHIPELAGO_QUICK_FIX_REFERENCE.txt

# Print for reference
cat TESTING_SUMMARY.txt | lp
```

## Quick Lookup Examples

### Find Archipelago timeout solution
```bash
grep -A 5 "timeout" ARCHIPELAGO_QUICK_FIX_REFERENCE.txt
```

### Check swarm status commands
```bash
grep "status" SWARM_QUICK_START.txt
```

### See extraction workflow
```bash
cat METADATA_EXTRACTION_VISUAL_GUIDE.txt
```

## Relationship to Full Documentation

These quick references are **summaries** of full documentation:

| Quick Reference | Full Documentation |
|---|---|
| ARCHIPELAGO_QUICK_FIX_REFERENCE.txt | ../ARCHIPELAGO_INTEGRATION.md |
| SWARM_QUICK_START.txt | ../SWARM_INTEGRATION_GUIDE.md |
| SWARM_INTEGRATION_QUICK_REFERENCE.txt | ../SWARM_IMPLEMENTATION_COMPLETE.md |
| TESTING_SUMMARY.txt | ../TESTING_INDEX.md |
| METADATA_EXTRACTION_VISUAL_GUIDE.txt | ../METADATA_EXTRACTION_START_HERE.md |

**Use quick reference for:** Fast lookup, decision-making, quick fixes
**Use full documentation for:** Understanding, implementation, detailed examples

## Updating Quick References

Quick references should be:
- **Current** - Updated when significant changes occur
- **Concise** - Only essential information
- **Scannable** - Easy to find what you need
- **Practical** - Focus on actionable advice

When updating:
1. Keep information current
2. Remove outdated items
3. Add newly discovered tips
4. Cross-reference full documentation

## Tips for Effective Use

1. **Bookmark frequently used guides** in your terminal editor
2. **Print important ones** for offline reference
3. **Search within files** for quick lookup: `grep -i keyword filename`
4. **Combine with full docs** for deeper understanding
5. **Share with teammates** for common issues

## See Also

- `../INDEX.md` - Complete documentation index
- `../START_HERE.md` - Project overview
- `../../tests/README.md` - Testing guide
- `../../scripts/README.md` - Scripts guide

---

**Last Updated:** January 13, 2026
