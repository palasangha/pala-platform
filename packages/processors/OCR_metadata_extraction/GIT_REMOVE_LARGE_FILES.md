# Git Commands to Remove TAR and DEB Files from Repository

This guide provides step-by-step Git commands to remove large binary files (`.tar` and `.deb`) from your repository history.

## Option 1: Using Interactive Rebase (For Recent Commits)

If the commit is recent (within last few commits), use interactive rebase:

```bash
# Start interactive rebase from the commit before the one with large files
git rebase -i COMMIT_HASH^

# In the editor, change 'pick' to 'edit' for the commit containing large files
# Save and exit the editor

# Remove the large files
git rm cloudflared.deb mygvpocr-worker.tar

# Stage the changes
git add .

# Amend the commit
git commit --amend --no-edit

# Continue the rebase
git rebase --continue
```

## Option 2: Using git reset + Manual Checkout (Cleanest Approach)

This approach recreates the commit without the large files:

```bash
# Reset to the commit before the problematic commit
git reset --hard PARENT_COMMIT_HASH

# Stash any uncommitted changes
git stash

# List files from the old commit (excluding the large files)
git show OLD_COMMIT_HASH --name-only | grep -v "\.tar\|\.deb"

# Checkout files from the old commit (example)
git show OLD_COMMIT_HASH:.cloudflared/cert.pem > .cloudflared/cert.pem
git show OLD_COMMIT_HASH:Caddyfile > Caddyfile
# ... repeat for each file you want to keep

# Stage all files
git add .

# Create new commit with original author info
GIT_AUTHOR_DATE="ORIGINAL_DATE" GIT_COMMITTER_DATE="ORIGINAL_DATE" \
  git commit -m "commit message" --author="Author Name <email>"

# Cherry-pick any subsequent commits
git cherry-pick NEXT_COMMIT_HASH
```

## Option 3: Using git filter-branch (For Multiple Commits)

For removing files from multiple commits across the history:

```bash
# Install git-filter-repo (recommended over filter-branch)
pip install git-filter-repo

# Remove specific files from all commits
git filter-repo --invert-paths --paths cloudflared.deb --paths mygvpocr-worker.tar

# Or using git filter-branch (older method)
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f \
  --tree-filter 'rm -f cloudflared.deb mygvpocr-worker.tar' \
  -- --all
```

## Option 4: Using git bfg (Fastest for Large Files)

Install and use BFG Repo-Cleaner:

```bash
# Install BFG
# macOS: brew install bfg
# Linux: apt-get install bfg (or download from https://rtyley.github.io/bfg-repo-cleaner/)

# Remove files by extension
bfg --delete-files '*.tar' --delete-files '*.deb' .

# Or remove specific files
bfg --delete-files 'cloudflared.deb' --delete-files 'mygvpocr-worker.tar' .

# Clean up reflog
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

## Useful Diagnostic Commands

```bash
# Check if a file exists in a commit
git ls-tree -r COMMIT_HASH | grep -E "\.tar|\.deb"

# Show which commits modified a file
git log --all --full-history -- "*.deb"

# See total size of files
git rev-list --all --objects | grep -E "\.tar|\.deb" | sort -k2

# List all files in a specific commit
git show COMMIT_HASH --name-only

# Get original commit date for preserving
git log -1 --format=%aI COMMIT_HASH
```

## After Removing Files

```bash
# Verify the files are gone
git log --all --name-only | grep -E "\.tar|\.deb"

# Force push to remote (use with caution!)
git push origin BRANCH_NAME -f

# Or create a new branch
git push origin NEW_BRANCH_NAME

# Clean up local repository
git gc --aggressive --prune=now
```

## Important Notes

⚠️ **WARNING:** These operations rewrite history. Before proceeding:

1. **Backup your repository:**
   ```bash
   git clone --mirror /path/to/repo /path/to/backup.git
   ```

2. **Only do this if:**
   - The commit hasn't been pushed to shared remote, OR
   - You can force-push and coordinate with team members

3. **Coordinate with team:** If others have cloned the repo, they'll need to:
   ```bash
   git fetch origin
   git reset --hard origin/BRANCH_NAME
   ```

4. **Verify changes:** Always verify the files are removed before pushing:
   ```bash
   git log -p --all -- cloudflared.deb
   git log -p --all -- mygvpocr-worker.tar
   ```

## Example: Removing from commit d0afe0b

```bash
# Reset to parent commit
git reset --hard bab6eb9

# List files to keep (exclude .tar and .deb)
git show d0afe0b --name-only | grep -v "cloudflared.deb\|mygvpocr-worker.tar"

# Checkout each file (create directories first)
mkdir -p certs .cloudflared
git show d0afe0b:certs/docgenai.com-key.pem > certs/docgenai.com-key.pem
# ... repeat for all needed files

# Commit with original date/author
git add .
GIT_AUTHOR_DATE="Sun Dec 14 17:15:06 2025 +0530" \
  GIT_COMMITTER_DATE="Sun Dec 14 17:15:06 2025 +0530" \
  git commit -m "solved the google login issue" \
  --author="Bhushan Gawai <bhushan0508@gmail.com>"

# Cherry-pick any subsequent commits
git cherry-pick fc57d58
```

## Quick Reference Cheat Sheet

```bash
# Remove files from last commit before pushing
git rm large_file.tar
git commit --amend --no-edit

# Remove files from specific commit (interactive rebase)
git rebase -i COMMIT_HASH^
# Change 'pick' to 'edit', then git rm FILENAME, git add ., git commit --amend

# Check file sizes in git
git rev-list --all --objects | sort -k2 | tail -20

# Find and list all tar/deb files in history
git log --all --full-history -- '*.tar' '*.deb'

# Restore deleted files
git checkout COMMIT_HASH -- deleted_file.tar
```
