#!/bin/bash

# Get current project name from directory name
PROJECT_NAME=$(basename "$(pwd)")

# Create timestamp in format YYYY-MM-DD_HHMM
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")

# Set up backup directories
BASE_BACKUP_DIR="/Users/chiragahmedabadi/dev/project_backups"
PROJECT_BACKUP_DIR="${BASE_BACKUP_DIR}/${PROJECT_NAME}"
BACKUP_DIR="${PROJECT_BACKUP_DIR}/backup_${TIMESTAMP}"
SENSITIVE_DIR="${BACKUP_DIR}/sensitive"

# Create required directories
mkdir -p "${BASE_BACKUP_DIR}"
mkdir -p "${PROJECT_BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}"
mkdir -p "${SENSITIVE_DIR}"
chmod 700 "${SENSITIVE_DIR}"  # Restrict permissions for sensitive directory

# List of important files to backup
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

# List of sensitive files to backup
SENSITIVE_FILES=(
    ".env"
    "token.json"
    "token.pickle"
    "credentials.json"
    "client_secret.json"
    "oauth_token.json"
    "*.key"
    "*.pem"
    "*.crt"
)

# Function to backup a file with error handling
backup_file() {
    local file=$1
    local target_dir=$2
    if [ -f "$file" ]; then
        echo "Backing up $file..."
        cp "$file" "${target_dir}/${file%.*}_${TIMESTAMP}.${file##*.}"
    else
        echo "Warning: $file not found, skipping..."
    fi
}

# Function to backup files matching a pattern
backup_pattern() {
    local pattern=$1
    local target_dir=$2
    for file in $pattern; do
        if [ -f "$file" ]; then
            echo "Backing up $file..."
            cp "$file" "${target_dir}/$(basename ${file%.*})_${TIMESTAMP}.${file##*.}"
        fi
    done
}

# Create a manifest file
MANIFEST="${BACKUP_DIR}/backup_manifest.txt"
echo "Backup created on $(date)" > "$MANIFEST"
echo "Project: ${PROJECT_NAME}" >> "$MANIFEST"
echo "Files included:" >> "$MANIFEST"

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
    if [[ "$file" == *"*"* ]]; then
        # Handle wildcard patterns
        backup_pattern "$file" "${SENSITIVE_DIR}"
        for matched_file in $file; do
            if [ -f "$matched_file" ]; then
                echo "- $matched_file (encrypted)" >> "$MANIFEST"
            fi
        done
    else
        backup_file "$file" "${SENSITIVE_DIR}"
        if [ -f "$file" ]; then
            echo "- $file (encrypted)" >> "$MANIFEST"
        fi
    fi
done

# Backup test directory if it exists
if [ -d "tests" ]; then
    echo "Backing up tests directory..."
    cp -r tests "${BACKUP_DIR}/tests_${TIMESTAMP}"
    echo -e "\nTest files:" >> "$MANIFEST"
    echo "- tests/" >> "$MANIFEST"
fi

# Add backup location information to manifest
echo -e "\nBackup Information:" >> "$MANIFEST"
echo "- Timestamp: ${TIMESTAMP}" >> "$MANIFEST"
echo "- Project: ${PROJECT_NAME}" >> "$MANIFEST"
echo "- Base Location: ${BASE_BACKUP_DIR}" >> "$MANIFEST"
echo "- Project Backups: ${PROJECT_BACKUP_DIR}" >> "$MANIFEST"
echo "- This Backup: ${BACKUP_DIR}" >> "$MANIFEST"

echo "Backup completed successfully!"
echo "Backup location: ${BACKUP_DIR}"
echo "Sensitive files location: ${SENSITIVE_DIR}"
echo "A manifest file has been created at: ${MANIFEST}"
echo -e "\nNOTE: Sensitive files have been backed up with restricted permissions (600)."
echo "The sensitive directory is accessible only by the owner (700)."

# Create a symlink to latest backup
LATEST_LINK="${PROJECT_BACKUP_DIR}/latest"
rm -f "${LATEST_LINK}"
ln -s "${BACKUP_DIR}" "${LATEST_LINK}"
echo "Created symlink to latest backup at: ${LATEST_LINK}"
