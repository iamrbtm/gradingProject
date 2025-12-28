#!/bin/bash

# ===========================================
# GitHub Push Script with Authentication
# ===========================================
# This script safely handles GitHub credentials and pushes to your repository
# Supports both HTTPS (with credentials) and SSH authentication
#
# Usage: ./push-to-github.sh [branch] [commit-message]
# Example: ./push-to-github.sh main "Add Render.com configuration"
#
# Security: Uses git credential helper or SSH keys (never stores passwords in code)
# ===========================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ===========================================
# CONFIGURATION
# ===========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# Default values
DEFAULT_BRANCH="main"
GITHUB_USERNAME="${GITHUB_USERNAME:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
REPO_URL="${REPO_URL:-}"

# ===========================================
# HELPER FUNCTIONS
# ===========================================

print_header() {
    echo -e "\n${BLUE}===========================================\n$1\n===========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ===========================================
# VALIDATION FUNCTIONS
# ===========================================

check_git_installed() {
    print_info "Checking if Git is installed..."
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    print_success "Git is installed"
}

check_git_initialized() {
    print_info "Checking if Git repository is initialized..."
    if [ ! -d "$PROJECT_DIR/.git" ]; then
        print_error "Git repository not found at $PROJECT_DIR"
        print_info "Initializing new Git repository..."
        cd "$PROJECT_DIR"
        git init
        print_success "Git repository initialized"
    else
        print_success "Git repository found"
    fi
}

check_git_config() {
    print_header "Checking Git Configuration"
    
    # Check git username
    GIT_USERNAME=$(git config --global user.name 2>/dev/null || echo "")
    if [ -z "$GIT_USERNAME" ]; then
        print_warning "Git username not configured globally"
        read -p "Enter your Git username: " GIT_USERNAME
        git config --global user.name "$GIT_USERNAME"
        print_success "Git username set to: $GIT_USERNAME"
    else
        print_success "Git username configured: $GIT_USERNAME"
    fi
    
    # Check git email
    GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")
    if [ -z "$GIT_EMAIL" ]; then
        print_warning "Git email not configured globally"
        read -p "Enter your Git email: " GIT_EMAIL
        git config --global user.email "$GIT_EMAIL"
        print_success "Git email set to: $GIT_EMAIL"
    else
        print_success "Git email configured: $GIT_EMAIL"
    fi
}

check_github_remote() {
    print_info "Checking for GitHub remote..."
    
    REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || echo "")
    
    if [ -z "$REMOTE_URL" ]; then
        print_warning "No GitHub remote configured"
        print_info "GitHub repository URL is needed for authentication"
        read -p "Enter your GitHub repository URL (https://github.com/username/repo.git): " REPO_URL
        
        if [ -z "$REPO_URL" ]; then
            print_error "Repository URL cannot be empty"
            exit 1
        fi
        
        git remote add origin "$REPO_URL"
        print_success "GitHub remote added: $REPO_URL"
    else
        print_success "GitHub remote configured: $REMOTE_URL"
        REPO_URL="$REMOTE_URL"
    fi
}

check_authentication() {
    print_header "Checking GitHub Authentication"
    
    # Check if using SSH or HTTPS
    if [[ "$REPO_URL" == *"git@github.com"* ]]; then
        print_info "Repository uses SSH authentication"
        check_ssh_auth
    elif [[ "$REPO_URL" == *"https://"* ]]; then
        print_info "Repository uses HTTPS authentication"
        check_https_auth
    else
        print_error "Unable to determine authentication method from URL: $REPO_URL"
        exit 1
    fi
}

check_ssh_auth() {
    print_info "Testing SSH connection to GitHub..."
    
    if ssh -T git@github.com &> /dev/null; then
        print_success "SSH key is configured and working"
        AUTH_METHOD="ssh"
    else
        print_warning "SSH authentication failed"
        print_info "Options:"
        echo "  1. Set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh"
        echo "  2. Switch to HTTPS authentication"
        read -p "Do you want to switch to HTTPS? (y/n): " SWITCH_HTTPS
        
        if [[ "$SWITCH_HTTPS" =~ ^[Yy]$ ]]; then
            convert_to_https
            check_https_auth
        else
            print_error "Cannot proceed without working SSH keys"
            exit 1
        fi
    fi
}

check_https_auth() {
    print_info "Checking HTTPS authentication..."
    
    # Extract username from URL
    if [[ "$REPO_URL" =~ https://[^/]+/([^/]+)/ ]]; then
        GITHUB_USERNAME="${BASH_REMATCH[1]}"
    fi
    
    # Check if GitHub token/password is available
    if [ -z "$GITHUB_TOKEN" ]; then
        print_warning "GitHub token/password not set"
        print_info "You can provide authentication in 3 ways:"
        echo "  1. Use GITHUB_TOKEN environment variable (recommended)"
        echo "  2. Use git credential helper (will prompt)"
        echo "  3. Use personal access token"
        
        read -p "Do you have a GitHub token? (y/n): " HAS_TOKEN
        
        if [[ "$HAS_TOKEN" =~ ^[Yy]$ ]]; then
            read -sp "Enter your GitHub personal access token: " GITHUB_TOKEN
            echo ""
            
            if [ -z "$GITHUB_TOKEN" ]; then
                print_error "Token cannot be empty"
                exit 1
            fi
            
            # Test token
            if test_github_token "$GITHUB_TOKEN"; then
                print_success "GitHub token is valid"
                export GITHUB_TOKEN
                AUTH_METHOD="https"
            else
                print_error "GitHub token is invalid"
                exit 1
            fi
        else
            print_info "Git will prompt for credentials when pushing"
            AUTH_METHOD="https"
        fi
    else
        print_success "GITHUB_TOKEN environment variable is set"
        AUTH_METHOD="https"
    fi
}

test_github_token() {
    local token=$1
    local response=$(curl -s -H "Authorization: token $token" https://api.github.com/user 2>/dev/null || echo "")
    
    if echo "$response" | grep -q '"login"'; then
        return 0
    else
        return 1
    fi
}

convert_to_https() {
    print_info "Converting SSH URL to HTTPS..."
    
    # Convert git@github.com:username/repo.git to https://github.com/username/repo.git
    NEW_URL=$(echo "$REPO_URL" | sed 's/git@github.com:/https:\/\/github.com\//' | sed 's/\.git$//' | sed 's/$/.git/')
    
    git remote set-url origin "$NEW_URL"
    REPO_URL="$NEW_URL"
    print_success "Remote URL updated to: $NEW_URL"
}

# ===========================================
# GIT OPERATIONS
# ===========================================

check_git_status() {
    print_header "Git Status"
    
    cd "$PROJECT_DIR"
    
    # Check for uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        print_info "No changes to commit"
        read -p "Do you want to continue anyway? (y/n): " CONTINUE
        if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
            print_warning "Push cancelled"
            exit 0
        fi
    else
        print_info "Changes found:"
        git status --short
    fi
}

stage_changes() {
    print_header "Staging Changes"
    
    cd "$PROJECT_DIR"
    
    read -p "Stage all changes? (y/n): " STAGE_ALL
    
    if [[ "$STAGE_ALL" =~ ^[Yy]$ ]]; then
        git add .
        print_success "All changes staged"
    else
        print_info "Interactive staging mode"
        git add -p
        print_success "Changes staged interactively"
    fi
}

get_commit_message() {
    print_header "Commit Message"
    
    COMMIT_MSG="${1:-}"
    
    if [ -z "$COMMIT_MSG" ]; then
        read -p "Enter commit message: " COMMIT_MSG
    fi
    
    if [ -z "$COMMIT_MSG" ]; then
        print_error "Commit message cannot be empty"
        exit 1
    fi
    
    echo "$COMMIT_MSG"
}

commit_changes() {
    local msg=$1
    
    print_info "Committing changes..."
    
    cd "$PROJECT_DIR"
    git commit -m "$msg"
    
    print_success "Changes committed"
}

get_branch() {
    print_header "Branch Selection"
    
    BRANCH="${1:-}"
    
    if [ -z "$BRANCH" ]; then
        # Get current branch
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
        read -p "Enter branch name (current: $CURRENT_BRANCH): " BRANCH
        BRANCH="${BRANCH:-$CURRENT_BRANCH}"
    fi
    
    echo "$BRANCH"
}

push_to_github() {
    local branch=$1
    
    print_header "Pushing to GitHub"
    
    cd "$PROJECT_DIR"
    
    print_info "Pushing to origin/$branch..."
    
    if [ "$AUTH_METHOD" = "https" ] && [ -n "$GITHUB_TOKEN" ]; then
        # Use token for authentication
        git push -u origin "$branch" 2>&1 | while read line; do
            # Hide token in output
            echo "$line" | sed "s/$GITHUB_TOKEN/[REDACTED]/g"
        done
    else
        # Let git use credential helper or SSH keys
        git push -u origin "$branch"
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Successfully pushed to origin/$branch"
        return 0
    else
        print_error "Failed to push to GitHub"
        return 1
    fi
}

# ===========================================
# MAIN EXECUTION
# ===========================================

main() {
    print_header "GitHub Push Script"
    
    # Arguments
    BRANCH="${1:-$DEFAULT_BRANCH}"
    COMMIT_MSG="${2:-}"
    
    # Run all checks
    check_git_installed
    check_git_initialized
    check_git_config
    check_github_remote
    check_authentication
    
    # Git operations
    check_git_status
    stage_changes
    COMMIT_MSG=$(get_commit_message "$COMMIT_MSG")
    commit_changes "$COMMIT_MSG"
    BRANCH=$(get_branch "$BRANCH")
    push_to_github "$BRANCH"
    
    print_header "✓ Push Complete"
    print_success "Your changes have been pushed to GitHub!"
    
    # Display repository URL
    print_info "Repository: $REPO_URL"
    print_info "Branch: $BRANCH"
    
    # Show next steps for Render
    print_info "Next steps:"
    echo "  1. Go to https://dashboard.render.com"
    echo "  2. Create new Web Service"
    echo "  3. Connect this repository"
    echo "  4. Render will auto-detect render.yaml"
    echo "  5. Set environment variables in dashboard"
    echo "  6. Deploy!"
}

# Run main function with all arguments
main "$@"
