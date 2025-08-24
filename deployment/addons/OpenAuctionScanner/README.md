# OpenAuctionScanner

A World of Warcraft 3.3.5a (Wrath of the Lich King) addon for scanning and analyzing auction house data.

## Features

- Simple and clean user interface
- Auction house scanning functionality
- Movable and resizable frame
- Slash commands for easy access

## Installation

1. Download or extract the addon files to your WoW addons directory:
   ```
   World of Warcraft\Interface\AddOns\OpenAuctionScanner\
   ```

2. Make sure the folder structure looks like this:
   ```
   OpenAuctionScanner\
   ├── OpenAuctionScanner.toc
   ├── OpenAuctionScanner.lua
   └── README.md
   ```

3. Restart World of Warcraft or reload your UI (`/reload`)

4. The addon should automatically load and you'll see a message in chat

## Usage

### Slash Commands
- `/oas` - Toggle the addon interface
- `/openauctionscanner` - Alternative command to toggle the interface

### Interface
- The main frame can be moved by dragging with the left mouse button
- Click "Scan AH" to scan the auction house (requires AH to be open)
- The status text shows current addon status

## Requirements

- World of Warcraft 3.3.5a (Wrath of the Lich King)
- No additional dependencies required

## Development

This addon is designed for WoW 3.3.5a and uses the API available in that version. The main features include:

- Frame creation and management
- Event handling
- Slash command registration
- Basic UI elements

## Customization

You can modify the addon by:
- Changing colors and styling in the Lua file
- Adding new functionality to the scan function
- Modifying the frame size and position
- Adding new UI elements

## Troubleshooting

- If the addon doesn't load, check that all files are in the correct directory
- Ensure the TOC file has the correct interface version (30300 for 3.3.5a)
- Use `/reload` to reload the UI after making changes
- Check the chat for any error messages

## License

This addon is provided as-is for educational and personal use.
