"""
AstrBot Discord Message Forwarder Plugin

Forwards messages from source Discord channels to destination channels.
Supports multiple forwarding rules for different Discord bot instances.
Supports text, images, files (including videos, documents, etc.), and other message components.
"""

from dataclasses import dataclass
from typing import Optional

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image, File
from astrbot.core.message.message_event_result import MessageChain


@dataclass
class ForwardRule:
    """Represents a single forwarding rule."""
    platform_id: str
    source_channel_id: str
    destination_channel_id: str
    forward_images: bool = True
    forward_text: bool = True
    forward_files: bool = True
    include_sender_info: bool = True
    ignore_bot_messages: bool = True
    enabled: bool = True


@register(
    "astrbot_plugin_discord_forwarder",
    "Minara",
    "Discord message forwarding plugin - forwards messages between channels",
    "1.2.1",
)
class DiscordForwarderPlugin(Star):
    """Discord message forwarding plugin with support for multiple forwarding rules."""

    def __init__(self, context: Context, config: dict) -> None:
        super().__init__(context)
        self.config = config
        self.enabled = config.get("enabled", True)
        self.forward_rules: list[ForwardRule] = []

        # Load forwarding rules
        self._load_rules()

    def _load_rules(self) -> None:
        """Load forwarding rules from configuration."""
        self.forward_rules = []

        # Check for new multi-rule format
        rules_config = self.config.get("forward_rules", [])

        if rules_config:
            # New format: multiple rules
            for rule_dict in rules_config:
                if isinstance(rule_dict, dict):
                    rule = ForwardRule(
                        platform_id=rule_dict.get("platform_id", "discord"),
                        source_channel_id=str(rule_dict.get("source_channel_id", "")),
                        destination_channel_id=str(rule_dict.get("destination_channel_id", "")),
                        forward_images=rule_dict.get("forward_images", True),
                        forward_text=rule_dict.get("forward_text", True),
                        forward_files=rule_dict.get("forward_files", True),
                        include_sender_info=rule_dict.get("include_sender_info", True),
                        ignore_bot_messages=rule_dict.get("ignore_bot_messages", True),
                        enabled=rule_dict.get("enabled", True),
                    )
                    self.forward_rules.append(rule)
                    logger.info(
                        f"[DiscordForwarder] Loaded rule: platform={rule.platform_id}, "
                        f"source={rule.source_channel_id}, dest={rule.destination_channel_id}"
                    )

        # Check for legacy single-rule format (backward compatibility)
        legacy_platform_id = self.config.get("forward_from_platform_id")
        legacy_source = self.config.get("source_channel_id")
        legacy_dest = self.config.get("destination_channel_id")

        if legacy_platform_id and legacy_source and legacy_dest:
            # Check if this rule already exists in forward_rules
            exists = any(
                r.platform_id == legacy_platform_id
                for r in self.forward_rules
            )
            if not exists:
                legacy_rule = ForwardRule(
                    platform_id=legacy_platform_id,
                    source_channel_id=str(legacy_source),
                    destination_channel_id=str(legacy_dest),
                    forward_images=self.config.get("forward_images", True),
                    forward_text=self.config.get("forward_text", True),
                    forward_files=self.config.get("forward_files", True),
                    include_sender_info=self.config.get("include_sender_info", True),
                    ignore_bot_messages=self.config.get("ignore_bot_messages", True),
                    enabled=True,
                )
                self.forward_rules.append(legacy_rule)
                logger.info(
                    f"[DiscordForwarder] Loaded legacy rule: platform={legacy_rule.platform_id}, "
                    f"source={legacy_rule.source_channel_id}, dest={legacy_rule.destination_channel_id}"
                )

        if not self.forward_rules:
            logger.warning(
                "[DiscordForwarder] No forwarding rules configured. "
                "Please configure the plugin in the WebUI."
            )

    async def initialize(self) -> None:
        """Called when plugin is activated."""
        logger.info(
            f"[DiscordForwarder] Plugin initialized with {len(self.forward_rules)} rule(s)."
        )

    async def terminate(self) -> None:
        """Called when plugin is disabled/reloaded."""
        logger.info("[DiscordForwarder] Plugin terminated.")

    def _get_matching_rule(self, event: AstrMessageEvent) -> Optional[ForwardRule]:
        """Find the forwarding rule that matches the event's platform and channel."""
        try:
            platform_id = event.platform_meta.id
        except Exception:
            platform_id = None

        session_id = event.session_id or ""
        unified_origin = event.unified_msg_origin or ""

        for rule in self.forward_rules:
            if not rule.enabled:
                continue

            # Check platform ID match
            platform_match = False
            if platform_id:
                platform_match = platform_id == rule.platform_id
            else:
                # Fallback: check from session or unified_msg_origin
                platform_match = (
                    rule.platform_id in session_id
                    or rule.platform_id in unified_origin
                )

            if not platform_match:
                continue

            # Check source channel match
            channel_match = (
                rule.source_channel_id in session_id
                or rule.source_channel_id in unified_origin
                or session_id == rule.source_channel_id
            )

            if channel_match:
                return rule

        return None

    def _is_bot_message(self, event: AstrMessageEvent) -> bool:
        """Check if the message is from a bot."""
        try:
            message_obj = event.message_obj
            if hasattr(message_obj, "raw_message"):
                raw_msg = message_obj.raw_message
                if raw_msg and hasattr(raw_msg, "author"):
                    return raw_msg.author.bot
        except Exception as e:
            logger.debug(f"[DiscordForwarder] Error checking bot status: {e}")
        return False

    async def _build_forwarded_message(
        self, event: AstrMessageEvent, rule: ForwardRule
    ) -> Optional[MessageChain]:
        """Build the message chain to forward based on the rule."""
        chain = MessageChain()

        # Add sender info if configured
        if rule.include_sender_info:
            sender_name = event.get_sender_name() or "Unknown"
            sender_id = event.get_sender_id() or "Unknown"
            header = f"[{sender_name} (ID: {sender_id})]\n"
            chain.message(header)

        # Get message components
        message_obj = event.message_obj
        components = []

        if message_obj and hasattr(message_obj, "message"):
            components = message_obj.message or []

        has_forwarded_content = False

        # Process message components
        for component in components:
            if isinstance(component, Plain) and rule.forward_text:
                text = component.text.strip()
                if text:
                    chain.message(text)
                    has_forwarded_content = True

            elif isinstance(component, Image) and rule.forward_images:
                try:
                    if component.url:
                        chain.image(url=component.url)
                        has_forwarded_content = True
                    elif component.path:
                        chain.image(path=component.path)
                        has_forwarded_content = True
                    elif component.file:
                        chain.image(file=component.file)
                        has_forwarded_content = True
                except Exception as e:
                    logger.error(f"[DiscordForwarder] Error forwarding image: {e}")

            elif isinstance(component, File) and rule.forward_files:
                try:
                    # Get file information
                    file_name = component.name or "unknown_file"
                    file_url = component.url

                    if file_url:
                        # Forward file using URL (Discord attachment URL)
                        # The File component will handle the download when needed
                        logger.info(
                            f"[DiscordForwarder] Forwarding file: {file_name}, URL: {file_url}"
                        )
                        # MessageChain doesn't have a file() method, so we append directly
                        chain.chain.append(File(name=file_name, url=file_url))
                        has_forwarded_content = True
                    else:
                        # Try to get file from local path
                        file_path = await component.get_file(allow_return_url=True)
                        if file_path:
                            logger.info(
                                f"[DiscordForwarder] Forwarding file: {file_name}, path: {file_path}"
                            )
                            # Check if it's a URL or local path
                            if file_path.startswith("http://") or file_path.startswith("https://"):
                                chain.chain.append(File(name=file_name, url=file_path))
                            else:
                                chain.chain.append(File(name=file_name, file=file_path))
                            has_forwarded_content = True
                        else:
                            logger.warning(
                                f"[DiscordForwarder] Could not get file content for: {file_name}"
                            )
                except Exception as e:
                    logger.error(f"[DiscordForwarder] Error forwarding file: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

        # If no components found, try to get plain text from message_str
        if not has_forwarded_content and rule.forward_text:
            text = event.message_str or ""
            if text.strip():
                chain.message(text)
                has_forwarded_content = True

        return chain if has_forwarded_content else None

    @filter.platform_adapter_type(filter.PlatformAdapterType.DISCORD)
    async def on_discord_message(self, event: AstrMessageEvent):
        """
        Handle all Discord messages and forward if matching a rule.
        This handler catches all Discord messages without requiring a command.
        """
        # Skip if plugin is disabled
        if not self.enabled:
            return

        # Find matching rule
        rule = self._get_matching_rule(event)
        if not rule:
            return

        # Skip bot messages if configured
        if rule.ignore_bot_messages and self._is_bot_message(event):
            logger.debug("[DiscordForwarder] Skipping bot message")
            return

        try:
            # Build the forwarded message
            forward_chain = await self._build_forwarded_message(event, rule)

            if not forward_chain:
                logger.debug("[DiscordForwarder] No content to forward")
                return

            # Build destination session ID
            # Format: platform_id:GroupMessage:<channel_id>
            dest_session = f"{rule.platform_id}:GroupMessage:{rule.destination_channel_id}"

            logger.info(
                f"[DiscordForwarder] Forwarding message from platform '{rule.platform_id}' "
                f"to channel {rule.destination_channel_id}"
            )

            # Send to destination channel
            success = await self.context.send_message(dest_session, forward_chain)

            if success:
                logger.info("[DiscordForwarder] Message forwarded successfully")
                # Note: We intentionally do NOT call event.stop_event() here
                # to allow other plugins (like video_vision) to also process the message
                # If you want to block LTM from responding, configure it separately
            else:
                logger.warning(
                    "[DiscordForwarder] Failed to forward message - platform not found"
                )

        except Exception as e:
            logger.error(f"[DiscordForwarder] Error forwarding message: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @filter.command("forward_status")
    async def forward_status(self, event: AstrMessageEvent):
        """Check the forwarder plugin status."""
        status_parts = [
            "**Discord Forwarder Status**",
            f"- Plugin Enabled: {self.enabled}",
            f"- Total Rules: {len(self.forward_rules)}",
            "",
            "**Forwarding Rules:**",
        ]

        for i, rule in enumerate(self.forward_rules, 1):
            status_parts.extend([
                f"\n**Rule {i}:**",
                f"  - Platform ID: {rule.platform_id}",
                f"  - Source Channel: {rule.source_channel_id or 'Not configured'}",
                f"  - Destination Channel: {rule.destination_channel_id or 'Not configured'}",
                f"  - Enabled: {rule.enabled}",
                f"  - Forward Images: {rule.forward_images}",
                f"  - Forward Text: {rule.forward_text}",
                f"  - Forward Files: {rule.forward_files}",
            ])

        yield event.plain_result("\n".join(status_parts))

    @filter.command("forward_test")
    async def forward_test(self, event: AstrMessageEvent):
        """Test forwarding a message to the destination channel of the first rule."""
        if not self.forward_rules:
            yield event.plain_result("No forwarding rules configured!")
            return

        rule = self.forward_rules[0]
        if not rule.destination_channel_id:
            yield event.plain_result("Destination channel not configured for the first rule!")
            return

        try:
            test_chain = MessageChain().message("Test message from Discord Forwarder!")
            dest_session = f"{rule.platform_id}:GroupMessage:{rule.destination_channel_id}"
            success = await self.context.send_message(dest_session, test_chain)

            if success:
                yield event.plain_result(
                    f"Test message sent to channel {rule.destination_channel_id} via platform '{rule.platform_id}'!"
                )
            else:
                yield event.plain_result(
                    f"Failed to send test message. Make sure platform '{rule.platform_id}' is connected."
                )
        except Exception as e:
            yield event.plain_result(f"Error: {e}")
