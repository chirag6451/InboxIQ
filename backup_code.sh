#!/bin/bash

# Get current project name from directory name
PROJECT_NAME=$(basename "$(pwd)")

# Set up backup directories
BASE_BACKUP_DIR="./backups"
PROJECT_BACKUP_DIR="${BASE_BACKUP_DIR}/${PROJECT_NAME}"

# Function to show usage
show_usage() {
    echo "Usage: $0 [command] [backup_path]"
    echo "Commands:"
    echo "  backup              - Create a new backup"
    echo "  restore-latest     - Restore from the latest backup"
    echo "  restore [path]     - Restore from a specific backup path"
    echo "  delete-all         - Delete all backups of the project"
    echo "  list               - List all available backups"
}

# Function to backup a single file
backup_file() {
    local source="$1"
    local dest_dir="$2"
    if [ -f "$source" ]; then
        local filename=$(basename "$source")
        local dest="${dest_dir}/${filename%.*}_${TIMESTAMP}.${filename##*.}"
        echo "Backing up ${filename}..."
        cp "$source" "$dest"
    else
        echo "Warning: ${source} not found, skipping..."
    fi
}

# Function to backup files matching a pattern
backup_pattern() {
    local pattern="$1"
    local dest_dir="$2"
    for file in $pattern; do
        if [ -f "$file" ]; then
            backup_file "$file" "$dest_dir"
        fi
    done
}

# Function to create a new backup
create_backup() {
    # Create timestamp in format YYYY-MM-DD_HHMM
    TIMESTAMP=$(date +"%Y-%m-%d_%H%M")
    BACKUP_DIR="${PROJECT_BACKUP_DIR}/backup_${TIMESTAMP}"
    SENSITIVE_DIR="${BACKUP_DIR}/sensitive"

    # Create required directories
    mkdir -p "${BASE_BACKUP_DIR}"
    mkdir -p "${PROJECT_BACKUP_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "${SENSITIVE_DIR}"
    chmod 700 "${SENSITIVE_DIR}"  # Restrict permissions for sensitive directory

    # Create a manifest file
    MANIFEST="${BACKUP_DIR}/backup_manifest.txt"
    echo "Backup created on $(date)" > "$MANIFEST"
    echo "Project: ${PROJECT_NAME}" >> "$MANIFEST"
    echo "Files included:" >> "$MANIFEST"

    # Backup regular files
    FILES_TO_BACKUP=(
        "config.py"
        "gmail_auth.py"
        "gmail_handler.py"
        "process_emails.py"
        "email_classifier.py"
        "email_analyzer.py"
        "app.py"
        "requirements.txt"
        ".env.example"
        "README.md"
    )

    # Sensitive files that need special handling
    SENSITIVE_FILES=(
        ".env"
        "token.json"
        "token.pickle"
        "credentials.json"
        "client_secret.json"
        "oauth_token.json"
    )

    # Backup regular files
    for file in "${FILES_TO_BACKUP[@]}"; do
        backup_file "$file" "${BACKUP_DIR}"
        if [ -f "$file" ]; then
            echo "- $file" >> "$MANIFEST"
        fi
    done

    # Backup sensitive files
    echo -e "\nSensitive files backed up:" >> "$MANIFEST"
    for file in "${SENSITIVE_FILES[@]}"; do
        backup_file "$file" "${SENSITIVE_DIR}"
        if [ -f "$file" ]; then
            echo "- $file" >> "$MANIFEST"
        fi
    done

    # Backup test directory if it exists
    if [ -d "tests" ]; then
        echo "Backing up tests directory..."
        cp -r tests "${BACKUP_DIR}/tests_${TIMESTAMP}"
        echo -e "\nTest files:" >> "$MANIFEST"
        echo "- tests/" >> "$MANIFEST"
    fi

    # Create a symlink to latest backup
    LATEST_LINK="${PROJECT_BACKUP_DIR}/latest"
    rm -f "${LATEST_LINK}"
    ln -s "${BACKUP_DIR}" "${LATEST_LINK}"

    echo "Backup completed successfully!"
    echo "Backup location: ${BACKUP_DIR}"
    echo "Sensitive files location: ${SENSITIVE_DIR}"
    echo "A manifest file has been created at: ${MANIFEST}"
    echo -e "\nNOTE: Sensitive files have been backed up with restricted permissions (600)."
    echo "The sensitive directory is accessible only by the owner (700)."
    echo "Created symlink to latest backup at: ${LATEST_LINK}"
}

# Function to restore files from a backup
restore_from_backup() {
    local backup_path="$1"
    
    if [ ! -d "$backup_path" ]; then
        echo "Error: Backup directory not found: $backup_path"
        exit 1
    fi

    echo "Restoring from backup: $backup_path"
    
    # First, create a backup of current state
    create_backup

    # Restore regular files
    for file in "$backup_path"/*; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            # Remove timestamp from filename
            original_name=$(echo "$filename" | sed -E 's/_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}\./\./')
            if [[ "$original_name" != "backup_manifest.txt" ]]; then
                echo "Restoring $original_name..."
                cp "$file" "./$original_name"
            fi
        fi
    done

    # Restore sensitive files if they exist
    if [ -d "$backup_path/sensitive" ]; then
        echo "Restoring sensitive files..."
        for file in "$backup_path/sensitive"/*; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                original_name=$(echo "$filename" | sed -E 's/_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}\./\./')
                echo "Restoring $original_name..."
                cp "$file" "./$original_name"
            fi
        done
    fi

    # Restore tests directory if it exists
    for dir in "$backup_path"/tests_*; do
        if [ -d "$dir" ]; then
            echo "Restoring tests directory..."
            rm -rf ./tests
            cp -r "$dir" ./tests
            break
        fi
    done

    echo "Restore completed successfully!"
}

# Function to list all backups
list_backups() {
    echo "Available backups for $PROJECT_NAME:"
    echo "----------------------------------------"
    if [ -d "$PROJECT_BACKUP_DIR" ]; then
        ls -lt "$PROJECT_BACKUP_DIR" | grep "^d" | awk '{print $9}' | while read -r backup; do
            if [ -f "$PROJECT_BACKUP_DIR/$backup/backup_manifest.txt" ]; then
                echo "$backup - $(head -n 1 "$PROJECT_BACKUP_DIR/$backup/backup_manifest.txt")"
            else
                echo "$backup"
            fi
        done
    else
        echo "No backups found."
    fi
}

# Function to delete all backups
delete_all_backups() {
    if [ -d "$PROJECT_BACKUP_DIR" ]; then
        echo "Warning: This will delete all backups for $PROJECT_NAME"
        read -p "Are you sure you want to continue? (y/N) " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            rm -rf "$PROJECT_BACKUP_DIR"
            echo "All backups for $PROJECT_NAME have been deleted."
        else
            echo "Operation cancelled."
        fi
    else
        echo "No backups found for $PROJECT_NAME."
    fi
}

# Main script logic
case "$1" in
    "backup")
        create_backup
        ;;
    "restore-latest")
        if [ -L "${PROJECT_BACKUP_DIR}/latest" ]; then
            restore_from_backup "$(readlink "${PROJECT_BACKUP_DIR}/latest")"
        else
            echo "Error: No latest backup found."
            exit 1
        fi
        ;;
    "restore")
        if [ -z "$2" ]; then
            echo "Error: Please specify the backup path to restore from."
            show_usage
            exit 1
        fi
        restore_from_backup "$2"
        ;;
    "list")
        list_backups
        ;;
    "delete-all")
        delete_all_backups
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
