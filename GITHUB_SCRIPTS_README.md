# GitHub & Render.com Deployment Scripts

Complete bash script solution for securely pushing to GitHub and deploying to Render.com.

## 📋 Scripts Overview

### 1. `github-setup.sh` - Initial Setup (Run Once)
Sets up GitHub authentication (SSH, token, or credential helper) and configures your repository.

```bash
./github-setup.sh
```

**What it does:**
- Helps you choose authentication method
- Generates SSH keys if needed
- Configures git remotes
- Tests GitHub connection

### 2. `push-to-github.sh` - Full Featured Push
Complete push script with authentication verification and git workflow.

```bash
./push-to-github.sh [branch] [commit-message]
```

**Examples:**
```bash
# Interactive (prompts for everything)
./push-to-github.sh

# With arguments
./push-to-github.sh main "Add Render.com configuration"

# With environment variable
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
./push-to-github.sh main "Your message"
```

**What it does:**
- ✓ Validates git installation and configuration
- ✓ Checks GitHub authentication
- ✓ Prompts for commit message
- ✓ Stages and commits changes
- ✓ Pushes to GitHub
- ✓ Shows success/error clearly

### 3. `push-quick.sh` - Fast Push
Simplified script for quick pushes after initial setup.

```bash
./push-quick.sh "Your commit message" [branch]
```

**Examples:**
```bash
./push-quick.sh "Fix bug" main
./push-quick.sh "Add feature"  # Defaults to main
```

**What it does:**
- ✓ Faster than full script (no auth checks)
- ✓ Assumes you're already authenticated
- ✓ Stage, commit, and push in seconds

## 🚀 Quick Start

### First Time Setup

```bash
# 1. Initialize GitHub authentication
./github-setup.sh

# 2. Follow the prompts to choose auth method (SSH recommended)

# 3. When prompted, paste your SSH public key to GitHub
```

### First Push

```bash
# 1. Make your changes
# 2. Run the push script
./push-to-github.sh main "Add Render.com configuration"

# 3. Script will:
#    - Verify git configuration
#    - Check GitHub authentication
#    - Stage your changes
#    - Commit with your message
#    - Push to GitHub
```

### Subsequent Pushes

```bash
# Use the quick script for faster pushes
./push-quick.sh "Your commit message"

# Or use the full script with error checking
./push-to-github.sh main "Your commit message"
```

## 🔐 Authentication Methods

### Option 1: SSH Keys (Recommended)

**Advantages:**
- Most secure
- No passwords needed
- Works with credential agents
- Faster authentication

**Setup:**
```bash
# Generate key (if needed)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to GitHub
# 1. Copy: cat ~/.ssh/id_ed25519.pub
# 2. Go to https://github.com/settings/keys
# 3. Paste key and save

# Test connection
ssh -T git@github.com
```

**Repository URL:**
```
git@github.com:username/repository.git
```

### Option 2: Personal Access Token

**Advantages:**
- Easy to set up
- Can revoke easily
- More control than password
- Good for multiple machines

**Setup:**
```bash
# 1. Go to https://github.com/settings/tokens
# 2. Click "Generate new token"
# 3. Select scope: "repo" (full control of repositories)
# 4. Copy the token

# Set as environment variable
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Or save to file (secure)
echo "export GITHUB_TOKEN='ghp_xxxxxxxxxxxx'" > ~/.config/github-token
chmod 600 ~/.config/github-token
```

**Repository URL:**
```
https://github.com/username/repository.git
```

### Option 3: Git Credential Helper

**Advantages:**
- No tokens to manage
- Uses system keychain
- Automatic caching

**Setup:**

**macOS:**
```bash
git config --global credential.helper osxkeychain
```

**Linux:**
```bash
git config --global credential.helper cache
# Or: git config --global credential.helper store
```

**Windows:**
- Built-in by default

**Repository URL:**
```
https://github.com/username/repository.git
```

## 📝 Environment Variables

Use these to avoid prompts:

```bash
# GitHub credentials (for HTTPS auth)
export GITHUB_USERNAME="your_username"
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Repository configuration
export REPO_URL="https://github.com/username/repository.git"
```

**Save to shell profile:**

```bash
# Add to ~/.bashrc, ~/.zshrc, or ~/.bash_profile:
source ~/.config/github-env

# Then source it:
source ~/.bashrc
```

## 🔍 Verification & Testing

### Test SSH Connection
```bash
ssh -T git@github.com
# Should show: Hi username! You've successfully authenticated...
```

### Test GitHub Token
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
# Should show your user info
```

### Check Git Configuration
```bash
git config --list | grep user
git remote -v
```

### View Git Status
```bash
git status
git log --oneline -5
```

## 🛠️ Script Features

### Security
- ✓ Never stores passwords in code
- ✓ Masks tokens in output
- ✓ Validates credentials before pushing
- ✓ Uses git credential helpers safely
- ✓ Permissions set to 600 for sensitive files

### Usability
- ✓ Colorized output (success/error/info)
- ✓ Interactive prompts for missing info
- ✓ Helpful error messages
- ✓ Works with or without arguments
- ✓ Supports both SSH and HTTPS

### Reliability
- ✓ Checks git is installed
- ✓ Initializes repo if needed
- ✓ Validates git configuration
- ✓ Tests authentication before push
- ✓ Clear success/error reporting

## 🐛 Troubleshooting

### "SSH key is not configured"
```bash
# Generate new key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Add to ssh-agent
ssh-add ~/.ssh/id_ed25519

# Add to GitHub
# https://github.com/settings/keys
```

### "Repository not found" or "Permission denied"
```bash
# Check remote URL
git remote -v

# Update if needed
git remote set-url origin https://github.com/username/repo.git

# Test access
git remote show origin
```

### "Token is invalid"
```bash
# Create new token at https://github.com/settings/tokens
# Make sure it has "repo" scope

# Test token
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user
```

### "fatal: not a git repository"
```bash
# Initialize git
git init

# Or run the setup script
./github-setup.sh
```

### "fatal: 'origin' does not appear to be a git repository"
```bash
# Add remote
git remote add origin https://github.com/username/repo.git

# Verify
git remote -v
```

## 📋 Deployment Workflow

### Complete Flow

```bash
# 1. Setup (once)
./github-setup.sh

# 2. Make changes to your code
# (Edit files, test locally, etc.)

# 3. Push to GitHub
./push-to-github.sh main "Your commit message"

# 4. Deploy to Render
# - Go to https://dashboard.render.com
# - Create new Web Service
# - Connect your GitHub repository
# - Render auto-detects render.yaml
# - Set environment variables
# - Click "Create Web Service"
```

### Subsequent Deploys

```bash
# Make changes
# ...

# Push to GitHub
./push-quick.sh "Your commit message"

# Render auto-deploys from GitHub!
```

## 🎯 Integration with Render.com

After pushing to GitHub:

1. **Go to Render dashboard**: https://dashboard.render.com
2. **Create new Web Service**:
   - Click "New" → "Web Service"
   - Connect GitHub account
   - Select this repository
3. **Render detects render.yaml**:
   - Automatically uses our Render configuration
   - Configures PostgreSQL database
   - Configures Redis cache
4. **Set environment variables**:
   - `FLASK_SECRET_KEY` (generate: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `API_TOKEN_ENCRYPTION_KEY`
   - `MAIL_USERNAME` / `MAIL_PASSWORD` (if using email)
   - Other settings from `RENDER_ENV_SETUP.md`
5. **Deploy**:
   - Click "Create Web Service"
   - Render builds and deploys automatically
   - Application is live!

## 📚 Additional Resources

- **GitHub Authentication**: https://docs.github.com/en/authentication
- **SSH Keys**: https://docs.github.com/en/authentication/connecting-to-github-with-ssh
- **Personal Access Tokens**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
- **Render.com Deployment**: https://render.com/docs
- **Infrastructure as Code**: https://render.com/docs/infrastructure-as-code
- **Flask Deployment**: https://flask.palletsprojects.com/deployment/

## 💡 Tips

- **Use SSH for security**: SSH keys are more secure than tokens
- **Keep tokens safe**: Never commit tokens to git
- **Use credential helpers**: Cache credentials securely on your machine
- **Test before pushing**: Run `git status` and review changes
- **Write meaningful commits**: Use clear, descriptive commit messages
- **Automate deployment**: Render auto-deploys on GitHub push

## 📞 Support

For issues with:
- **GitHub**: https://github.com/contact
- **Git**: https://git-scm.com/
- **SSH**: https://man.openbsd.org/ssh
- **Render.com**: https://support.render.com

## ✅ Verification Checklist

Before pushing:
- [ ] Made changes to your code
- [ ] Tested locally
- [ ] Ran `git status` to see changes
- [ ] Commit message is descriptive
- [ ] GitHub authentication is set up
- [ ] You're pushing to the correct branch

After pushing:
- [ ] Check GitHub to confirm push succeeded
- [ ] View code on GitHub repository
- [ ] Set environment variables in Render
- [ ] Watch deployment in Render dashboard
- [ ] Test your application

## 🚀 You're Ready!

```bash
# Everything is set up. Now you can:
./push-to-github.sh main "Your message"

# And Render will automatically deploy! 🎉
```

Happy deploying! 🚀
