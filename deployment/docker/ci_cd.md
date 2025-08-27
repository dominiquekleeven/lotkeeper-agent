# CI/CD Setup for Docker Image

This document explains how to set up the CI/CD workflow to build and push Docker images to a private container registry.

## Prerequisites

1. GitHub repository with GitHub Actions enabled
2. Access to your private container registry
3. Registry credentials

## Setup Steps

### 1. Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions, and add the following secrets:

- `REGISTRY_USERNAME`: Your registry username
- `REGISTRY_PASSWORD`: Your registry password or access token
- `REGISTRY_URL`: Your registry URL (e.g., `registry.example.com`)

### 2. Workflow Triggers

The workflow will automatically run on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Git tags starting with `v` (e.g., `v1.0.0`)
- Manual trigger via GitHub Actions UI with optional custom tag

### 3. Image Naming and Tagging

Images will be pushed to: `{REGISTRY_URL}/open-ah-agent`

Tags will be automatically generated:
- `latest` for the main branch
- `{branch-name}-{commit-sha}` for feature branches
- `{version}` for semantic version tags
- `{major}.{minor}` for major.minor version tags
- Custom tag when manually triggered (optional)

### 4. Building Locally

To build the image locally:

```bash
# Build the image
docker build -f deployment/docker/Dockerfile -t open-ah-agent .

# Tag for your registry (replace with your actual registry URL)
docker tag open-ah-agent your-registry.com/open-ah-agent:latest

# Login to your registry
docker login your-registry.com

# Push the image
docker push your-registry.com/open-ah-agent:latest
```

### 5. Using the Image

Pull and run the image:

```bash
# Pull the image (replace with your actual registry URL)
docker pull your-registry.com/open-ah-agent:latest

# Run the container
docker run -it your-registry.com/open-ah-agent:latest
```

## Workflow Features

- **Multi-platform support**: Currently configured for `linux/amd64`
- **Layer caching**: Uses GitHub Actions cache for faster builds
- **Automatic tagging**: Smart tag generation based on git events
- **Security**: Credentials stored as GitHub secrets
- **Build optimization**: Uses `.dockerignore` to reduce build context

## Troubleshooting

### Common Issues

1. **Authentication failed**: Verify your Gitea credentials in GitHub secrets
2. **Build context too large**: Check `.dockerignore` file excludes unnecessary files
3. **Permission denied**: Ensure your Gitea user has push access to the registry

### Debug Mode

To debug the workflow, you can:
- Check the Actions tab in your GitHub repository
- Review build logs for specific steps
- Use `workflow_dispatch` trigger for manual testing

## Security Notes

- Never commit credentials to the repository
- Use access tokens instead of passwords when possible
- Regularly rotate your registry credentials
- Consider using OIDC for more secure authentication
