#!/bin/bash

# ===========================================
# Quick GitHub Push - Simplified Version
# ===========================================
# Use this for quick pushes after first setup
# Assumes git is configured and authenticated
#
# Usage: ./push-quick.sh "Your commit message"
#        ./push-quick.sh "Your commit message" branch_name
#
# Example: ./push-quick.sh "Add Render.com config" main
# ===========================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
COMMIT_MSG="${1:-}"
BRANCH="${2:-main}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Functions
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Validation
if [ -z "$COMMIT_MSG" ]; then
    print_error "Commit message is required"
    echo "Usage: ./push-quick.sh \"Your commit message\" [branch]"
    echo "Example: ./push-quick.sh \"Add feature\" main"
    exit 1
fi

if [ ! -d "$PROJECT_DIR/.git" ]; then
    print_error "Not a git repository"
    echo "Run ./push-to-github.sh first to set up authentication"
    exit 1
fi

# Main operations
cd "$PROJECT_DIR"

print_info "Git status:"
git status --short

echo ""
read -p "Stage all changes and commit? (y/n): " CONFIRM

if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    print_info "Push cancelled"
    exit 0
fi

# Stage and commit
git add .
print_success "Changes staged"

git commit -m "$COMMIT_MSG"
print_success "Committed: $COMMIT_MSG"

# Push
print_info "Pushing to origin/$BRANCH..."
git push -u origin "$BRANCH"

print_success "Pushed to GitHub!"
print_info "Repository: $(git remote get-url origin)"
print_info "Branch: $BRANCH"
