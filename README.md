# AstrBot Discord Message Forwarder Plugin

A powerful Discord message forwarding plugin for [AstrBot](https://github.com/Soulter/AstrBot) that forwards messages between Discord channels with support for multiple Discord bot instances.

## Features

- **Multi-Rule Support**: Configure multiple forwarding rules for different Discord bot instances
- **Flexible Forwarding**: Forward text, images, or both
- **Sender Information**: Optionally include sender name and ID in forwarded messages
- **Bot Message Control**: Choose to ignore or forward messages from other bots
- **Backward Compatible**: Supports legacy single-rule configuration format

## Installation

1. In AstrBot WebUI, go to **Extensions** > **Install from GitHub**
2. Enter the repository URL: `https://github.com/MinaraAgent/astrbot_plugin_discord_forwarder`
3. Click **Install** and restart AstrBot

Alternatively, clone this repository to your AstrBot plugins directory:
```bash
cd /path/to/astrbot/data/plugins/
git clone https://github.com/MinaraAgent/astrbot_plugin_discord_forwarder.git
```

## Configuration

### Multi-Rule Configuration (Recommended)

Configure multiple forwarding rules in the WebUI:

| Field | Description |
|-------|-------------|
| `platform_id` | Discord platform ID in AstrBot (e.g., `discord`, `discord-b`) |
| `source_channel_id` | Discord channel ID to forward messages **FROM** |
| `destination_channel_id` | Discord channel ID to forward messages **TO** |
| `forward_images` | Include images from forwarded messages |
| `forward_text` | Include text content from forwarded messages |
| `include_sender_info` | Add sender name and ID to forwarded messages |
| `ignore_bot_messages` | Skip forwarding messages sent by Discord bots |
| `enabled` | Toggle this specific forwarding rule on/off |

### How to Get Channel IDs

1. Enable **Developer Mode** in Discord (User Settings > Advanced > Developer Mode)
2. Right-click on a channel and select **Copy Channel ID**

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `/forward_status` | Check the forwarder plugin status and all configured rules |
| `/forward_test` | Test forwarding a message to the destination channel of the first rule |

### Example Setup

To forward messages from Channel A to Channel B using your primary Discord bot:

1. Configure a new rule:
   - `platform_id`: `discord`
   - `source_channel_id`: `123456789012345678` (Channel A)
   - `destination_channel_id`: `876543210987654321` (Channel B)
   - Enable the rule

2. Use `/forward_status` to verify the configuration

3. Send a message in Channel A - it will be forwarded to Channel B

## Use Cases

- **Message Relay**: Forward announcements from one server to another
- **Bot-to-Bot Communication**: Forward messages between different bot instances
- **Channel Mirroring**: Keep multiple channels synchronized
- **Notification Forwarding**: Forward alerts from monitoring channels

## Requirements

- AstrBot v3.4.0 or higher
- Discord platform adapter configured in AstrBot

## Troubleshooting

### Messages not being forwarded

1. Check if the plugin is enabled
2. Verify channel IDs are correct using `/forward_status`
3. Ensure the Discord bot has permission to read messages in the source channel and send messages in the destination channel
4. Check if `ignore_bot_messages` is enabled and you're testing with a bot message

### Bot messages not being forwarded

By default, the plugin ignores messages from other bots. To forward bot messages:
1. Set `ignore_bot_messages` to `false` in the rule configuration
2. Also ensure your Discord platform adapter has `discord_allow_bot_messages` enabled (requires AstrBot v3.5.0+)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
