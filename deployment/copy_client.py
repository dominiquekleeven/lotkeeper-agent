#!/usr/bin/env python3
"""
Script to copy WoW client data into the client_data Docker volume.
This script copies a specified client from data/clients/<client_name> to the volume root.
"""

import argparse
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


def list_available_clients(clients_dir: Path) -> list[str]:
    """List available client directories."""
    if not clients_dir.exists():
        return []
    return [d.name for d in clients_dir.iterdir() if d.is_dir()]


def select_client_interactive(available_clients: list[str]) -> str | None:
    """Interactive client selection menu."""
    if not available_clients:
        return None

    print("\nAvailable clients:")
    for i, client in enumerate(available_clients, 1):
        print(f"  {i}. {client}")

    while True:
        try:
            choice = input(f"\nSelect a client (1-{len(available_clients)}) or 'q' to quit: ").strip()

            if choice.lower() == "q":
                return None

            choice_num = int(choice)
            if 1 <= choice_num <= len(available_clients):
                return available_clients[choice_num - 1]
            else:
                print(f"Please enter a number between 1 and {len(available_clients)}")

        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy WoW client data to Docker volume",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python copy_client.py           # Interactive selection (default)
  python copy_client.py --list    # List available clients only
  python copy_client.py --force   # Interactive selection with force overwrite
        """,
    )

    parser.add_argument("--list", "-l", action="store_true", help="List available client directories")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite existing data in volume")
    parser.add_argument("--clients-dir", type=Path, help="Custom path to clients directory (default: ./clients)")

    args = parser.parse_args()

    # Set default clients directory
    if args.clients_dir:
        clients_dir = args.clients_dir
    else:
        script_dir = Path(__file__).parent
        clients_dir = script_dir / "clients"

    print("WoW Client Copy Script")
    print("=" * 50)
    print(f"Clients directory: {clients_dir}")

    # List available clients if requested
    if args.list:
        available_clients = list_available_clients(clients_dir)
        if available_clients:
            print(f"\nAvailable clients in {clients_dir}:")
            for client in available_clients:
                print(f"  📁 {client}")
        else:
            print(f"\n❌ No client directories found in {clients_dir}")
        return

    # Always use interactive selection
    available_clients = list_available_clients(clients_dir)
    if not available_clients:
        print(f"\n❌ No client directories found in {clients_dir}")
        print("Please create the directory structure: data/clients/<client_name>/")
        sys.exit(1)

    selected_client = select_client_interactive(available_clients)
    if not selected_client:
        print("No client selected. Exiting.")
        sys.exit(0)

    client_name = selected_client
    print(f"\n✅ Selected client: {client_name}")

    # Check if clients directory exists
    if not clients_dir.exists():
        print(f"\n❌ Error: Clients directory not found at {clients_dir}")
        print("Please create the directory structure: data/clients/<client_name>/")
        sys.exit(1)

    # Set up client path (we know it exists from interactive selection)
    client_path = clients_dir / client_name
    print(f"\n📁 Found client: {client_name}")
    print(f"   Source path: {client_path}")

    # Check client directory contents
    client_files = list(client_path.iterdir())
    if not client_files:
        print(f"\n⚠️  Warning: Client directory '{client_name}' is empty")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            sys.exit(0)
    else:
        print(f"   Contains {len(client_files)} items")

    # Check if Docker is available
    print("\n🔍 Checking Docker availability...")
    stdout, stderr = run_docker_command("docker --version")
    if stdout is None:
        print("❌ Error: Docker not available or not in PATH")
        sys.exit(1)
    print(f"✅ Docker found: {stdout.strip()}")

    # Remove and recreate client_data volume for clean slate
    print("\n🔍 Managing client_data volume...")
    stdout, stderr = run_docker_command("docker volume ls")
    if stdout and "client_data" in stdout:
        print("🗑️  Removing existing client_data volume...")
        # First try to stop any containers using the volume
        stop_cmd = "docker ps -q --filter volume=client_data"
        stdout, stderr = run_docker_command(stop_cmd)
        if stdout and stdout.strip():
            container_ids = stdout.strip().split("\n")
            print(f"⏹️  Stopping {len(container_ids)} container(s) using the volume...")
            for container_id in container_ids:
                stop_container_cmd = f"docker stop {container_id}"
                run_docker_command(stop_container_cmd)

        # Remove the volume
        remove_cmd = "docker volume rm client_data"
        stdout, stderr = run_docker_command(remove_cmd)
        if stdout is None:
            print("❌ Error: Failed to remove existing client_data volume")
            print("Make sure no containers are using the volume")
            sys.exit(1)
        print("✅ Existing volume removed")

    # Create fresh volume
    print("🆕 Creating fresh client_data volume...")
    stdout, stderr = run_docker_command("docker volume create client_data")
    if stdout is None:
        print("❌ Error: Failed to create client_data volume")
        sys.exit(1)
    print("✅ Fresh client_data volume created")

    # Since we recreated the volume, it should be empty - skip the data check

    # Copy client data to the volume
    print(f"\n📦 Copying client '{client_name}' to client_data volume...")

    # Convert Windows path to format Docker expects
    client_absolute = client_path.resolve()
    docker_source_path = str(client_absolute).replace("\\", "/")
    if docker_source_path.startswith("C:"):
        docker_source_path = "/c" + docker_source_path[2:]

    # Volume is already fresh from recreation, no need to clear

    # Copy the client data
    copy_cmd = f'docker run --rm -v client_data:/data -v "{docker_source_path}:/source" alpine sh -c "cp -r /source/* /data/ 2>/dev/null || cp -r /source/. /data/"'
    print("Running copy operation...")

    stdout, stderr = run_docker_command(copy_cmd)
    if stdout is None:
        print("❌ Error: Failed to copy client data")
        sys.exit(1)

    # Set proper ownership for wine user (UID 1010)
    print("\n🔧 Setting proper ownership for wine user...")
    chown_cmd = 'docker run --rm -v client_data:/data alpine sh -c "chown -R 1010:1010 /data"'
    stdout, stderr = run_docker_command(chown_cmd)
    if stdout is None:
        print("⚠️  Warning: Failed to set ownership (may cause permission issues)")

    # Verify the copy
    print("\n✅ Verifying client installation...")
    verify_cmd = 'docker run --rm -v client_data:/data alpine sh -c "ls -la /data"'
    stdout, stderr = run_docker_command(verify_cmd)
    if stdout:
        print("📁 Contents of /data/:")
        print(stdout)

    # Look for WoW executable
    exe_cmd = "docker run --rm -v client_data:/data alpine sh -c \"find /data -name '*.exe' -type f | head -5\""
    stdout, stderr = run_docker_command(exe_cmd)
    if stdout and stdout.strip():
        exe_files = stdout.strip().split("\n")
        print("\n🎮 Found WoW executable(s):")
        for exe in exe_files:
            if exe.strip():
                exe_name = Path(exe).name
                print(f"  ✅ {exe_name}")

    # Calculate disk usage
    du_cmd = 'docker run --rm -v client_data:/data alpine sh -c "du -sh /data"'
    stdout, stderr = run_docker_command(du_cmd)
    if stdout:
        size = stdout.strip().split()[0]
        print(f"\n💾 Total size: {size}")

    print(f"\n🎉 Client '{client_name}' copy completed!")
    print("\nYour WoW client is now available in the Docker volume.")
    print("\nMake sure your WOW_EXE environment variable matches one of the executables found above.")


if __name__ == "__main__":
    main()
