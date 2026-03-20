# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.1] - 2025-03-20

### Fixed
- Fixed `AttributeError: 'MessageChain' object has no attribute 'file'` error when forwarding file attachments
- Now correctly appends File components to the message chain using `chain.chain.append()` instead of the non-existent `chain.file()` method

## [1.2.0] - 2025-03-20

### Added
- **File attachment forwarding support**: Forward file attachments (MP4, PDF, documents, etc.) along with messages
- `forward_files` configuration option to enable/disable file forwarding per rule
- Support for all file types supported by Discord (videos, documents, audio files, etc.)

### Changed
- Updated `/forward_status` command to display file forwarding status
- Improved error handling and logging for file forwarding

## [1.1.0] - 2025-03-17

### Added
- **Multi-rule support**: Configure multiple forwarding rules for different Discord bot instances
- `forward_rules` configuration option with support for:
  - `platform_id`: Target specific Discord platform adapters
  - Per-rule settings for images, text, sender info, and bot message handling
  - Individual enable/disable toggle for each rule

### Changed
- Improved rule matching logic with platform ID support
- Better logging for rule loading and message forwarding
- Updated `/forward_status` command to display all configured rules

### Deprecated
- Legacy single-rule configuration format (still supported for backward compatibility)
  - `forward_from_platform_id`
  - `source_channel_id`
  - `destination_channel_id`
  - `forward_images`
  - `forward_text`
  - `include_sender_info`
  - `ignore_bot_messages`

## [1.0.0] - 2025-03-16

### Added
- Initial release
- Basic message forwarding from one Discord channel to another
- Support for text and image forwarding
- Sender information inclusion option
- Bot message filtering
- `/forward_status` command to check plugin status
- `/forward_test` command to test forwarding functionality
