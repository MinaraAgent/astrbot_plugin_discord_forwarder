"""
AstrBot Discord Message Forwarder Plugin

Forwards messages from a source Discord channel to a destination channel.
Supports text, images, and other message components.
"""

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image
from astrbot.core.message.message_event_result import MessageChain, CommandResult


@register(
    "astrbot_plugin_discord_forwarder",
    "Minara",
    "Discord message forwarding plugin - forwards messages between channels",
    "1.0.0",
)
class DiscordForwarderPlugin(Star):
    """Discord message forwarding plugin."""

    def __init__(self, context: Context, config: dict) -> None:
        super().__init__(context)
        self.config = config
        self.enabled = config.get("enabled", True)
        self.source_channel_id = str(config.get("source_channel_id", ""))
        self.destination_channel_id = str(config.get("destination_channel_id", ""))
        self.forward_images = config.get("forward_images", True)
        self.forward_text = config.get("forward_text", True)
        self.include_sender_info = config.get("include_sender_info", True)
        self.ignore_bot_messages = config.get("ignore_bot_messages", True)

    async def initialize(self) -> None:
        """Called when plugin is activated."""
        logger.info(
            f"[DiscordForwarder] Plugin initialized. "
            f"Source: {self.source_channel_id}, Destination: {self.destination_channel_id}"
        )

        if not self.source_channel_id or not self.destination_channel_id:
            logger.warning(
                "[DiscordForwarder] Source or destination channel ID not configured. "
                "Please configure the plugin in the WebUI."
            )

    async def terminate(self) -> None:
        """Called when plugin is disabled/reloaded."""
        logger.info("[DiscordForwarder] Plugin terminated.")

    def _is_from_source_channel(self, event: AstrMessageEvent) -> bool:
        """Check if the message is from the configured source channel."""
        # Get the session ID which contains the channel ID for Discord
        session_id = event.session_id or ""
        unified_origin = event.unified_msg_origin or ""

        # For Discord, session_id or unified_msg_origin contains the channel ID
        # Format: platform_discord_<channel_id> or just the channel_id
        logger.debug(
            f"[DiscordForwarder] Checking channel - session_id: {session_id}, unified_origin: {unified_origin}"
        )

        # Check if source channel ID matches
        return (
            self.source_channel_id in session_id
            or self.source_channel_id in unified_origin
            or session_id == self.source_channel_id
        )

    def _is_bot_message(self, event: AstrMessageEvent) -> bool:
        """Check if the message is from a bot."""
        try:
            # Access the raw Discord message object
            message_obj = event.message_obj
            if hasattr(message_obj, "raw_message"):
                raw_msg = message_obj.raw_message
                if raw_msg and hasattr(raw_msg, "author"):
                    return raw_msg.author.bot
        except Exception as e:
            logger.debug(f"[DiscordForwarder] Error checking bot status: {e}")
        return False

    async def _build_forwarded_message(
        self, event: AstrMessageEvent
    ) -> MessageChain:
        """Build the message chain to forward."""
        chain = MessageChain()

        # Add sender info if configured
        if self.include_sender_info:
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
            if isinstance(component, Plain) and self.forward_text:
                # Forward text
                text = component.text.strip()
                if text:
                    chain.message(text)
                    has_forwarded_content = True

            elif isinstance(component, Image) and self.forward_images:
                # Forward image
                try:
                    if component.url:
                        chain.image(url=component.url)
                        has_forwarded_content = True
                    elif component.path:
                        chain.image(path=component.path)
                        has_forwarded_content = True
                    elif component.file:
                        # Base64 or file object
                        chain.image(file=component.file)
                        has_forwarded_content = True
                except Exception as e:
                    logger.error(f"[DiscordForwarder] Error forwarding image: {e}")

        # If no components found, try to get plain text from message_str
        if not has_forwarded_content and self.forward_text:
            text = event.message_str or ""
            if text.strip():
                chain.message(text)
                has_forwarded_content = True

        return chain if has_forwarded_content else None

    @filter.platform_adapter_type(filter.PlatformAdapterType.DISCORD)
    async def on_discord_message(self, event: AstrMessageEvent):
        """
        Handle all Discord messages and forward if from source channel.
        This handler catches all Discord messages without requiring a command.
        """
        # Skip if plugin is disabled
        if not self.enabled:
            return

        # Skip if channels not configured
        if not self.source_channel_id or not self.destination_channel_id:
            return

        # Check if from source channel
        if not self._is_from_source_channel(event):
            return

        # Skip bot messages if configured
        if self.ignore_bot_messages and self._is_bot_message(event):
            logger.debug("[DiscordForwarder] Skipping bot message")
            return

        try:
            # Build the forwarded message
            forward_chain = await self._build_forwarded_message(event)

            if not forward_chain:
                logger.debug("[DiscordForwarder] No content to forward")
                return

            # Build destination session ID
            # Format: discord:GroupMessage:<channel_id>
            dest_session = f"discord:GroupMessage:{self.destination_channel_id}"

            logger.info(
                f"[DiscordForwarder] Forwarding message to channel {self.destination_channel_id}"
            )

            # Send to destination channel
            success = await self.context.send_message(dest_session, forward_chain)

            if success:
                logger.info("[DiscordForwarder] Message forwarded successfully")
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
            f"- Enabled: {self.enabled}",
            f"- Source Channel: {self.source_channel_id or 'Not configured'}",
            f"- Destination Channel: {self.destination_channel_id or 'Not configured'}",
            f"- Forward Images: {self.forward_images}",
            f"- Forward Text: {self.forward_text}",
            f"- Include Sender Info: {self.include_sender_info}",
            f"- Ignore Bot Messages: {self.ignore_bot_messages}",
        ]
        yield event.plain_result("\n".join(status_parts))

    @filter.command("forward_test")
    async def forward_test(self, event: AstrMessageEvent):
        """Test forwarding a message to the destination channel."""
        if not self.destination_channel_id:
            yield event.plain_result("Destination channel not configured!")
            return

        try:
            test_chain = MessageChain().message("Test message from Discord Forwarder!")

            dest_session = f"discord_{self.destination_channel_id}"
            success = await self.context.send_message(dest_session, test_chain)

            if success:
                yield event.plain_result(
                    f"Test message sent to channel {self.destination_channel_id}!"
                )
            else:
                yield event.plain_result(
                    "Failed to send test message. Make sure Discord platform is connected."
                )
        except Exception as e:
            yield event.plain_result(f"Error: {e}")
