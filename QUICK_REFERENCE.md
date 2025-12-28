# Quick Reference Card - GitHub & Render Deployment

## TL;DR - First Time Setup

```bash
# 1. Setup GitHub authentication (choose SSH or Token)
./github-setup.sh

# 2. Push to GitHub
./push-to-github.sh main "Add Render.com configuration"

# 3. Go to https://dashboard.render.com
# 4. Connect GitHub → Select repository
# 5. Set environment variables (FLASK_SECRET_KEY, etc.)
# 6. Click "Create Web Service"
# 7. Done! Your app deploys automatically
```

## Command Reference

### GitHub Push Scripts

| Task | Command |
|------|---------|
| **First-time setup** | `./github-setup.sh` |
| **Full push (with checks)** | `./push-to-github.sh main "message"` |
| **Quick push** | `./push-quick.sh "message"` |
| **Check status** | `git status` |
| **View commits** | `git log --oneline -5` |

### Useful Git Commands

```bash
# Show what changed
git status
git diff

# View commit history
git log --oneline -10

# Show which branch you're on
git branch

# Add all changes
git add .

# Commit with message
git commit -m "Your message"

# Push to GitHub
git push

# Check remote URL
git remote -v
```

## Key Files Explained

| File | Purpose | When to Use |
|------|---------|-----------|
| `render.yaml` | Render infrastructure config | Never edit unless deployment specs change |
| `Dockerfile.render` | Docker image for Render | Never edit unless dependencies change |
| `requirements-render.txt` | Production dependencies | Edit when adding/removing packages |
| `.dockerignore` | Docker build optimization | Usually don't need to edit |
| `github-setup.sh` | GitHub authentication setup | Run once, first time |
| `push-to-github.sh` | Full-featured push script | Use for careful pushes with validation |
| `push-quick.sh` | Fast push script | Use after setup for quick pushes |

## Authentication Methods (Choose One)

### Option 1: SSH Keys (Recommended)
```bash
# Generate (if needed)
ssh-keygen -t ed25519 -C "your@email.com"

# Add to GitHub: https://github.com/settings/keys

# Test
ssh -T git@github.com

# Repository URL
git@github.com:username/repo.git
```

### Option 2: Personal Access Token
```bash
# Create at https://github.com/settings/tokens
# Select scope: "repo"

# Use
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
./push-to-github.sh main "message"

# Repository URL
https://github.com/username/repo.git
```

### Option 3: Git Credential Helper (macOS)
```bash
git config --global credential.helper osxkeychain
# Then git will use macOS Keychain

# Repository URL
https://github.com/username/repo.git
```

## Deployment Workflow

### Initial Deploy
```
1. ./github-setup.sh               (setup auth once)
2. ./push-to-github.sh main "msg"  (push code)
3. Create Render service           (https://dashboard.render.com)
4. Set environment variables       (FLASK_SECRET_KEY, etc)
5. Wait for deployment             (5-10 minutes)
6. Test at https://your-app.onrender.com/health
```

### Subsequent Updates
```
1. Make code changes locally
2. ./push-quick.sh "message"       (push to GitHub)
3. Render auto-deploys             (automatic!)
```

## Important Environment Variables

**Must Set in Render Dashboard:**
- `FLASK_SECRET_KEY` - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
- `API_TOKEN_ENCRYPTION_KEY` - Your existing or new key
- `FLASK_ENV` - Set to `production`
- `USE_HTTPS` - Set to `true`

**Auto-Set by Render:**
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection

See `RENDER_ENV_SETUP.md` for complete list.

## Troubleshooting Quick Fixes

### "SSH key not working"
```bash
ssh -T git@github.com
# If fails, run: ./github-setup.sh
```

### "Remote not found"
```bash
git remote add origin https://github.com/username/repo.git
git branch -M main
git push -u origin main
```

### "Permission denied" on script
```bash
chmod +x push-to-github.sh push-quick.sh github-setup.sh
```

### "Cannot connect to database"
- Verify DATABASE_URL in Render environment variables
- Wait for PostgreSQL service to fully start
- Check Render logs for errors

### "Health check failing"
- Verify Flask /health endpoint exists
- Check all environment variables are set correctly
- Review Render logs for startup errors

## File Locations

```
Your Project Root
├── github-setup.sh              ← Run this first
├── push-to-github.sh            ← Then use this
├── push-quick.sh                ← Then use this for updates
├── render.yaml                  ← For Render infrastructure
├── Dockerfile.render            ← For Docker image
├── requirements-render.txt      ← Production dependencies
└── DEPLOYMENT_SUMMARY.md        ← Full instructions
```

## Security Reminders

- ✅ Never commit `.env` files
- ✅ Never hardcode secrets in code
- ✅ Never share tokens/passwords
- ✅ Use Render "Secrets" for sensitive variables
- ✅ SSH keys are more secure than tokens
- ✅ Rotate tokens periodically
- ✅ Revoke old tokens when not needed

## Cost Estimate

- **Web Service** (Standard): ~$7-12/month
- **PostgreSQL** (Starter): ~$7/month
- **Redis** (Starter): ~$6/month
- **Total**: ~$20-25/month

Can reduce to ~$13/month by using "starter" plans for dev.

## Key Links

- **Render Dashboard**: https://dashboard.render.com
- **GitHub Settings**: https://github.com/settings/
- **SSH Keys**: https://github.com/settings/keys
- **Personal Tokens**: https://github.com/settings/tokens
- **Render Docs**: https://render.com/docs

## One-Liner Cheat Sheet

```bash
# First time: setup
./github-setup.sh && ./push-to-github.sh main "Initial setup"

# Regular pushes
./push-quick.sh "Your commit message"

# Check everything
git status && git log --oneline -3 && git remote -v

# Generate a secure secret
python -c "import secrets; print(secrets.token_hex(32))"

# Test GitHub SSH
ssh -T git@github.com

# Test GitHub token
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

## Deployment Checklist

### Before First Push
- [ ] Git initialized in project
- [ ] `./github-setup.sh` run successfully
- [ ] SSH keys or token configured
- [ ] Repository URL correct
- [ ] `.env` files not committed

### Before Render Deploy
- [ ] Code pushed to GitHub
- [ ] All files visible on GitHub
- [ ] Render account created
- [ ] GitHub connected to Render
- [ ] render.yaml present in repo

### After Render Deploy
- [ ] All environment variables set
- [ ] Database service running
- [ ] Redis service running
- [ ] Health check passes
- [ ] App accessible at provided URL
- [ ] Features tested

## Next Steps

1. **Right now**: `./github-setup.sh`
2. **Next**: `./push-to-github.sh main "Add Render config"`
3. **Then**: Go to https://dashboard.render.com
4. **Finally**: Set environment variables and deploy

## More Help

- **Full Guide**: `DEPLOYMENT_SUMMARY.md`
- **GitHub Auth**: `GITHUB_PUSH_GUIDE.md`
- **Scripts Help**: `GITHUB_SCRIPTS_README.md`
- **Render Config**: `RENDER_ENV_SETUP.md`
- **Build Details**: `RENDER_BUILD_GUIDE.md`

---

**You've got this! 🚀**

Questions? Check the detailed guides above or ask in the Render/GitHub documentation.
