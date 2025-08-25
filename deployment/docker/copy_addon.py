#!/usr/bin/env python3
"""
Script to copy WoW addons into the client_data Docker volume.
This script handles the proper directory structure for WoW addons.
"""

import subprocess
import sys
from pathlib import Path


def run_docker_command(cmd: str) -> tuple[str | None, str | None]:
    """Run a docker command and return the result."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return None, e.stderr


def list_available_addons(addons_path: Path) -> list[str]:
    """List available addon directories."""
    if not addons_path.exists():
        return []
    return [d.name for d in addons_path.iterdir() if d.is_dir()]


def select_addons_interactive(available_addons: list[str]) -> list[str] | None:
    """Interactive addon selection menu with multiple selection support."""
    if not available_addons:
        return None

    print("\nAvailable addons:")
    for i, addon in enumerate(available_addons, 1):
        print(f"  {i}. {addon}")

    print("\n  A. All addons")

    while True:
        try:
            choice = input(
                f"\nSelect addon(s) (1-{len(available_addons)}, 'A' for all, or comma-separated numbers) or 'q' to quit: "
            ).strip()

            if choice.lower() == "q":
                return None

            if choice.upper() == "A":
                return available_addons

            # Handle comma-separated choices
            if "," in choice:
                selected_addons = []
                choices = [c.strip() for c in choice.split(",")]
                for c in choices:
                    choice_num = int(c)
                    if 1 <= choice_num <= len(available_addons):
                        addon_name = available_addons[choice_num - 1]
                        if addon_name not in selected_addons:
                            selected_addons.append(addon_name)
                    else:
                        print(f"Invalid choice: {c}. Please enter numbers between 1 and {len(available_addons)}")
                        break
                else:
                    return selected_addons
            else:
                # Single choice
                choice_num = int(choice)
                if 1 <= choice_num <= len(available_addons):
                    return [available_addons[choice_num - 1]]
                else:
                    print(f"Please enter a number between 1 and {len(available_addons)}")

        except ValueError:
            print("Please enter valid number(s), 'A' for all, or 'q' to quit")
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return None


def main() -> None:
    # Get the project root directory (parent of docker folder)
    script_dir = Path(__file__).parent
    deployment_root = script_dir.parent
    addons_path = deployment_root / "addons"

    # Convert to absolute path for Docker volume mounting
    addons_absolute = addons_path.resolve()

    print("WoW Addon Copy Script")
    print("=" * 50)
    print(f"Deployment root: {deployment_root}")
    print(f"Addons source: {addons_absolute}")

    # Check if addons directory exists
    if not addons_path.exists():
        print(f"❌ Error: Addons directory not found at {addons_path}")
        sys.exit(1)

    # List available addons and let user select
    available_addons = list_available_addons(addons_path)
    if not available_addons:
        print("❌ Error: No addon folders found in addons directory")
        sys.exit(1)

    selected_addons = select_addons_interactive(available_addons)
    if not selected_addons:
        print("No addons selected. Exiting.")
        sys.exit(0)

    print(f"\n✅ Selected {len(selected_addons)} addon(s) to copy:")
    for addon in selected_addons:
        print(f"  📁 {addon}")

    # Check if Docker is available
    print("\n🔍 Checking Docker availability...")
    stdout, stderr = run_docker_command("docker --version")
    if stdout is None:
        print("❌ Error: Docker not available or not in PATH")
        sys.exit(1)
    print(f"✅ Docker found: {stdout.strip()}")

    # Check if client_data volume exists
    print("\n🔍 Checking client_data volume...")
    stdout, stderr = run_docker_command("docker volume ls")
    if stdout and "client_data" not in stdout:
        print("⚠️  Warning: client_data volume not found. Creating it...")
        stdout, stderr = run_docker_command("docker volume create client_data")
        if stdout is None:
            print("❌ Error: Failed to create client_data volume")
            sys.exit(1)
        print("✅ client_data volume created")
    else:
        print("✅ client_data volume found")

    # Copy addons to the volume
    print("\n📦 Copying addons to client_data volume...")

    # First, create the Interface/AddOns directory structure
    create_dirs_cmd = 'docker run --rm -v client_data:/data alpine sh -c "mkdir -p /data/Interface/AddOns"'
    stdout, stderr = run_docker_command(create_dirs_cmd)
    if stdout is None:
        print("❌ Error: Failed to create directory structure")
        sys.exit(1)

    # Copy the selected addons
    print("\n📦 Copying selected addons...")

    for addon in selected_addons:
        addon_path = addons_path / addon
        addon_absolute = addon_path.resolve()

        # Convert Windows path to format Docker expects
        docker_source_path = str(addon_absolute).replace("\\", "/")
        if docker_source_path.startswith("C:"):
            docker_source_path = "/c" + docker_source_path[2:]

        print(f"📂 Copying {addon}... (from {docker_source_path} to /data/Interface/AddOns/{addon})")
        
        # First create the addon directory
        mkdir_cmd = f'docker run --rm -v client_data:/data alpine sh -c "mkdir -p /data/Interface/AddOns/{addon}"'
        stdout, stderr = run_docker_command(mkdir_cmd)
        if stdout is None:
            print(f"❌ Error: Failed to create directory for addon {addon}")
            sys.exit(1)
        
        # Then copy the addon files
        copy_cmd = f'docker run --rm -v client_data:/data -v "{docker_source_path}:/source" alpine sh -c "cp -r /source/* /data/Interface/AddOns/{addon}/"'

        stdout, stderr = run_docker_command(copy_cmd)
        if stdout is None:
            print(f"❌ Error: Failed to copy addon {addon}")
            sys.exit(1)
        else:
            print(f"✅ {addon} copied successfully")
            
            # Show the contents of the copied addon directory
            print(f"📁 Contents of /data/Interface/AddOns/{addon}/:")
            ls_cmd = f'docker run --rm -v client_data:/data alpine sh -c "ls -la /data/Interface/AddOns/{addon}/"'
            stdout, stderr = run_docker_command(ls_cmd)
            if stdout:
                print(stdout)
            
            # Show the .toc file contents if it exists
            toc_cmd = f'docker run --rm -v client_data:/data alpine sh -c "cat /data/Interface/AddOns/{addon}/*.toc"'
            stdout, stderr = run_docker_command(toc_cmd)
            if stdout:
                print(f"📄 {addon}.toc contents:")
                print(stdout)
            else:
                print(f"⚠️  No .toc file found for {addon}")

    # Verify the copy
    print("\n✅ Verifying addon installation...")
    verify_cmd = 'docker run --rm -v client_data:/data alpine sh -c "ls -la /data/Interface/AddOns/"'
    stdout, stderr = run_docker_command(verify_cmd)
    if stdout:
        print("📁 Contents of /data/Interface/AddOns/:")
        print(stdout)

    # Check for .toc files (addon indicator) for selected addons
    toc_cmd = "docker run --rm -v client_data:/data alpine sh -c \"find /data/Interface/AddOns -name '*.toc'\""
    stdout, stderr = run_docker_command(toc_cmd)
    if stdout:
        toc_files = stdout.strip().split("\n")
        installed_addons = []
        for toc in toc_files:
            if toc.strip():
                addon_name = Path(toc).parent.name
                installed_addons.append(addon_name)

        print(f"\n🎮 Successfully installed {len(installed_addons)} addon(s):")
        for addon_name in installed_addons:
            if addon_name in selected_addons:
                print(f"  ✅ {addon_name}")
            else:
                print(f"  📁 {addon_name} (existing)")

    print(f"\n🎉 {len(selected_addons)} addon(s) copy completed successfully!")
    print("\nYour selected addons are now available in the WoW client running in Docker.")
    print("Start your wowbox container and the addons should be loaded automatically.")


if __name__ == "__main__":
    main()
