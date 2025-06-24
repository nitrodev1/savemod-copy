import logging
import asyncio
from typing import Dict, Any, NamedTuple, Optional
import time
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


message_cache: Dict[int, Dict[str, Any]] = {}


ACTION_EDIT = "edit"
ACTION_DELETE = "delete"


# paste your token. Don't forget about turning on business mode :)
BOT_TOKEN = ""


class RecentsItem(NamedTuple):

    timestamp: int
    chat_id: int
    message_id: int
    action: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None

    @classmethod
    def from_edit(cls, message: Message, old_text: str) -> "RecentsItem":
        return cls(
            timestamp=int(time.time()),
            chat_id=message.chat.id,
            message_id=message.message_id,
            action=ACTION_EDIT,
            old_text=old_text,
            new_text=message.text,
        )


async def cache_message(msg: Message, types: str, user_id: int, caption: str = 'None') -> None:

    try:

        msg_id = int(f"{msg.chat.id}{msg.message_id}")
        

        message_data = {
            "message_id": msg_id,
            "chat_id": msg.chat.id,
            "user_full_name": msg.from_user.full_name if msg.from_user else "Unknown",
            "user_id": user_id,
            "message_type": types,
            "additional_info": caption
        }
        

        if types == 'text':
            message_data["text"] = msg.text or ''
            
        elif types == 'photo':
            message_data["text"] = msg.photo[-1].file_id
            message_data["additional_info"] = caption or msg.caption or 'None'
            
        elif types == 'video':
            message_data["text"] = msg.video.file_id
            message_data["additional_info"] = caption or msg.caption or 'None'
            
        elif types == 'video_note':
            message_data["text"] = msg.video_note.file_id
            
        elif types == 'voice':
            message_data["text"] = msg.voice.file_id
        

        message_cache[msg_id] = message_data
        logger.debug(f"Cached {types} message {msg_id}")
        
    except Exception as e:
        logger.exception(f"Error caching message: {e}")


async def handle_media(msg: Message, file_type: str, media_path: str, connection_user_id: int, bot: Bot) -> None:

    try:
        if not msg.reply_to_message:
            return
            
        media = getattr(msg.reply_to_message, file_type, None)
        if not media:
            return
            
        bot_info = await bot.get_me()
        
        if isinstance(media, list):
            media_file = media[-1]  
        else:
            media_file = media
            

        disappearing_markers = ['GA', 'Fg', 'Fw', 'GQ']

        file_id = media_file.file_id
        file = await bot.get_file(file_id)
        check = file.file_id[0:2]
        
        if check in disappearing_markers:

            if not os.path.exists(media_path):
                os.makedirs(media_path)
                
            local_file_path = f"{media_path}/{file.file_path.split('/')[-1]}"
            await bot.download_file(file.file_path, local_file_path)


            media_file = FSInputFile(local_file_path)
            caption = f'<b>☝️Сохранено с помощью @{bot_info.username}</b>'


            if file_type == 'photo':
                await bot.send_photo(connection_user_id, photo=media_file, caption=caption, parse_mode=ParseMode.HTML)
            elif file_type == 'video':
                await bot.send_video(connection_user_id, video=media_file, caption=caption, parse_mode=ParseMode.HTML)
            elif file_type == 'voice':
                await bot.send_voice(connection_user_id, voice=media_file, caption=caption, parse_mode=ParseMode.HTML)
            elif file_type == 'video_note':
                await bot.send_video(connection_user_id, video=media_file, caption=caption, parse_mode=ParseMode.HTML)


            os.remove(local_file_path)
            await asyncio.sleep(0.05)
        
    except Exception as e:
        logger.exception(f"Error handling {file_type}: {e}")
        await bot.send_message(connection_user_id, f"Ошибка: Не удалось обработать {file_type}.")


async def check_deleted_message(message_id: int, bot: Bot) -> None:

    try:

        cached_message = message_cache.get(message_id)
        
        if cached_message:

            user_id = cached_message.get("user_id")
            chat_id = cached_message.get("chat_id")
            sender_name = cached_message.get("user_full_name")
            message_content = cached_message.get("text")
            msg_type = cached_message.get("message_type")
            caption = cached_message.get("additional_info")
            
            del message_cache[message_id]
            
            if msg_type == 'text':
                await bot.send_message(user_id,
                    text=f"🗑 Это сообщение было удалено:\n\n"
                        f"Отправитель: <a href='tg://user?id={chat_id}'><b>{sender_name}</b></a>\n"
                        f"Текст: <blockquote><b>{message_content}</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)
                
            elif msg_type == 'photo':
                await bot.send_photo(user_id,
                    photo=message_content,
                    caption=f"🗑 Это фото было удалено:\n\n"
                            f"Отправитель: <a href='tg://user?id={chat_id}'><b>{sender_name}</b></a>\n"
                            f"{f'С содержанием: <code><b>{caption}</b></code>' if caption and caption != 'None' else ''}",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)
                
            elif msg_type == 'video':
                await bot.send_video(user_id,
                    video=message_content,
                    caption=f"🗑 Это видео было удалено:\n\n"
                            f"Отправитель: <a href='tg://user?id={chat_id}'><b>{sender_name}</b></a>\n"
                            f"{f'С содержанием: <code><b>{caption}</b></code>' if caption and caption != 'None' else ''}",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)
                
            elif msg_type == 'video_note':
                await bot.send_video(user_id,
                    video=message_content,
                    caption=f"🗑 Это видео было удалено:\n\n"
                            f"Отправитель: <a href='tg://user?id={chat_id}'><b>{sender_name}</b></a>\n"
                            f"{f'С содержанием: <code><b>{caption}</b></code>' if caption and caption != 'None' else ''}",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)
                
            elif msg_type == 'voice':
                await bot.send_voice(user_id,
                    voice=message_content,
                    caption=f"🗑 Это голосовое было удалено:\n\n"
                            f"Отправитель: <a href='tg://user?id={chat_id}'><b>{sender_name}</b></a>\n"
                            f"{f'С содержанием: <code><b>{caption}</b></code>' if caption and caption != 'None' else ''}",
                    parse_mode=ParseMode.HTML
                )
                await asyncio.sleep(0.05)
                
            logger.info(f"Notification sent for deleted {msg_type} message {message_id}")
            
    except Exception as e:
        logger.exception(f"Error checking deleted message: {e}")


def create_router() -> Router:
    
    router = Router(name="spy_router")
    
    @router.business_message(F.text)
    async def business_text_handler(msg: Message, bot: Bot) -> None:
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            if not msg.reply_to_message:
                await cache_message(
                    msg=msg,
                    types='text',
                    caption='None',
                    user_id=connection.user.id
                )
            else:
                if msg.from_user and msg.from_user.id == connection.user.id:
                    if msg.reply_to_message.photo:
                        await handle_media(msg, "photo", "photos", connection.user.id, bot)
                    elif msg.reply_to_message.video:
                        await handle_media(msg, "video", "videos", connection.user.id, bot)
                    elif msg.reply_to_message.video_note:
                        await handle_media(msg, "video_note", "videos", connection.user.id, bot)
                    elif msg.reply_to_message.voice:
                        await handle_media(msg, "voice", "voices", connection.user.id, bot)
                    else:
                        await cache_message(
                            msg=msg,
                            types='text',
                            caption='None',
                            user_id=connection.user.id
                        )
                else:
                    await cache_message(
                        msg=msg,
                        types='text',
                        caption='None',
                        user_id=connection.user.id
                    )
        except Exception as e:
            logger.exception(f"Error handling business text: {e}")

    @router.business_message(F.photo)
    async def business_photo_handler(msg: Message, bot: Bot) -> None:
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await cache_message(
                msg=msg,
                types='photo',
                caption=msg.caption,
                user_id=connection.user.id
            )

        except Exception as e:
            logger.exception(f"Error handling business photo: {e}")

    @router.business_message(F.video)
    async def business_video_handler(msg: Message, bot: Bot) -> None:
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await cache_message(
                msg=msg,
                types='video',
                caption=msg.caption,
                user_id=connection.user.id
            )

        except Exception as e:
            logger.exception(f"Error handling business video: {e}")

    @router.business_message(F.video_note)
    async def business_video_note_handler(msg: Message, bot: Bot) -> None:
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await cache_message(
                msg=msg,
                types='video_note',
                caption=msg.caption if hasattr(msg, 'caption') else None,
                user_id=connection.user.id
            )

        except Exception as e:
            logger.exception(f"Error handling business video note: {e}")

    @router.business_message(F.voice)
    async def business_voice_handler(msg: Message, bot: Bot) -> None:
        try:
            feedback = msg.business_connection_id
            connection = await bot.get_business_connection(feedback)

            await cache_message(
                msg=msg,
                types='voice',
                caption=msg.caption if hasattr(msg, 'caption') else None,
                user_id=connection.user.id
            )

        except Exception as e:
            logger.exception(f"Error handling business voice: {e}")

    @router.edited_business_message(F.text)
    async def business_edit_handler(message: Message, bot: Bot) -> None:
        try:
            msg_id = int(f"{message.chat.id}{message.message_id}")
            
            feedback = message.business_connection_id
            connection = await bot.get_business_connection(feedback)
            
            cached_message = message_cache.get(msg_id)
            
            if cached_message:
                old_text = cached_message.get("text")
                recent_item = RecentsItem.from_edit(message, old_text)
                
                cached_message["text"] = message.text
                
                if message.from_user and message.from_user.id == cached_message.get("user_id"):
                    return
                    
                await bot.send_message(
                    cached_message.get("user_id"),
                    f"🔏 Пользователь <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a> "
                    f"изменил сообщение:\n\n"
                    f"Старый текст: <blockquote><b>{old_text}</b></blockquote>\n"
                    f"Новый текст: <blockquote><b>{recent_item.new_text}</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
                
            else:
                new_cache = {
                    "message_id": msg_id,
                    "chat_id": message.chat.id,
                    "user_full_name": message.from_user.full_name if message.from_user else "Unknown",
                    "text": message.text,
                    "message_type": "text",
                    "additional_info": "none",
                    "user_id": connection.user.id
                }
                message_cache[msg_id] = new_cache
                
                if message.from_user and message.from_user.id == connection.user.id:
                    return
                    
                await bot.send_message(
                    connection.user.id,
                    f"🔏 Пользователь <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a> "
                    f"изменил сообщение, но старый текст отсутствует в кэше.\n\n"
                    f"Новый текст: <blockquote><b>{message.text}</b></blockquote>",
                    parse_mode=ParseMode.HTML
                )
                
            await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.exception(f"Error handling edited message: {e}")

    @router.deleted_business_messages()
    async def business_delete_handler(msg: Message, bot: Bot) -> None:
        try:
            for message_id in msg.message_ids:
                full_msg_id = int(f"{msg.chat.id}{message_id}")
                await check_deleted_message(message_id=full_msg_id, bot=bot)
        except Exception as e:
            logger.exception(f"Error handling deleted messages: {e}")

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            "Привет! Я бизнес-бот, который поможет отследить удаленные и измененные сообщения. "
            "Чтобы начать сохранять сообщения, просто подключи меня в разделе "Чат Боты" для телеграм бизнеса"
            "Только для подписчиков Telegram Premium"
        )

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        help_text = (
            "🔍 <b>Команды бота:</b>\n\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение помощи\n\n"
            "🔔 <b>Функции бота:</b>\n\n"
            "- Отслеживает <b>удаленные сообщения</b> и уведомляет вас о них\n"
            "- Сохраняет <b>измененные сообщения</b> и показывает старую и новую версии\n"
            "- Сохраняет <b>исчезающие фото и видео</b>, включая видеозаметки и голосовые сообщения\n\n"
            "Чтобы использовать бота, добавьте его через Telegram Business Tools в свою компанию."
        )
        await message.answer(help_text, parse_mode=ParseMode.HTML)

    return router

async def main() -> None:
    if not BOT_TOKEN:
        logger.error("Не указан BOT_TOKEN! Установите его в переменных окружения.")
        return
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(create_router())
    
    os.makedirs("photos", exist_ok=True)
    os.makedirs("videos", exist_ok=True)
    os.makedirs("voices", exist_ok=True)
    
    logger.info("Starting bot...")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
