# GitHub Push Script - Quick Start Guide

## Overview

The `push-to-github.sh` script provides a secure, user-friendly way to push your code to GitHub with automatic authentication setup.

## Features

✅ **Automatic Authentication Setup**
- Detects SSH vs HTTPS configuration
- Tests SSH keys and validates tokens
- Falls back gracefully if authentication fails

✅ **Security**
- Never stores passwords in code
- Supports GitHub personal access tokens
- Masks tokens in output
- Can use SSH keys or git credential helper

✅ **User-Friendly**
- Colorized output for easy reading
- Interactive prompts for missing information
- Shows helpful guidance at each step

✅ **Git Configuration Management**
- Auto-configures git username/email if needed
- Sets up remote URL automatically
- Validates git repository

## Prerequisites

1. **Git installed**: `git --version`
2. **GitHub account**: https://github.com
3. **Authentication method**:
   - **SSH keys** (recommended for security)
   - **Personal access token** (easier to set up)
   - **Password** (via git credential helper)

## Setup Options

### Option 1: SSH Keys (Recommended)

SSH keys provide the most secure authentication without needing to store tokens.

**Check if you have SSH keys:**
```bash
ls -la ~/.ssh/
```

**Generate new SSH keys (if needed):**
```bash
ssh-keygen -t ed25519 -C "rbtm2006@me.com"
# Or for older systems:
# ssh-keygen -t rsa -b 4096 -C "rbtm2006@me.com"
```

**Add SSH key to GitHub:**
1. Copy your public key: `cat ~/.ssh/id_ed25519.pub`
2. Go to https://github.com/settings/keys
3. Click "New SSH key"
4. Paste your key and save

**Update repository to use SSH:**
```bash
# If you have HTTPS URL, convert to SSH
git remote set-url origin git@github.com:username/repo.git
```

### Option 2: GitHub Personal Access Token

Easier than SSH but requires managing a token.

**Create a token:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token"
3. Select scopes: `repo` (full control of private repositories)
4. Copy the token (you won't see it again!)

**Use the token:**
```bash
# Option A: Set environment variable
export GITHUB_TOKEN="your_token_here"
./push-to-github.sh main "Your commit message"

# Option B: Script will prompt for it
./push-to-github.sh main "Your commit message"
```

### Option 3: Git Credential Helper

Let git handle credentials securely (platform-specific).

**macOS (recommended):**
```bash
git config --global credential.helper osxkeychain
```

**Linux:**
```bash
git config --global credential.helper cache
# Or use pass, store, or other credential managers
```

**Windows:**
Windows Credential Manager is usually configured by default.

## Usage

### Basic Usage

```bash
# Simplest way - script prompts for everything
./push-to-github.sh

# With branch and commit message
./push-to-github.sh main "Add Render.com configuration"

# With environment variable (no prompts)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
./push-to-github.sh main "Your commit message"
```

### Examples

```bash
# Push to main branch with commit message
./push-to-github.sh main "Add Render.com configuration"

# Push to develop branch
./push-to-github.sh develop "Fix bug in authentication"

# Interactive mode (answers all questions)
./push-to-github.sh
```

## What the Script Does

1. **Validates Environment**
   - Checks if Git is installed
   - Initializes repository if needed
   - Verifies git username/email configuration

2. **Sets Up Remote**
   - Checks for existing GitHub remote
   - Adds remote URL if not present
   - Converts between SSH/HTTPS if needed

3. **Handles Authentication**
   - Tests SSH keys or GitHub token
   - Provides helpful guidance if auth fails
   - Masks tokens in output

4. **Performs Git Operations**
   - Shows current changes
   - Stages files (all or interactive)
   - Creates commit with message
   - Selects target branch
   - Pushes to GitHub

5. **Reports Status**
   - Shows success/error clearly
   - Displays repository URL and branch
   - Provides next steps for Render.com deployment

## Troubleshooting

### "SSH key is not configured"

```bash
# Test SSH connection
ssh -T git@github.com

# If this fails, generate new key:
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add key to ssh-agent:
ssh-add ~/.ssh/id_ed25519
```

### "GitHub token is invalid"

```bash
# Verify token works:
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user

# Create new token if expired:
# https://github.com/settings/tokens
```

### "Remote 'origin' already exists"

The script will use your existing remote. If it's wrong:

```bash
git remote remove origin
# Then run the script again to add correct URL
```

### "fatal: not a git repository"

```bash
# Initialize git if not already done:
git init

# Or run the script - it will do this for you
./push-to-github.sh
```

### "Everything is up to date"

No changes to commit. Either:
1. You haven't made any changes since last commit
2. Try: `git status` to see what files are modified
3. Make sure you're in the project directory

## Setting Environment Variables (Recommended for CI/CD)

To avoid being prompted every time, set environment variables:

```bash
# In your shell profile (~/.bash_profile, ~/.zshrc, etc.):
export GITHUB_USERNAME="your_github_username"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Source the file to apply:
source ~/.bash_profile

# Verify:
echo $GITHUB_TOKEN
```

**Security Note**: Only do this on your local machine. Never commit tokens to a repository!

## Script Permissions

The script needs execute permission:

```bash
# Already set, but if needed:
chmod +x push-to-github.sh

# Run it:
./push-to-github.sh
```

## After Push: Deploy to Render

Once your code is pushed to GitHub:

1. Go to https://dashboard.render.com
2. Click "New Web Service"
3. Connect your GitHub account
4. Select this repository
5. Render will auto-detect `render.yaml`
6. Set environment variables in the Render dashboard
7. Click "Create Web Service" to deploy!

## Environment Variables Reference

To use the script securely with environment variables:

```bash
# Basic variables
export GITHUB_USERNAME="your_username"

# Authentication (choose one):
# Option 1: Personal access token
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Option 2: SSH (just make sure keys are in ~/.ssh/)
# No env var needed, just works automatically

# Optional: Repository URL (if script can't detect it)
export REPO_URL="https://github.com/username/repo.git"

# Then run:
./push-to-github.sh main "Your commit message"
```

## Manual Git Commands (If You Prefer)

If you'd rather use git directly:

```bash
# Stage changes
git add .

# Commit
git commit -m "Your message"

# Push
git push -u origin main

# Or if you want to set up SSH/HTTPS first:
git remote add origin https://github.com/username/repo.git
git branch -M main
git push -u origin main
```

## Tips

- **Test your authentication first**: `ssh -T git@github.com` (SSH) or `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user` (HTTPS)
- **Keep your token safe**: Never commit it to git
- **Use SSH for security**: SSH keys are more secure than tokens
- **Store token in 1Password/LastPass**: For secure storage
- **Use git credential helper**: Caches credentials securely on your machine

## Advanced: Using with Other CI/CD Tools

The script can be used in GitHub Actions or other CI/CD:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Render

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Push changes
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: ./push-to-github.sh main "CI/CD deploy"
```

## Getting Help

```bash
# View the script
cat push-to-github.sh

# Check git status
git status

# Check remotes
git remote -v

# Check git config
git config --list

# Test connection
ssh -T git@github.com
```

## Next Steps

1. Choose authentication method (SSH or Token)
2. Set up GitHub remote URL
3. Run the script: `./push-to-github.sh main "Your message"`
4. Deploy to Render.com from GitHub
5. Set environment variables in Render dashboard
6. Watch your app deploy!

Happy deploying! 🚀
