#!/bin/bash

# Docker build script for the Lotkeeper Agent (Local Development)
# This script builds the Docker image locally for development use
# And directly runs the docker-compose deployment in attached mode
# Just open a new terminal if you dislike that :>

set -e

# Configuration
IMAGE_NAME="lotkeeper-agent"
IMAGE_TAG="${1:-dev}"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup docker-compose stack
cleanup() {
    echo ""
    print_status "Received interrupt signal. Stopping docker-compose stack..."
    
    # Check if we're in the deployment directory
    if [[ "$PWD" == *"/deployment" ]]; then
        if docker-compose -f wowbox.yml down; then
            print_success "Stack stopped successfully!"
        else
            print_error "Failed to stop stack"
        fi
    else
        # We're in the root directory, need to cd to deployment
        cd deployment
        if docker-compose -f wowbox.yml down; then
            print_success "Stack stopped successfully!"
        else
            print_error "Failed to stop stack"
        fi
    fi
    exit 0
}

# Set up signal handlers
trap cleanup INT TERM

# Show usage
show_usage() {
    echo "Usage: $0 [TAG]"
    echo ""
    echo "Arguments:"
    echo "  TAG    Docker image tag (default: dev)"
    echo ""
    echo "Examples:"
    echo "  $0        # Build with 'dev' tag"
    echo "  $0 v1.0   # Build with 'v1.0' tag"
}

# Parse command line arguments
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    show_usage
    exit 0
fi

print_status "Building Docker image: $FULL_IMAGE_NAME"

# Check if we're in the right directory
if [[ ! -f "docker/Dockerfile" ]]; then
    print_error "Dockerfile not found. Please run this script from the project root directory."
    exit 1
fi

# Build the image
print_status "Building image from docker/Dockerfile..."
if docker build -t "$FULL_IMAGE_NAME" -f docker/Dockerfile .; then
    print_success "Image built successfully: $FULL_IMAGE_NAME"
else
    print_error "Failed to build image"
    exit 1
fi

# Show image info
print_status "Image details:"
docker images "$FULL_IMAGE_NAME"

# Run docker-compose
echo ""
print_status "Starting docker-compose deployment in detached mode..."
cd deployment

if docker-compose -f wowbox.yml up -d; then
    print_success "Deployment started successfully in detached mode!"
    
    echo ""
    print_status "Attaching to container logs (press Ctrl+C to stop the stack)..."
    if docker-compose -f wowbox.yml logs -f; then
        print_success "Deployment completed successfully!"
    else
        print_error "Failed to attach to logs"
        exit 1
    fi
else
    print_error "Deployment failed to start"
    exit 1
fi
