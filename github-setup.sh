#!/bin/bash

# ===========================================
# GitHub Setup Helper
# ===========================================
# This script helps with initial GitHub configuration
# Run this once before using push-to-github.sh
#
# Usage: ./github-setup.sh
# ===========================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}===========================================\n$1\n===========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_header "GitHub Setup Helper"

# 1. Check GitHub authentication method
print_info "Choose your GitHub authentication method:"
echo "  1) SSH Keys (Recommended - Most Secure)"
echo "  2) Personal Access Token (Easier Setup)"
echo "  3) Git Credential Helper (Platform-Specific)"
read -p "Select option (1-3): " AUTH_CHOICE

case $AUTH_CHOICE in
    1)
        print_header "Setting Up SSH Keys"
        
        # Check for existing SSH key
        if [ -f ~/.ssh/id_ed25519 ]; then
            print_success "SSH key found at ~/.ssh/id_ed25519"
            PUBKEY=$(cat ~/.ssh/id_ed25519.pub)
        elif [ -f ~/.ssh/id_rsa ]; then
            print_success "SSH key found at ~/.ssh/id_rsa"
            PUBKEY=$(cat ~/.ssh/id_rsa.pub)
        else
            print_error "No SSH key found"
            print_info "Generating new SSH key..."
            
            read -p "Enter your email (for SSH key): " EMAIL
            ssh-keygen -t ed25519 -C "$EMAIL" -f ~/.ssh/id_ed25519 -N ""
            
            print_success "SSH key generated at ~/.ssh/id_ed25519"
            PUBKEY=$(cat ~/.ssh/id_ed25519.pub)
            
            # Add to ssh-agent
            eval "$(ssh-agent -s)"
            ssh-add ~/.ssh/id_ed25519
            print_success "SSH key added to ssh-agent"
        fi
        
        print_header "Your SSH Public Key"
        echo "$PUBKEY"
        echo ""
        print_info "Next steps:"
        echo "  1. Go to https://github.com/settings/keys"
        echo "  2. Click 'New SSH key'"
        echo "  3. Paste the key above"
        echo "  4. Click 'Add SSH key'"
        
        read -p "Have you added the key to GitHub? (y/n): " ADDED_KEY
        
        if [[ "$ADDED_KEY" =~ ^[Yy]$ ]]; then
            print_info "Testing SSH connection..."
            if ssh -T git@github.com 2>&1 | grep -q "Hi.*successfully"; then
                print_success "SSH connection successful!"
            else
                ssh -T git@github.com
                print_error "SSH connection failed. Check the error above."
            fi
        fi
        
        print_info "Repository URL format for SSH:"
        echo "  git@github.com:username/repository.git"
        ;;
        
    2)
        print_header "Setting Up Personal Access Token"
        
        print_info "Steps to create a Personal Access Token:"
        echo "  1. Go to https://github.com/settings/tokens"
        echo "  2. Click 'Generate new token'"
        echo "  3. Set name: 'Grading Project Token'"
        echo "  4. Select scopes:"
        echo "     ☑ repo (full control of private repositories)"
        echo "  5. Click 'Generate token'"
        echo "  6. Copy the token (you won't see it again!)"
        echo ""
        
        read -sp "Paste your GitHub token here: " GITHUB_TOKEN
        echo ""
        
        # Test token
        print_info "Testing token..."
        if curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user | grep -q '"login"'; then
            print_success "Token is valid!"
            
            # Offer to save to environment
            read -p "Save token to ~/.github-token (secure file)? (y/n): " SAVE_TOKEN
            if [[ "$SAVE_TOKEN" =~ ^[Yy]$ ]]; then
                mkdir -p ~/.config
                echo "export GITHUB_TOKEN='$GITHUB_TOKEN'" > ~/.config/github-token
                chmod 600 ~/.config/github-token
                print_success "Token saved to ~/.config/github-token"
                print_info "Add to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
                echo "  source ~/.config/github-token"
            fi
        else
            print_error "Token is invalid. Check the token and try again."
        fi
        
        print_info "Repository URL format for HTTPS:"
        echo "  https://github.com/username/repository.git"
        ;;
        
    3)
        print_header "Setting Up Git Credential Helper"
        
        OS_TYPE=$(uname -s)
        
        if [[ "$OS_TYPE" == "Darwin" ]]; then
            print_info "Setting up macOS Keychain..."
            git config --global credential.helper osxkeychain
            print_success "Git credential helper set to osxkeychain"
            print_info "Git will now prompt for credentials and cache them securely"
            
        elif [[ "$OS_TYPE" == "Linux" ]]; then
            print_info "Available credential helpers:"
            echo "  - cache (fastest, 15min timeout)"
            echo "  - store (simplest, saved in ~/.git-credentials)"
            echo "  - pass (secure, uses pass package)"
            read -p "Choose helper (cache/store/pass): " HELPER_TYPE
            
            git config --global credential.helper "$HELPER_TYPE"
            print_success "Git credential helper set to $HELPER_TYPE"
            
        elif [[ "$OS_TYPE" == "MINGW64_NT"* ]] || [[ "$OS_TYPE" == "MSYS_NT"* ]]; then
            print_info "Windows uses built-in Credential Manager"
            print_success "No additional setup needed"
            
        else
            print_error "Unknown OS: $OS_TYPE"
        fi
        
        print_info "Repository URL format for HTTPS:"
        echo "  https://github.com/username/repository.git"
        ;;
        
    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

# 2. Get repository URL
print_header "Repository Configuration"

CURRENT_REMOTE=$(git config --get remote.origin.url 2>/dev/null || echo "")

if [ -n "$CURRENT_REMOTE" ]; then
    print_success "Current remote: $CURRENT_REMOTE"
    read -p "Change remote? (y/n): " CHANGE_REMOTE
else
    CHANGE_REMOTE="y"
fi

if [[ "$CHANGE_REMOTE" =~ ^[Yy]$ ]]; then
    read -p "Enter your GitHub username: " GITHUB_USERNAME
    read -p "Enter your repository name: " REPO_NAME
    
    case $AUTH_CHOICE in
        1)
            REPO_URL="git@github.com:$GITHUB_USERNAME/$REPO_NAME.git"
            ;;
        *)
            REPO_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
            ;;
    esac
    
    if [ -n "$CURRENT_REMOTE" ]; then
        git remote set-url origin "$REPO_URL"
        print_success "Remote updated: $REPO_URL"
    else
        git remote add origin "$REPO_URL"
        print_success "Remote added: $REPO_URL"
    fi
fi

# 3. Test connection
print_header "Testing Connection"

if [[ "$AUTH_CHOICE" == "1" ]]; then
    print_info "Testing SSH connection..."
    if ssh -T git@github.com 2>&1 | grep -q "Hi"; then
        print_success "SSH connection successful"
    else
        print_error "SSH connection failed"
        exit 1
    fi
else
    print_info "Skipping connection test (will test on first push)"
fi

# 4. Final summary
print_header "✓ GitHub Setup Complete"

print_info "Your configuration:"
git config --list | grep -E "user\.(name|email)|remote\.origin"

echo ""
print_info "Next steps:"
echo "  1. Set git user name: git config --global user.name 'Your Name'"
echo "  2. Set git user email: git config --global user.email 'your@email.com'"
echo "  3. Create initial commit: ./push-to-github.sh"
echo ""
print_success "Ready to push to GitHub!"
