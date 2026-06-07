"""
Force Join Channel middleware.
Checks if user has joined the required channel before allowing bot usage.
If not joined, shows a message asking them to join first.
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from config import settings

logger = logging.getLogger(__name__)


async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if the user has joined the required channel.

    Returns:
        True if user has joined (or force join is disabled)
        False if user has NOT joined (and a message was sent)
    """
    channel = settings.FORCE_JOIN_CHANNEL
    if not channel:
        # Force join not configured, allow all
        return True

    # Get user info
    if update.effective_user is None:
        return True

    user_id = update.effective_user.id

    try:
        # Check membership status
        chat_member = await context.bot.get_chat_member(
            chat_id=f"@{channel}",
            user_id=user_id,
        )

        # These statuses mean the user is in the channel
        if chat_member.status in [
            ChatMember.MEMBER,
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER,
        ]:
            return True

        # User is not a member
        await _send_join_message(update, channel)
        return False

    except TelegramError as e:
        # If we can't check (bot not admin in channel, etc.), log and allow
        logger.warning(f"Cannot check channel membership for user {user_id}: {e}")
        # If it's a "user not found" or "chat not found" error, ask to join
        if "user not found" in str(e).lower() or "member" in str(e).lower():
            await _send_join_message(update, channel)
            return False
        # For other errors (bot not admin, etc.), allow access
        return True
    except Exception as e:
        logger.error(f"Unexpected error checking force join: {e}")
        return True


async def _send_join_message(update: Update, channel: str):
    """Send the 'please join channel' message with button."""
    keyboard = [
        [
            InlineKeyboardButton(
                "📢 Join Channel",
                url=f"https://t.me/{channel}",
            ),
        ],
        [
            InlineKeyboardButton(
                "✅ I've Joined / Sudah Join",
                callback_data="check_joined",
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "    🔒 CHANNEL REQUIRED\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "To use this bot, you must first\n"
        "join our channel:\n\n"
        f"📢 @{channel}\n\n"
        "Click the button below to join,\n"
        "then click 'I've Joined' to verify.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Untuk menggunakan bot ini,\n"
        "kamu harus join channel dulu:\n\n"
        f"📢 @{channel}\n\n"
        "Klik tombol di bawah untuk join,\n"
        "lalu klik 'Sudah Join' untuk verifikasi.\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)


async def handle_check_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'I've Joined' button click — re-verify membership."""
    query = update.callback_query
    await query.answer()

    channel = settings.FORCE_JOIN_CHANNEL
    if not channel:
        await query.edit_message_text("✅ Welcome! Type /start to begin.")
        return

    user_id = update.effective_user.id

    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=f"@{channel}",
            user_id=user_id,
        )

        if chat_member.status in [
            ChatMember.MEMBER,
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER,
        ]:
            # User has joined!
            text = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "    ✅ VERIFIED!\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Thank you for joining! 🎉\n"
                "You can now use all bot features.\n\n"
                "Type /start to begin.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "Terima kasih sudah join! 🎉\n"
                "Kamu sekarang bisa pakai semua fitur.\n\n"
                "Ketik /start untuk mulai.\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )
            await query.edit_message_text(text)
        else:
            # Still not joined
            text = (
                "❌ You haven't joined the channel yet!\n"
                "❌ Kamu belum join channel!\n\n"
                f"Please join @{channel} first."
            )
            keyboard = [
                [
                    InlineKeyboardButton(
                        "📢 Join Channel",
                        url=f"https://t.me/{channel}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "✅ I've Joined / Sudah Join",
                        callback_data="check_joined",
                    ),
                ],
            ]
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except TelegramError as e:
        logger.error(f"Error verifying join for user {user_id}: {e}")
        await query.edit_message_text(
            "⚠️ Cannot verify. Make sure you've joined the channel, "
            "then try /start again."
        )
