> This project is archived and open-sourced as a reference implementation of an automation system for WoW. With a focus on WoW private servers running the 3.3.5a client.

# Lotkeeper Agent

An automated World of Warcraft auction house scanning agent that runs WoW in a containerized Wine environment and uses OpenCV for game interaction.

## Overview

Lotkeeper Agent automates:
- **WoW in Docker**: Wine-based WoW client in headless Linux container
- **Computer Vision**: OpenCV and OCR for game state detection
- **In-game Tasks**: Login, character selection, auction house scanning
- **API Integration**: Sends auction data to Lotkeeper API

## Key Components

### WowBox Deployment (`wowbox-deploy.yml`)

The core of the system - a Docker Compose configuration that creates a complete WoW environment in a container:

```yaml
# Extends base wowbox.yml configuration
# Runs WoW client in Wine with optimized graphics settings
# Provides VNC access for monitoring via noVNC on port 6080 (remote desktop access)
# Mounts client data and configuration volumes
```

**Special Features:**
- **Wine Optimization**: Configured with WINEESYNC, WINEFSYNC, and Mesa GPU acceleration
- **Headless Graphics**: Uses Xvfb virtual framebuffer with optimized OpenGL settings
- **Resource Limits**: 3GB RAM, 2 CPU cores, 1GB shared memory

### Agents (`/agents/`)

Task orchestrators that manage automated workflows:
- **BaseAgent**: Core scheduling and task execution framework with cron-like timing
- **AuctionHouseAgent**: Specialized agent for auction house operations
- **WowAgent**: General-purpose WoW game interaction agent

### Tasks (`/tasks/`)

Atomic operations performed in-game:
- **ScanAuctionsTask**: Complete auction house scanning workflow using custom WoW addon
- **LoginTask**: Automated character login and server selection
- **SelectWindowTask**: Game window management and focus
- **TargetInteractCreatureTask**: NPC interaction automation

### Detectors (`/detectors/`)

Computer vision modules for game state detection:
- **TextDetector**: OCR-based text recognition using Tesseract/TesserOCR
- Detects UI elements like "OAS IDLE", "OAS SCANNING", login screens
- Template matching and image processing with OpenCV
- Screenshot capture and analysis pipeline

### WoW Integration

**Custom Addon**: `OpenAuctionScanner.lua`
- Scans auction house data efficiently
- Saves results to WoW's SavedVariables system
- Provides status indicators for the automation system

**Game Control**: Uses X11 automation (xdotool-style) for:
- Keyboard input simulation
- Mouse clicks and movement
- Window management
- Chat command execution


## Screenshots
Various screenshots of what the `Agent` publishes to the configured Discord webhook
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/1b2519cb-5934-4d2f-b79e-8a4d855de0a6" />
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/0c3f29c8-fa9a-43c3-8570-3f0c5e3cbcf6" />
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/67d9db50-1f4f-446a-97c7-ee7eb99d02e5" />
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/ad147bcd-606b-45b3-b697-a7a28c3d0f6a" />
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/9ca7b40e-aa7b-403c-bab1-5c29dbbb7f31" />
<img width="1024" height="768" alt="image" src="https://github.com/user-attachments/assets/d80db6ea-0045-4e4b-80ab-8bdbe4c27502" />
<img width="592" height="476" alt="image" src="https://github.com/user-attachments/assets/cb90cc94-7fed-4ee5-b81b-549173de37b5" />

Discord offered a convenient way of embedding images, e.g. when it recognized something or when it failed to recognize or complete a task. Basically an unconvential logger.


## Quick Start

1. **Configure Environment**:
   ```bash
   cp deployment/example.env .env
   # Edit .env with your WoW server, credentials, and API tokens
   ```

2. **Deploy with Docker**:
   ```bash
   cd deployment
   docker-compose -f wowbox-deploy.yml up -d
   ```

3. **Monitor via noVNC**: Access `http://localhost:6080` to view the WoW client

4. **Manual Mode** (for setup/debugging):
   ```bash
   AGENT_MODE=MANUAL docker-compose -f wowbox-deploy.yml up
   ```

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Docker Host   │    │   Wine Container │    │  Lotkeeper API  │
│                 │    │                  │    │                 │
│  noVNC:6080 ────┼────┤  WoW Client      │    │                 │
│                 │    │  ├─ Xvfb :99     │    │                 │
│                 │    │  ├─ OpenCV       │    │                 │
│                 │    │  ├─ Tesseract    │    │                 │
│                 │    │  └─ Python Agent ├────┤  /api/v1/agent  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Technology Stack

- **Python 3.13** with UV package manager
- **OpenCV & Tesseract** for computer vision and OCR
- **Wine** for running Windows WoW client on Linux
- **Docker** with X11 forwarding and VNC
- **APScheduler** for cron-like task scheduling
- **Pydantic** for data validation and API models

## Configuration

The system requires several configuration files:
- `config/wow.json`: WoW account credentials and server settings
- `.env`: Environment variables for API tokens and agent settings
- Custom WoW addon installation for auction house integration

Built for automated, large-scale auction house data collection across multiple WoW servers and characters.
