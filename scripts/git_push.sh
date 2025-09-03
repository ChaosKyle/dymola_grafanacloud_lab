#!/bin/bash

# Git Push Script with Interactive Commit Message
# Automates the git add, commit, and push workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Check if we're in a git repository
check_git_repo() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not in a git repository!"
        exit 1
    fi
}

# Check for uncommitted changes
check_changes() {
    if git diff --quiet && git diff --cached --quiet; then
        warning "No changes detected to commit"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Exiting..."
            exit 0
        fi
    fi
}

# Show current git status
show_status() {
    log "Current git status:"
    echo "======================="
    git status --short
    echo "======================="
    echo
}

# Show diff summary
show_diff_summary() {
    if ! git diff --quiet || ! git diff --cached --quiet; then
        log "Changes summary:"
        echo "======================="
        
        # Show file statistics
        echo -e "${PURPLE}Files changed:${NC}"
        git diff --stat HEAD 2>/dev/null || git diff --stat
        echo
        
        # Show added/modified/deleted counts
        ADDED=$(git diff --name-status HEAD 2>/dev/null | grep -c '^A' || echo "0")
        MODIFIED=$(git diff --name-status HEAD 2>/dev/null | grep -c '^M' || echo "0") 
        DELETED=$(git diff --name-status HEAD 2>/dev/null | grep -c '^D' || echo "0")
        
        echo "Added: $ADDED, Modified: $MODIFIED, Deleted: $DELETED"
        echo "======================="
        echo
    fi
}

# Get commit message from user
get_commit_message() {
    echo -e "${BLUE}Enter your commit message:${NC}"
    echo "----------------------------------------"
    echo "Tip: First line should be a brief summary (50 chars or less)"
    echo "Add blank line, then detailed description if needed"
    echo "Press Ctrl+D when finished, or Ctrl+C to cancel"
    echo "----------------------------------------"
    echo
    
    # Read multi-line input
    COMMIT_MESSAGE=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        COMMIT_MESSAGE="${COMMIT_MESSAGE}${line}"$'\n'
    done
    
    # Remove trailing newline
    COMMIT_MESSAGE="${COMMIT_MESSAGE%$'\n'}"
    
    if [[ -z "$COMMIT_MESSAGE" ]]; then
        error "Empty commit message. Aborting."
        exit 1
    fi
}

# Preview commit message
preview_commit() {
    echo
    log "Commit message preview:"
    echo "======================="
    echo -e "${PURPLE}${COMMIT_MESSAGE}${NC}"
    echo "======================="
    echo
    
    read -p "Proceed with this commit message? (Y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        log "Commit cancelled by user"
        exit 0
    fi
}

# Add attribution
add_attribution() {
    local attribution="

Generated with love via AI prompts by Grok 4 and Claude Code for execution. 
ChaosKyle human in loop.

Co-Authored-By: Claude <noreply@anthropic.com>"
    
    COMMIT_MESSAGE="${COMMIT_MESSAGE}${attribution}"
}

# Perform git operations
do_git_operations() {
    log "Adding all changes to staging area..."
    git add .
    
    if git diff --cached --quiet; then
        warning "No changes staged for commit"
        exit 0
    fi
    
    log "Creating commit..."
    git commit -m "$COMMIT_MESSAGE"
    
    # Get the commit hash
    COMMIT_HASH=$(git rev-parse --short HEAD)
    success "Commit created: $COMMIT_HASH"
    
    # Ask about pushing
    read -p "Push to remote repository? (Y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        log "Pushing to remote..."
        
        # Get current branch
        CURRENT_BRANCH=$(git branch --show-current)
        
        # Check if remote exists
        if git remote get-url origin > /dev/null 2>&1; then
            git push origin "$CURRENT_BRANCH"
            success "Successfully pushed to origin/$CURRENT_BRANCH"
        else
            warning "No remote 'origin' configured"
            log "Commit created locally but not pushed"
        fi
    else
        log "Commit created locally but not pushed"
    fi
}

# Show final status
show_final_status() {
    echo
    log "Final repository status:"
    echo "======================="
    
    # Show last commit
    echo -e "${PURPLE}Latest commit:${NC}"
    git log -1 --oneline
    
    # Show branch status
    echo -e "${PURPLE}Branch status:${NC}"
    git status -b --porcelain=v1 | head -1
    
    echo "======================="
    success "Git operations completed successfully!"
}

# Handle interrupts
trap 'echo; error "Operation cancelled by user"; exit 130' INT

# Main execution
main() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    Git Push Helper Script                     ║"
    echo "║                                                              ║"
    echo "║  This script will help you commit and push your changes     ║"
    echo "║  with a properly formatted commit message.                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
    
    # Pre-flight checks
    check_git_repo
    check_changes
    
    # Show current state
    show_status
    show_diff_summary
    
    # Get commit message
    get_commit_message
    
    # Add attribution
    add_attribution
    
    # Preview and confirm
    preview_commit
    
    # Perform operations
    do_git_operations
    
    # Show final status
    show_final_status
}

# Handle command line arguments
case "${1:-}" in
    -h|--help)
        echo "Git Push Helper Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  -h, --help     Show this help message"
        echo "  -s, --status   Show git status and exit"
        echo "  -d, --dry-run  Show what would be committed without doing it"
        echo
        echo "Interactive mode (default):"
        echo "  - Shows current changes"
        echo "  - Prompts for commit message"
        echo "  - Adds attribution"
        echo "  - Commits and optionally pushes"
        ;;
    -s|--status)
        check_git_repo
        show_status
        show_diff_summary
        ;;
    -d|--dry-run)
        check_git_repo
        show_status
        show_diff_summary
        log "Dry run mode - no changes will be made"
        log "Files that would be committed:"
        git add --dry-run . 2>/dev/null | sed 's/^/  /' || echo "  (no changes)"
        ;;
    "")
        main
        ;;
    *)
        error "Unknown option: $1"
        echo "Use $0 --help for usage information"
        exit 1
        ;;
esac