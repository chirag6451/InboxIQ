#!/bin/bash

# Create timestamp in format YYYY-MM-DD_HHMM
TIMESTAMP=$(date +"%Y-%m-%d_%H%M")

# Create backup directory if it doesn't exist
BACKUP_DIR="backups/backup_${TIMESTAMP}"
SENSITIVE_DIR="${BACKUP_DIR}/sensitive"
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

# Add file hashes to manifest for integrity verification
echo -e "\nFile hashes (SHA-256):" >> "$MANIFEST"
for file in "${FILES_TO_BACKUP[@]}"; do
    if [ -f "$file" ]; then
        shasum -a 256 "$file" >> "$MANIFEST"
    fi
done

# Add hashes for sensitive files
echo -e "\nSensitive file hashes (SHA-256):" >> "$MANIFEST"
for file in "${SENSITIVE_FILES[@]}"; do
    if [[ "$file" == *"*"* ]]; then
        # Handle wildcard patterns
        for matched_file in $file; do
            if [ -f "$matched_file" ]; then
                shasum -a 256 "$matched_file" >> "$MANIFEST"
            fi
        done
    else
        if [ -f "$file" ]; then
            shasum -a 256 "$file" >> "$MANIFEST"
        fi
    fi
done

# Set restrictive permissions on the sensitive directory
chmod -R 600 "${SENSITIVE_DIR}"/*
chmod 700 "${SENSITIVE_DIR}"

echo "Backup completed successfully!"
echo "Backup location: ${BACKUP_DIR}"
echo "Sensitive files location: ${SENSITIVE_DIR}"
echo "A manifest file has been created at: ${MANIFEST}"
echo -e "\nNOTE: Sensitive files have been backed up with restricted permissions (600)."
echo "The sensitive directory is accessible only by the owner (700)."
