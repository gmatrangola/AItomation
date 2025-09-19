#!/bin/bash

# This script fetches a list of available generative models from the Google Gemini API.
# It requires 'curl' and 'jq' to be installed.

# --- Configuration ---
API_ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models"

# --- Helper Functions ---
print_info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

print_success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# --- Main Logic ---

# 1. Check for dependencies
if ! command -v curl &> /dev/null; then
    print_error "'curl' is not installed. Please inkstall it to continue."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    print_error "'jq' is not installed. It is required to parse the JSON response."
    print_info "You can install it with: sudo apt-get update && sudo apt-get install -y jq"
    exit 1
fi

# 2. Get API Key from user
read -sp "Please enter your Google Gemini API Key: " API_KEY
echo "" # Newline after secret input

if [ -z "$API_KEY" ]; then
    print_error "No API Key provided. Exiting."
    exit 1
fi

# 3. Fetch models from the API
print_info "Fetching models from Google AI..."
RESPONSE=$(curl -s -H "Content-Type: application/json" "${API_ENDPOINT}?key=${API_KEY}")

# 4. Check for errors in the response
if echo "$RESPONSE" | jq -e '.error' > /dev/null; then
    ERROR_MESSAGE=$(echo "$RESPONSE" | jq -r '.error.message')
    print_error "API call failed: $ERROR_MESSAGE"
    exit 1
fi

# 5. Parse and display the list of generative models
print_info "Filtering for models that support content generation..."
MODELS=$(echo "$RESPONSE" | jq -r '.models[] | select(.supportedGenerationMethods[] | contains("generateContent")) | .name' | sed 's/models\///')

if [ -z "$MODELS" ]; then
    print_error "No generative models found for your API key."
    exit 1
fi

print_success "Available Generative Models:"
echo "---------------------------------"
echo "$MODELS"
echo "---------------------------------"