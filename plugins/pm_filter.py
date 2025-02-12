from os import link
import random
import asyncio
import re, time
import math
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from Script import script
from datetime import datetime, timedelta
from info import QUALITIES, SEASONS, STICKERS_IDS, ADMINS, URL, MAX_BTN, BIN_CHANNEL, IS_STREAM, DELETE_TIME, FILMS_LINK, AUTH_CHANNEL, IS_VERIFY, VERIFY_EXPIRE, LOG_CHANNEL, SUPPORT_GROUP, SUPPORT_LINK, UPDATES_LINK, PICS, PROTECT_CONTENT, IMDB, AUTO_FILTER, SPELL_CHECK, IMDB_TEMPLATE, AUTO_DELETE, LANGUAGES, IS_FSUB, PAYMENT_QR, GROUP_FSUB, PM_SEARCH, UPI_ID, YEARS
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatPermissions, InputMediaPhoto
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, ChatAdminRequired
from utils import get_size, is_subscribed, is_check_admin, get_wish, get_shortlink, get_verify_status, update_verify_status, get_readable_time, get_poster, temp, get_settings, save_group_settings , imdb
from database.users_chats_db import db
from database.ia_filterdb import Media, get_file_details, get_search_results,delete_files
from fuzzywuzzy import process

# Ensure attributes exist before using them
if not hasattr(temp, "CHAT"):
    temp.CHAT = {}

if not hasattr(temp, "FILES_ID"):
    temp.FILES_ID = {}

BUTTONS = {}
CAP = {}
REACTIONS = ["🔥", "❤️", "😍", "⚡"]
#FILES_ID = {}

@Client.on_callback_query(filters.regex(r"^stream"))
async def aks_downloader(bot, query):
    file_id = query.data.split('#', 1)[1]
    msg = await bot.send_cached_media(chat_id=BIN_CHANNEL, file_id=file_id)
    watch = f"{URL}watch/{msg.id}"
    download = f"{URL}download/{msg.id}"
    btn= [[
        InlineKeyboardButton("ᴡᴀᴛᴄʜ ᴏɴʟɪɴᴇ", url=watch),
        InlineKeyboardButton("ꜰᴀsᴛ ᴅᴏᴡɴʟᴏᴀᴅ", url=download)
    ],[
        InlineKeyboardButton('❌ ᴄʟᴏsᴇ ❌', callback_data='close_data')
    ]]
    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(btn)
    )


async def add_movie_to_database(movie_title):
    try:
        # Database mein movie ko add karne ki logic
        movie_collection = db.movies  # Replace with your actual movie collection
        movie_data = {
            "title": movie_title,
            "added_at": datetime.now()
        }
        
        result = await movie_collection.insert_one(movie_data)
        return result.inserted_id is not None  # Success or failure
    except Exception as e:
        print(f"Error adding movie to database: {e}")
        return False

async def delete_request(movie_title):
    try:
        request_collection = db.movie_requests  # Replace with your actual requests collection
        await request_collection.delete_one({"movie_title": movie_title})
    except Exception as e:
        print(f"Error deleting request: {e}")

async def store_request(user_id, movie_title, group_id):
    try:
        request_data = {
            "user_id": user_id,
            "movie_title": movie_title,
            "group_id": group_id,
            "requested_at": datetime.now()
        }
        
        request_collection = db.movie_requests  # Replace with your actual requests collection
        await request_collection.insert_one(request_data)

        # Add movie to database and delete request if successful
        movie_added = await add_movie_to_database(movie_title)
        if movie_added:
            await delete_request(movie_title)
        return True
    except Exception as e:
        print(f"Error storing request: {e}")
        return False

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    await message.react(emoji=random.choice(REACTIONS))
    settings = await get_settings(message.chat.id)
    chatid = message.chat.id
    userid = message.from_user.id if message.from_user else None
    
    if GROUP_FSUB:
        btn = await is_subscribed(client, message, settings['fsub']) if settings.get('is_fsub', IS_FSUB) else None
        if btn:
            btn.append([InlineKeyboardButton("Unmute Me 🔕", callback_data=f"unmuteme#{chatid}")]
            )
            reply_markup = InlineKeyboardMarkup(btn)
            try:
                await client.restrict_chat_member(chatid, message.from_user.id, ChatPermissions(can_send_messages=False))
                await message.reply_photo(
                    photo=random.choice(PICS),
                    caption=f"👋 Hello {message.from_user.mention},\n\nPlease join and try again. 😇",
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )
                return
            except Exception as e:
                print(e)
    else:
        pass

    if settings["auto_filter"]:
        if not userid:
            await message.reply("I'm not working for anonymous admin!")
            return
        
        if message.chat.id == SUPPORT_GROUP:
            files, offset, total = await get_search_results(message.text)
            if files:
                btn = [[InlineKeyboardButton("Here", url=FILMS_LINK)]]
                await message.reply_text(f'Total {total} results found in this group', reply_markup=InlineKeyboardMarkup(btn))
            return
            
        if message.text.startswith("/"):
            return
            
        elif '@admin' in message.text.lower() or '@admins' in message.text.lower():
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            
            admins = []
            async for member in client.get_chat_members(chat_id=message.chat.id, filter=enums.ChatMembersFilter.ADMINISTRATORS):
                if not member.user.is_bot:
                    admins.append(member.user.id)
                    if member.status == enums.ChatMemberStatus.OWNER:
                        if message.reply_to_message:
                            try:
                                sent_msg = await message.reply_to_message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.reply_to_message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
                        else:
                            try:
                                sent_msg = await message.forward(member.user.id)
                                await sent_msg.reply_text(f"#Attention\n★ User: {message.from_user.mention}\n★ Group: {message.chat.title}\n\n★ <a href={message.link}>Go to message</a>", disable_web_page_preview=True)
                            except:
                                pass
            
            hidden_mentions = (f'[\u2064](tg://user?id={user_id})' for user_id in admins)
            await message.reply_text('Report sent!' + ''.join(hidden_mentions))
            return

        elif re.findall(r'https?://\S+|www\.\S+|t\.me/\S+', message.text):
            if await is_check_admin(client, message.chat.id, message.from_user.id):
                return
            await message.delete()
            return await message.reply('Links not allowed here!')
        
        elif '/request' in message.text.lower():
            if message.from_user.id in ADMINS:
                return
            movie_title = re.sub(r'/request', '', message.text.lower()).strip()
            await store_request(message.from_user.id, movie_title, message.chat.id)
            await message.reply_text("Request sent!")
            return
            
        else:
            await auto_filter(client, message)
    else:
        k = await message.reply_text('Auto Filter Off! ❌')
        await asyncio.sleep(5)
        await k.delete()
        try:
            await message.delete()
        except:
            pass


@Client.on_message(filters.private & filters.text)
async def pm_search(client, message):
    if PM_SEARCH:
        await auto_filter(client, message)
    else:
        files, n_offset, total = await get_search_results(message.text)
        if int(total) != 0:
            btn = [[
                InlineKeyboardButton("Here", url=FILMS_LINK)
            ]]
            await message.reply_text(f'Total {total} results found in this group', reply_markup=InlineKeyboardMarkup(btn))
            
@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    ident, req, key, offset = query.data.split("_")

    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    try:
        offset = int(offset)
    except ValueError:
        offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)

    if not search:
        await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
        return

    files, n_offset, total = await get_search_results(search, offset=offset)

    if not files:
        await query.answer("No results found!", show_alert=True)
        return

    temp.FILES[key] = files
    settings = await get_settings(query.message.chat.id)

    del_msg = (
        f"\n\n<b>⚠️ This message will be auto-deleted after <code>{get_readable_time(DELETE_TIME)}</code> to avoid copyright issues</b>"
        if settings["auto_delete"] else ''
    )

    files_link = ""
    btn = []

    if settings["links"]:
        for file_num, file in enumerate(files, start=offset + 1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn.extend([[InlineKeyboardButton(f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f"file#{file.file_id}")]
                    for file in files])

    if settings["shortlink"]:
        btn.insert(0, [
            InlineKeyboardButton("♻️ Send All ♻️", url=await get_shortlink(settings["url"], settings["api"], f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}")),
            InlineKeyboardButton("📰 Languages 📰", callback_data=f"languages#{key}#{req}#{offset}")
        ])
    else:
        btn.insert(0, [InlineKeyboardButton("♻️ Send All ♻️", callback_data=f"send_all#{key}")])
    
    btn.extend([
        [InlineKeyboardButton("✨ Quality 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
         InlineKeyboardButton("🚩 Year ⌛", callback_data=f"years#{key}#{offset}#{req}")],
        [InlineKeyboardButton("✨ Choose Season 🍿", callback_data=f"seasons#{key}#{offset}#{req}")]
    ])

    prev_offset = max(0, offset - MAX_BTN) if offset > 0 else None
    page_info = f"{math.ceil((offset + 1) / MAX_BTN)}/{math.ceil(total / MAX_BTN)}"

    navigation_buttons = []
    
    if prev_offset is not None:
        navigation_buttons.append(InlineKeyboardButton("« Back", callback_data=f"next_{req}_{key}_{prev_offset}"))

    navigation_buttons.append(InlineKeyboardButton(page_info, callback_data="buttons"))

    if n_offset != 0:
        navigation_buttons.append(InlineKeyboardButton("Next »", callback_data=f"next_{req}_{key}_{n_offset}"))

    btn.append(navigation_buttons)
    btn.append([InlineKeyboardButton("🚫 Close 🚫", callback_data="close_data")])

    try:
        await query.message.edit_text(
            cap + files_link + del_msg,
            reply_markup=InlineKeyboardMarkup(btn) if btn else None,
            disable_web_page_preview=True
        )
    except MessageNotModified:
        pass

@Client.on_callback_query(filters.regex(r"^languages"))
async def languages_cb_handler(client: Client, query: CallbackQuery):
    _, key, req, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
    btn = [[
        InlineKeyboardButton(text=lang.title(), callback_data=f"lang_search#{lang}#{key}#{offset}#{req}"),
    ]
        for lang in LANGUAGES
    ]
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʟᴀɴɢᴜᴀɢᴇ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ, sᴇʟᴇᴄᴛ ʜᴇʀᴇ</b>", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(btn))

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

@Client.on_callback_query(filters.regex(r"^lang_search"))
async def filter_languages_cb_handler(client: Client, query: CallbackQuery):
    _, lang, key, offset, req = query.data.split("#")
    
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    search = BUTTONS.get(key)  # Ensure BUTTONS is correctly imported
    cap = CAP.get(key)

    if not search:
        return await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)

    files, l_offset, total_results = await get_search_results(search, lang=lang)
    
    if not files:
        return await query.answer(f"Sorry '{lang.title()}' language files not found 😕", show_alert=True)

    settings = await get_settings(query.message.chat.id)
    
    del_msg = f"\n\n<b>⚠️ This message will be auto-deleted after <code>{get_readable_time(DELETE_TIME)}</code> to avoid copyright issues</b>" if settings["auto_delete"] else ''
    
    files_link = ''
    btn = []

    # ✅ Fix: List comprehension to store buttons properly
    if settings['links']:
        for file_num, file in enumerate(files, start=1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn += [
            [InlineKeyboardButton(text=f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f'file#{file.file_id}')]
            for file in files
        ]

    # ✅ Fix: Proper "Send All" button
    if settings['shortlink']:
        btn.append([
            InlineKeyboardButton("♻️ Send All ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))
        ])
    else:
        btn.append([
            InlineKeyboardButton("♻️ Send All ♻️", callback_data=f"send_all#{key}")
        ])

    # ✅ Fix: Correct Callback Buttons
    btn.append([
        InlineKeyboardButton("📰 Languages 📰", callback_data=f"languages#{key}#{req}#0")
    ])

    btn.append([
        InlineKeyboardButton("✨ Quality 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
        InlineKeyboardButton("🚩 Year ⌛", callback_data=f"years#{key}#{offset}#{req}")
    ])

    btn.append([
        InlineKeyboardButton("✨ Choose Season 🍿", callback_data=f"seasons#{key}#{offset}#{req}")
    ])

    if l_offset:
        btn.append([
            InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / MAX_BTN)}", callback_data="buttons"),
            InlineKeyboardButton(text="Next »", callback_data=f"lang_next#{req}#{key}#{lang}#{l_offset}#{offset}")
        ])
    else:
        btn.append([
            InlineKeyboardButton(text="🚸 No More Pages 🚸", callback_data="buttons")
        ])

    btn.append([
        InlineKeyboardButton(text="⪻ Back to Main Page", callback_data=f"next_{req}_{key}_{offset}")
    ])

    # ✅ Fix: Check if new text is different before editing
    new_text = cap + files_link + del_msg
    if query.message.text != new_text:
        await query.message.edit_text(new_text, disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(btn))
    else:
        await query.answer("Nothing to update!", show_alert=False)

@Client.on_callback_query(filters.regex(r"^lang_next"))
async def lang_next_page(bot, query):
    ident, req, key, lang, l_offset, offset = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    try:
        l_offset = int(l_offset)
    except:
        l_offset = 0

    search = BUTTONS.get(key)
    cap = CAP.get(key)
    settings = await get_settings(query.message.chat.id)
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    if not search:
        await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
        return 

    files, n_offset, total = await get_search_results(search, offset=l_offset, lang=lang)
    if not files:
        return
    temp.FILES[key] = files
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    files_link = ''

    if settings['links']:
        btn = []
        for file_num, file in enumerate(files, start=l_offset+1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"✨ {get_size(file.file_size)} ⚡️ {file.file_name}", callback_data=f'file#{file.file_id}')
        ]
            for file in files
        ]
    if settings['shortlink']:
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}")],
            [InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs 📰", callback_data=f"languages#{key}#{req}#0")],
            )
        btn.insert(1, [
            InlineKeyboardButton("✨ ǫᴜᴀʟɪᴛʏ 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
            InlineKeyboardButton("🚩 ʏᴇᴀʀ ⌛", callback_data=f"years#{key}#{offset}#{req}"),
            ])
        btn.insert(2, [
            InlineKeyboardButton("✨ ᴄʜᴏᴏsᴇ season🍿", callback_data=f"seasons#{key}#{offset}#{req}")
            ])

    if 0 < l_offset <= MAX_BTN:
        b_offset = 0
    elif l_offset == 0:
        b_offset = None
    else:
        b_offset = l_offset - MAX_BTN

    if n_offset == 0:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons")]
        )
    elif b_offset is None:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    else:
        btn.append(
            [InlineKeyboardButton("« ʙᴀᴄᴋ", callback_data=f"lang_next#{req}#{key}#{lang}#{b_offset}#{offset}"),
             InlineKeyboardButton(f"{math.ceil(int(l_offset) / MAX_BTN) + 1}/{math.ceil(total / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"lang_next#{req}#{key}#{lang}#{n_offset}#{offset}")]
        )
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)

@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, id, user = query.data.split('#')
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)

    movie = await get_poster(id, id=True)
    search = movie.get('title')
    await query.answer('Check In My Database...')
    files, offset, total_results = await get_search_results(search)
    if files:
        k = (search, files, offset, total_results)
        await auto_filter(bot, query, k)
    else:
        await bot.send_message(LOG_CHANNEL, script.NO_RESULT_TXT.format(query.message.chat.title, query.message.chat.id, query.from_user.mention, search))
        k = await query.message.edit(f"👋 Hello {query.from_user.mention},\n\nI don't find <b>'{search}'</b> in my database. 😔")
        await asyncio.sleep(60)
        await k.delete()
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
            
@Client.on_callback_query(filters.regex(r"^seasons#"))
async def seasons_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    
    if int(req) != query.from_user.id:
        return await query.answer(ALRT_TXT, show_alert=True) 

    btn = []
    for i in range(0, len(SEASONS) - 1, 3):
        btn.append([
            InlineKeyboardButton(
                text=SEASONS[i].title(),
                callback_data=f"season_search#{SEASONS[i].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=SEASONS[i+1].title(),
                callback_data=f"season_search#{SEASONS[i+1].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=SEASONS[i+2].title(),
                callback_data=f"season_search#{SEASONS[i+2].lower()}#{key}#0#{offset}#{req}"
            ),
        ])

    btn.append([InlineKeyboardButton(text="⪻ Back to Main Page", callback_data=f"next_{req}_{key}_{offset}")])
    
    await query.message.edit_text(
        "<b>In which season do you want? Choose from here ↓↓</b>",
        reply_markup=InlineKeyboardMarkup(btn)
    )
    return

@Client.on_callback_query(filters.regex(r"^season_search#"))
async def season_search(client: Client, query: CallbackQuery):
    _, season, key, offset, original_offset, req = query.data.split("#")

    if int(req) != query.from_user.id:
        return await query.answer(ALRT_TXT, show_alert=True)

    offset = int(offset)

    # ✅ Ensure temp.BUTTONS and temp.CAP exist
    search = temp.BUTTONS.get(key, None)
    cap = temp.CAP.get(key, "")

    if not search:
        return await query.answer(OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)

    search = search.replace("_", " ")
    
    files, n_offset, total = await get_search_results(f"{search} {season}", max_results=int(MAX_BTN), offset=offset)

    if not files:
        return await query.answer(f"Sorry, {season.title()} not found for {search}", show_alert=True)

    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = files
    temp.CHAT[query.from_user.id] = query.message.chat.id

    settings = await get_settings(query.message.chat.id)
    del_msg = (
        f"\n\n<b>⚠️ This message will auto-delete after <code>{get_readable_time(DELETE_TIME)}</code> to avoid copyright issues.</b>"
        if settings["auto_delete"] else ''
    )

    btn = [[InlineKeyboardButton(f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f'file#{file.file_id}')] for file in files]

    btn.insert(0, [InlineKeyboardButton("♻️ Send All", callback_data=f"send_all#{key}")])
    btn.insert(1, [InlineKeyboardButton("📰 Languages", callback_data=f"languages#{key}#{req}#{offset}")])
    btn.insert(2, [InlineKeyboardButton("✨ Quality", callback_data=f"qualities#{key}#{offset}#{req}")])
    btn.insert(3, [InlineKeyboardButton("🚩 Year", callback_data=f"years#{key}#{offset}#{req}")])
    btn.insert(4, [InlineKeyboardButton("✨ Choose Season", callback_data=f"seasons#{key}#{offset}#{req}")])

    if not n_offset:
        btn.append([InlineKeyboardButton("🚸 No More Pages 🚸", callback_data="buttons")])
    else:
        btn.append([
            InlineKeyboardButton("⪻ Back", callback_data=f"season_search#{season}#{key}#{offset - int(MAX_BTN)}#{original_offset}#{req}"),
            InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages"),
            InlineKeyboardButton("Next ⪼", callback_data=f"season_search#{season}#{key}#{n_offset}#{original_offset}#{req}")
        ])

    btn.append([InlineKeyboardButton("⪻ Back to Main Page", callback_data=f"next_{req}_{key}_{original_offset}")])

    new_text = str(cap) + str(del_msg)
    
    # ✅ Fix: Only edit if text is different
    if query.message.text != new_text:
        await query.message.edit_text(
            new_text,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(btn)
        )
    else:
        await query.answer("Nothing to update!", show_alert=False)

@Client.on_callback_query(filters.regex(r"^years#"))
async def years_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    btn  = []
    for i in range(0, len(YEARS)-1, 3):
        btn.append([
            InlineKeyboardButton(
                text=YEARS[i].title(),
                callback_data=f"years_search#{YEARS[i].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=YEARS[i+1].title(),
                callback_data=f"years_search#{YEARS[i+1].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=YEARS[i+2].title(),
                callback_data=f"years_search#{YEARS[i+2].lower()}#{key}#0#{offset}#{req}"
            ),
        ])
    
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ʏᴇᴀʀ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ғʀᴏᴍ ʜᴇʀᴇ ↓↓</b>", reply_markup=InlineKeyboardMarkup(btn))
    return

@Client.on_callback_query(filters.regex(r"^years_search#"))
async def year_search(client: Client, query: CallbackQuery):
    _, year, key, offset, orginal_offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)	
    offset = int(offset)
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return 
    search = search.replace("_", " ")
    files, n_offset, total = await get_search_results(f"{search} {year}", max_results=int(MAX_BTN), offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    files = [file for file in files if re.search(year, file.file_name, re.IGNORECASE)]
    if not files:
        await query.answer(f"sᴏʀʀʏ ʏᴇᴀʀ {year.title()} ɴᴏᴛ ғᴏᴜɴᴅ ғᴏʀ {search}", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id if query.from_user else 0
    settings = await get_settings(query.message.chat.id)
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    files_link = ''

    if settings['links']:
        btn = []
        for file_num, file in enumerate(files, start=1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f'file#{file.file_id}')
        ]
            for file in files
        ]
    if settings['shortlink']:
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        btn.insert(0,[
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs 📰", callback_data=f"languages#{key}#{req}#{offset}")],
            ])
        btn.insert(1, [
            InlineKeyboardButton("✨ ǫᴜᴀʟɪᴛʏ 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
            InlineKeyboardButton("🚩 ʏᴇᴀʀ ⌛", callback_data=f"years#{key}#{offset}#{req}"),
        ])
        btn.insert(2, [
            InlineKeyboardButton("✨ ᴄʜᴏᴏsᴇ season🍿", callback_data=f"seasons#{key}#{offset}#{req}")
        ])
    
    if n_offset== '':
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    elif n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"years_search#{year}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
            ])
    elif offset==0:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}",callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"years_search#{year}#{key}#{n_offset}#{orginal_offset}#{req}"),])
    else:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"years_search#{year}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"years_search#{year}#{key}#{n_offset}#{orginal_offset}#{req}"),])

    btn.append([
        InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{orginal_offset}"),])
    await query.message.edit_text(cap + link + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    return

@Client.on_callback_query(filters.regex(r"^qualities#"))
async def quality_cb_handler(client: Client, query: CallbackQuery):
    _, key, offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)
    btn= []
    for i in range(0, len(QUALITIES)-1, 3):
        btn.append([
            InlineKeyboardButton(
                text=QUALITIES[i].title(),
                callback_data=f"quality_search#{QUALITIES[i].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=QUALITIES[i+1].title(),
                callback_data=f"quality_search#{QUALITIES[i+1].lower()}#{key}#0#{offset}#{req}"
            ),
            InlineKeyboardButton(
                text=QUALITIES[i+2].title(),
                callback_data=f"quality_search#{QUALITIES[i+2].lower()}#{key}#0#{offset}#{req}"
            ),
        ])
    btn.append([InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{offset}")])
    await query.message.edit_text("<b>ɪɴ ᴡʜɪᴄʜ ǫᴜᴀʟɪᴛʏ ᴅᴏ ʏᴏᴜ ᴡᴀɴᴛ, ᴄʜᴏᴏsᴇ ғʀᴏᴍ ʜᴇʀᴇ ↓↓</b>", reply_markup=InlineKeyboardMarkup(btn))
    return

@Client.on_callback_query(filters.regex(r"^quality_search#"))
async def quality_search(client: Client, query: CallbackQuery):
    _, qul, key, offset, orginal_offset, req = query.data.split("#")
    if int(req) != query.from_user.id:
        return await query.answer(script.ALRT_TXT, show_alert=True)	
    offset = int(offset)
    search = BUTTONS.get(key)
    cap = CAP.get(key)
    if not search:
        await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name),show_alert=True)
        return 
    search = search.replace("_", " ")
    files, n_offset, total = await get_search_results(f"{search} {qul}", max_results=int(MAX_BTN), offset=offset)
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0
    files = [file for file in files if re.search(qul, file.file_name, re.IGNORECASE)]
    if not files:
        await query.answer(f"sᴏʀʀʏ ǫᴜᴀʟɪᴛʏ {qul.title()} ɴᴏᴛ ғᴏᴜɴᴅ ғᴏʀ {search}", show_alert=1)
        return

    batch_ids = files
    temp.FILES_ID[f"{query.message.chat.id}-{query.id}"] = batch_ids
    batch_link = f"batchfiles#{query.message.chat.id}#{query.id}#{query.from_user.id}"

    reqnxt = query.from_user.id if query.from_user else 0
    settings = await get_settings(query.message.chat.id)
    temp.CHAT[query.from_user.id] = query.message.chat.id
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    files_link = ''

    if settings['links']:
        btn = []
        for file_num, file in enumerate(files, start=1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f'file#{file.file_id}')
        ]
            for file in files
        ]
    if settings['shortlink']:
        btn.insert(0,
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}'))]
        )
    else:
        btn.insert(0,[
            [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
            InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs 📰", callback_data=f"languages#{key}#{req}#{offset}")],
            ])
        btn.insert(1, [
            InlineKeyboardButton("✨ ǫᴜᴀʟɪᴛʏ 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
            InlineKeyboardButton("🚩 ʏᴇᴀʀ ⌛", callback_data=f"years#{key}#{offset}#{req}"),
        ])
        btn.insert(2, [
            InlineKeyboardButton("✨ ᴄʜᴏᴏsᴇ season🍿", callback_data=f"seasons#{key}#{offset}#{req}")
        ])
    
    if n_offset== '':
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    elif n_offset == 0:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"quality_search#{qul}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
            ])
    elif offset==0:
        btn.append(
            [InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}",callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"quality_search#{qul}#{key}#{n_offset}#{orginal_offset}#{req}"),])
    else:
        btn.append(
            [InlineKeyboardButton("⪻ ʙᴀᴄᴋ", callback_data=f"quality_search#{qul}#{key}#{offset- int(MAX_BTN)}#{orginal_offset}#{req}"),
             InlineKeyboardButton(f"{math.ceil(offset / int(MAX_BTN)) + 1}/{math.ceil(total / int(MAX_BTN))}", callback_data="pages",),
             InlineKeyboardButton("ɴᴇxᴛ ⪼", callback_data=f"quality_search#{qul}#{key}#{n_offset}#{orginal_offset}#{req}"),])

    btn.append([
        InlineKeyboardButton(text="⪻ ʙᴀᴄᴋ ᴛᴏ ᴍᴀɪɴ ᴘᴀɢᴇ", callback_data=f"next_{req}_{key}_{orginal_offset}"),])
    await query.message.edit_text(cap + link + del_msg, disable_web_page_preview=True, parse_mode=enums.ParseMode.HTML, reply_markup=InlineKeyboardMarkup(btn))
    return
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^Upi"))
async def upi_payment_info(client, callback_query):
    cmd = callback_query.message
    btn = [[            
        InlineKeyboardButton("ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ 🧾", user_id=admin)
    ]
        for admin in ADMINS
    ]
    btn.append(
        [
            InlineKeyboardButton("QR ᴄᴏᴅᴇ", callback_data="qrcode_info") ,                   
            InlineKeyboardButton("UPI ID", callback_data="upiid_info")
        ]
    )
    btn.append(
        [            
            InlineKeyboardButton("⇚ Bᴀᴄᴋ", callback_data="buy_premium")
        ]
    ) 
    reply_markup = InlineKeyboardMarkup(btn)
    await client.edit_message_media(
        cmd.chat.id, 
        cmd.id, 
        InputMediaPhoto('https://graph.org/file/012b0fd51192f9e6506c0.jpg')
    )
    
    await cmd.edit(
        f"<b>👋 ʜᴇʏ {cmd.from_user.mention},\n    \n⚜️ ᴘᴀʏ ᴀᴍᴍᴏᴜɴᴛ ᴀᴄᴄᴏʀᴅɪɴɢ ᴛᴏ ʏᴏᴜʀ ᴘʟᴀɴ ᴀɴᴅ ᴇɴᴊᴏʏ ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀꜱʜɪᴘ !\n\n💵 ᴜᴘɪ ɪᴅ - <code>{UPI_ID}</code>\n\n‼️ ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ.</b>",
        reply_markup = reply_markup
    )

@Client.on_callback_query(filters.regex(r"^qrcode_info"))
async def qr_code_info(client, callback_query):
    cmd = callback_query.message
    btn = [[            
        InlineKeyboardButton("ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ 🧾", user_id=admin)
    ]
        for admin in ADMINS
    ]
    btn.append(
        [InlineKeyboardButton("⇚ Bᴀᴄᴋ", callback_data="Upi")]
    )
    reply_markup = InlineKeyboardMarkup(btn)
    await client.edit_message_media(
        cmd.chat.id, 
        cmd.id, 
        InputMediaPhoto(PAYMENT_QR)
    )
    await cmd.edit(
        f"<b>👋 ʜᴇʏ {cmd.from_user.mention},\n      \n⚜️ ᴘᴀʏ ᴀᴍᴍᴏᴜɴᴛ ᴀᴄᴄᴏʀᴅɪɴɢ ᴛᴏ ʏᴏᴜʀ ᴘʟᴀɴ ᴀɴᴅ ᴇɴᴊᴏʏ ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀꜱʜɪᴘ !\n\n‼️ ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ.</b>",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
            

@Client.on_callback_query(filters.regex(r"^upiid_info"))
async def upi_id_info(client, callback_query):
    cmd = callback_query.message
    btn = [[            
        InlineKeyboardButton("ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ 🧾", user_id=admin)
    ]
        for admin in ADMINS
    ]
    btn.append(
        [InlineKeyboardButton("⇚ Bᴀᴄᴋ", callback_data="Upi")]
    )
    reply_markup = InlineKeyboardMarkup(btn)
    await cmd.edit(
        f"<b>👋 ʜᴇʏ {cmd.from_user.mention},\n      \n⚜️ ᴘᴀʏ ᴀᴍᴍᴏᴜɴᴛ ᴀᴄᴄᴏʀᴅɪɴɢ ᴛᴏ ʏᴏᴜʀ ᴘʟᴀɴ ᴀɴᴅ ᴇɴᴊᴏʏ ᴘʀᴇᴍɪᴜᴍ ᴍᴇᴍʙᴇʀꜱʜɪᴘ !\n\n‼️ ᴍᴜsᴛ sᴇɴᴅ sᴄʀᴇᴇɴsʜᴏᴛ ᴀғᴛᴇʀ ᴘᴀʏᴍᴇɴᴛ.</b>\n\n💵 <code>{UPI_ID}</code>",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        try:
            user = query.message.reply_to_message.from_user.id
        except:
            user = query.from_user.id
        
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nThis Is Not For You!", show_alert=True)
        
        await query.answer("Closed!")
        await query.message.delete()
        
        try:
            await query.message.reply_to_message.delete()
        except:
            pass
  
    elif query.data.startswith("file"):
        try:
            data_parts = query.data.split("#")
            if len(data_parts) < 2:
                print("Invalid callback data:", query.data)
                return
            
            ident, file_id = data_parts[:2]
            user = query.message.reply_to_message.from_user.id
            
            if int(user) != 0 and query.from_user.id != int(user):
                return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
            
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start=file_{query.message.chat.id}_{file_id}")
        except Exception as e:
            print(f"Error in file callback: {e}")
    
    elif query.data == "get_trail":
        user_id = query.from_user.id
        free_trial_status = await db.get_free_trial_status(user_id)
        
        if not free_trial_status:            
            await db.give_free_trail(user_id)
            new_text = "**ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇs ꜰʀᴏᴍ ɴᴏᴡ 😀\n\nआप अब से 5 मिनट के लिए निःशुल्क ट्रायल का उपयोग कर सकते हैं 😀**"        
            await query.message.edit_text(text=new_text)
        else:
            new_text= "**🤣 you already used free now no more free trail. please buy subscription here are our 👉 /plans**"
            await query.message.edit_text(text=new_text)
        return
            
    elif query.data == "buy_premium":
        btn = [[
            InlineKeyboardButton("🏦 ꜱᴇʟᴇᴄᴛ ᴘᴀʏᴍᴇɴᴛ ᴍᴏᴅᴇ 🏧", callback_data="Upi")
        ]]            
            
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo="https://graph.org/file/ea8423d123dd90e34e10c.jpg",
            caption="**⚡️Buy Premium Now\n\n ╭━━━━━━━━╮\n    Premium Plans\n  • ₹10 - 1 day (Trial)\n  • ₹25 - 1 Week (Trial)\n  • ₹50 - 1 Month\n  • ₹120 - 3 Months\n  • ₹220 - 6 Months\n  • ₹400 - 1 Year\n╰━━━━━━━━╯\n\nPremium Features ♤ᵀ&ᶜ\n\n☆ New/Old Movies and Series\n☆ High Quality available\n☆ Get Files Directly \n☆ High speed Download links\n☆ Full Admin support \n☆ Request will be completed in 1 hour if available.\n\n**",
            reply_markup=reply_markup
        )
        return 
                
    elif query.data.startswith("checksub"):
        try:
            data_parts = query.data.split("#")
            if len(data_parts) < 2:
                print("Invalid callback data:", query.data)
                return
            
            ident, mc = data_parts[:2]
            settings = await get_settings(int(mc.split("_", 2)[1]))
            btn = await is_subscribed(client, query, settings['fsub'])
            
            if btn:
                await query.answer(f"Hello {query.from_user.first_name},\nPlease join my updates channel and try again.", show_alert=True)
                
                # 🛠️ Fix: btn.insert ke liye correct syntax
                btn.insert(0, [InlineKeyboardButton("🔁 Try Again 🔁", callback_data=f"checksub#{mc}")])
                
                await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
                return
            
            await query.answer(url=f"https://t.me/{temp.U_NAME}?start={mc}")
            await query.message.delete()
        
        except Exception as e:
            print(f"Error in checksub callback: {e}")

    elif query.data.startswith("unmuteme"):
        ident, chatid = query.data.split("#")
        settings = await get_settings(int(chatid))
        btn = await is_subscribed(client, query, settings['fsub'])
        if btn:
           await query.answer("Kindly Join Given Channel To Get Unmute", show_alert=True)
        else:
            await client.unban_chat_member(query.message.chat.id, user_id)
            await query.answer("Unmuted Successfully !", show_alert=True)
   
    elif query.data == "buttons":
        await query.answer("⚠️")

    elif query.data == "instructions":
        await query.answer("Movie request format.\nExample:\nBlack Adam or Black Adam 2022\n\nTV Reries request format.\nExample:\nLoki S01E01 or Loki S01 E01\n\nDon't use symbols.", show_alert=True)

    
    elif query.data == "start":
        await query.answer('Welcome!')
        buttons = [[
            InlineKeyboardButton('⤬ Aᴅᴅ Mᴇ Tᴏ Yᴏᴜʀ Gʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=start')
        ],[
            InlineKeyboardButton('🌿 ꜱᴜᴘᴘᴏʀᴛ', callback_data="my_about"),
            InlineKeyboardButton('👤 ᴏᴡɴᴇʀ', callback_data='my_owner')
        ],[
            InlineKeyboardButton('🍁 ғᴇᴀᴛᴜʀᴇs', callback_data='help'),
            InlineKeyboardButton('🔐 ᴘʀᴇᴍɪᴜᴍ', callback_data='buy_premium')
        ],[
            InlineKeyboardButton('💰 ᴇᴀʀɴ ᴍᴏɴᴇʏ ʙʏ ʙᴏᴛ 💰', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention, get_wish()),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "my_about":
        buttons = [[
            InlineKeyboardButton('📊 sᴛᴀᴛᴜs', callback_data='stats'),
            InlineKeyboardButton('🔋 sᴏᴜʀᴄᴇ ᴄᴏᴅᴇ', callback_data='source')
        ],[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_ABOUT_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    elif query.data == "stats":
        if query.from_user.id not in ADMINS:
            return await query.answer("ADMINS Only!", show_alert=True)
        files = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        u_size = get_size(await db.get_db_size())
        f_size = get_size(536870912 - await db.get_db_size())
        uptime = get_readable_time(time.time() - temp.START_TIME)
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='my_about')
        ]]
        await query.message.edit_text(script.STATUS_TXT.format(files, users, chats, u_size, f_size, uptime), reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    elif query.data == "my_owner":
        buttons = [[
            InlineKeyboardButton(text=f"☎️ ᴄᴏɴᴛᴀᴄᴛ - {(await client.get_users(admin)).first_name}", user_id=admin)
        ]
            for admin in ADMINS
        ]
        buttons.append(
            [InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start')]
        )
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MY_OWNER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "earn":
        buttons = [[
            InlineKeyboardButton('‼️ ʜᴏᴡ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ sʜᴏʀᴛɴᴇʀ ‼️', callback_data='howshort')
        ],[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EARN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "howshort":
        buttons = [[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='earn')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HOW_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('User Command', callback_data='user_command'),
            InlineKeyboardButton('Admin Command', callback_data='admin_command')
        ],[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='start')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "user_command":
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.USER_COMMAND_TXT,
            reply_markup=reply_markup
        )
        
    elif query.data == "admin_command":
        if query.from_user.id not in ADMINS:
            return await query.answer("ADMINS Only!", show_alert=True)
        buttons = [[
            InlineKeyboardButton('« ʙᴀᴄᴋ', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_COMMAND_TXT,
            reply_markup=reply_markup
        )

    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('≼ ʙᴀᴄᴋ', callback_data='my_about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

    
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        userid = query.from_user.id if query.from_user else None
        if not await is_check_admin(client, int(grp_id), userid):
            await query.answer("This Is Not For You!", show_alert=True)
            return

        if status == "True":
            await save_group_settings(int(grp_id), set_type, False)
            await query.answer("❌")
        else:
            await save_group_settings(int(grp_id), set_type, True)
            await query.answer("✅")

        settings = await get_settings(int(grp_id))

        if settings is not None:
            buttons = [[
                InlineKeyboardButton('Auto Filter', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}'),
                InlineKeyboardButton('✅ Yes' if settings["auto_filter"] else '❌ No', callback_data=f'setgs#auto_filter#{settings["auto_filter"]}#{grp_id}')
            ],[
                InlineKeyboardButton('File Secure', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}'),
                InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No', callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}')
            ],[
                InlineKeyboardButton('IMDb Poster', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}'),
                InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No', callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Spelling Check', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}'),
                InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No', callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Auto Delete', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}'),
                InlineKeyboardButton(f'{get_readable_time(DELETE_TIME)}' if settings["auto_delete"] else '❌ No', callback_data=f'setgs#auto_delete#{settings["auto_delete"]}#{grp_id}')
            ],[
                InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',),
                InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No', callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}'),
            ],[
                InlineKeyboardButton('Shortlink', callback_data=f'setgs#shortlink#{settings["shortlink"]}#{grp_id}'),
                InlineKeyboardButton('✅ Yes' if settings["shortlink"] else '❌ No', callback_data=f'setgs#shortlink#{settings["shortlink"]}#{grp_id}'),
            ],[
                InlineKeyboardButton('Result Page', callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}'),
                InlineKeyboardButton('⛓ Link' if settings["links"] else '🧲 Button', callback_data=f'setgs#links#{settings["links"]}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('Fsub', callback_data=f'setgs#is_fsub#{settings.get("is_fsub", IS_FSUB)}#{str(grp_id)}'),
                InlineKeyboardButton('✅ On' if settings.get("is_fsub", IS_FSUB) else '❌ Off', callback_data=f'setgs#is_fsub#{settings.get("is_fsub", IS_FSUB)}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('Stream', callback_data=f'setgs#is_stream#{settings.get("is_stream", IS_STREAM)}#{str(grp_id)}'),
                InlineKeyboardButton('✅ On' if settings.get("is_stream", IS_STREAM) else '❌ Off', callback_data=f'setgs#is_stream#{settings.get("is_stream", IS_STREAM)}#{str(grp_id)}')
            ],[
                InlineKeyboardButton('❌ Close ❌', callback_data='close_data')
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
        else:
            await query.message.edit_text("Something went wrong!")
            
    elif query.data == "delete_all":
        files = await Media.count_documents()
        await query.answer('Deleting...')
        await Media.collection.drop()
        await query.message.edit_text(f"Successfully deleted {files} files")
        
    elif query.data.startswith("delete"):
        _, query_ = query.data.split("_", 1)
        deleted = 0
        await query.message.edit('Deleting...')
        total, files = await delete_files(query_)
        async for file in files:
            await Media.collection.delete_one({'_id': file.file_id})
            deleted += 1
        await query.message.edit(f'Deleted {deleted} files in your database in your query {query_}')
     
    elif query.data.startswith("send_all"):
        ident, key = query.data.split("#")
        user = query.message.reply_to_message.from_user.id
        if int(user) != 0 and query.from_user.id != int(user):
            return await query.answer(f"Hello {query.from_user.first_name},\nDon't Click Other Results!", show_alert=True)
        
        files = temp.FILES.get(key)
        if not files:
            await query.answer(f"Hello {query.from_user.first_name},\nSend New Request Again!", show_alert=True)
            return        
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start=all_{query.message.chat.id}_{key}")


    elif query.data == "unmute_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        users_id = []
        await query.message.edit("Unmute all started! This process maybe get some time...")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.RESTRICTED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.unban_chat_member(query.message.chat.id, user_id)
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f'Something went wrong.\n\n<code>{e}</code>')
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"Successfully unmuted <code>{len(users_id)}</code> users.")
        else:
            await query.message.reply('Nothing to unmute users.')

    elif query.data == "unban_all_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        users_id = []
        await query.message.edit("Unban all started! This process maybe get some time...")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.BANNED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.unban_chat_member(query.message.chat.id, user_id)
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f'Something went wrong.\n\n<code>{e}</code>')
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"Successfully unban <code>{len(users_id)}</code> users.")
        else:
            await query.message.reply('Nothing to unban users.')

    elif query.data == "kick_muted_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        users_id = []
        await query.message.edit("Kick muted users started! This process maybe get some time...")
        try:
            async for member in client.get_chat_members(query.message.chat.id, filter=enums.ChatMembersFilter.RESTRICTED):
                users_id.append(member.user.id)
            for user_id in users_id:
                await client.ban_chat_member(query.message.chat.id, user_id, datetime.now() + timedelta(seconds=30))
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f'Something went wrong.\n\n<code>{e}</code>')
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"Successfully kicked muted <code>{len(users_id)}</code> users.")
        else:
            await query.message.reply('Nothing to kick muted users.')

    elif query.data == "kick_deleted_accounts_members":
        if not await is_check_admin(client, query.message.chat.id, query.from_user.id):
            await query.answer("This Is Not For You!", show_alert=True)
            return
        users_id = []
        await query.message.edit("Kick deleted accounts started! This process maybe get some time...")
        try:
            async for member in client.get_chat_members(query.message.chat.id):
                if member.user.is_deleted:
                    users_id.append(member.user.id)
            for user_id in users_id:
                await client.ban_chat_member(query.message.chat.id, user_id, datetime.now() + timedelta(seconds=30))
        except Exception as e:
            await query.message.delete()
            await query.message.reply(f'Something went wrong.\n\n<code>{e}</code>')
            return
        await query.message.delete()
        if users_id:
            await query.message.reply(f"Successfully kicked deleted <code>{len(users_id)}</code> accounts.")
        else:
            await query.message.reply('Nothing to kick deleted accounts.')

async def ai_spell_check(wrong_name):
    async def search_movie(wrong_name):
        search_results = imdb.search_movie(wrong_name)
        movie_list = [movie['title'] for movie in search_results]
        return movie_list
    movie_list = await search_movie(wrong_name)
    if not movie_list:
        return
    for _ in range(5):
        closest_match = process.extractOne(wrong_name, movie_list)
        if not closest_match or closest_match[1] <= 80:
            return 
        movie = closest_match[0]
        files, offset, total_results = await get_search_results(movie)
        if files:
            return movie
        movie_list.remove(movie)
    return


async def delSticker(st):
    try:
        await st.delete()
    except:
        pass
async def auto_filter(client, msg, spoll=False):
    thinkStc = ''
    thinkStc = await msg.reply_sticker(sticker=random.choice(STICKERS_IDS))
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        search = message.text
        files, offset, total_results = await get_search_results(search)
        if not files:
            if settings["spell_check"]:
                await delSticker(thinkStc)
                ai_sts = await msg.reply_text('<b>Ai is Cheking For Your Spelling. Please Wait.</b>')
                is_misspelled = await ai_spell_check(search)
                if is_misspelled:
                    await ai_sts.edit(f'<b>Ai Suggested <code>{is_misspelled}</code>\nSo Im Searching for <code>{is_misspelled}</code></b>')
                    await asyncio.sleep(2)
                    msg.text = is_misspelled
                    await ai_sts.delete()
                    return await auto_filter(client, msg)
                await delSticker(thinkStc)
                await ai_sts.delete()
                await advantage_spell_chok(msg)
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll
    if spoll:
        await msg.message.delete()
    req = message.from_user.id if message.from_user else 0
    key = f"{message.chat.id}-{message.id}"
    temp.FILES[key] = files
    BUTTONS[key] = search
    files_link = ""

    if settings['links']:
        btn = []
        for file_num, file in enumerate(files, start=1):
            files_link += f"""<b>\n\n{file_num}. <a href=https://t.me/{temp.U_NAME}?start=file_{message.chat.id}_{file.file_id}>[{get_size(file.file_size)}] {file.file_name}</a></b>"""
    else:
        btn = [[
            InlineKeyboardButton(text=f"📂 {get_size(file.file_size)} {file.file_name}", callback_data=f'file#{file.file_id}')
        ]
            for file in files
        ]
    
    if offset != "":
        if settings['shortlink']:
            btn.insert(0,
                [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{message.chat.id}_{key}')),
                InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs 📰", callback_data=f"languages#{key}#{req}#0")],
            )
            btn.insert(1, [
                InlineKeyboardButton("✨ ǫᴜᴀʟɪᴛʏ 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
                InlineKeyboardButton("🚩 ʏᴇᴀʀ ⌛", callback_data=f"years#{key}#{offset}#{req}"),
            ])
            btn.insert(2, [
                InlineKeyboardButton("✨ ᴄʜᴏᴏsᴇ season🍿", callback_data=f"seasons#{key}#{offset}#{req}")
            ])
        else:
            btn.insert(0,
                [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}"),
                InlineKeyboardButton("📰 ʟᴀɴɢᴜᴀɢᴇs 📰", callback_data=f"languages#{key}#{req}#0")],
            )
            btn.insert(1, [
                InlineKeyboardButton("✨ ǫᴜᴀʟɪᴛʏ 🤡", callback_data=f"qualities#{key}#{offset}#{req}"),
                InlineKeyboardButton("🚩 ʏᴇᴀʀ ⌛", callback_data=f"years#{key}#{offset}#{req}"),
            ])
            btn.insert(2, [
                InlineKeyboardButton("✨ ᴄʜᴏᴏsᴇ season🍿", callback_data=f"seasons#{key}#{offset}#{req}")
            ])

        btn.append(
            [InlineKeyboardButton(text=f"1/{math.ceil(int(total_results) / MAX_BTN)}", callback_data="buttons"),
             InlineKeyboardButton(text="ɴᴇxᴛ »", callback_data=f"next_{req}_{key}_{offset}")]
        )
    else:
        if settings['shortlink']:
            btn.insert(0,
                [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", url=await get_shortlink(settings['url'], settings['api'], f'https://t.me/{temp.U_NAME}?start=all_{message.chat.id}_{key}'))]
            )
        else:
            btn.insert(0,
                [InlineKeyboardButton("♻️ sᴇɴᴅ ᴀʟʟ ♻️", callback_data=f"send_all#{key}")]
            )
        btn.append(
            [InlineKeyboardButton(text="🚸 ɴᴏ ᴍᴏʀᴇ ᴘᴀɢᴇs 🚸", callback_data="buttons")]
        )
    btn.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    imdb = await get_poster(search, file=(files[0]).file_name) if settings["imdb"] else None
    TEMPLATE = settings['template']
    if imdb:
        cap = TEMPLATE.format(
            query=search,
            title=imdb['title'],
            votes=imdb['votes'],
            aka=imdb["aka"],
            seasons=imdb["seasons"],
            box_office=imdb['box_office'],
            localized_title=imdb['localized_title'],
            kind=imdb['kind'],
            imdb_id=imdb["imdb_id"],
            cast=imdb["cast"],
            runtime=imdb["runtime"],
            countries=imdb["countries"],
            certificates=imdb["certificates"],
            languages=imdb["languages"],
            director=imdb["director"],
            writer=imdb["writer"],
            producer=imdb["producer"],
            composer=imdb["composer"],
            cinematographer=imdb["cinematographer"],
            music_team=imdb["music_team"],
            distributors=imdb["distributors"],
            release_date=imdb['release_date'],
            year=imdb['year'],
            genres=imdb['genres'],
            poster=imdb['poster'],
            plot=imdb['plot'],
            rating=imdb['rating'],
            url=imdb['url'],
            **locals()
        )
    else:
        cap = f"<b>💭 ʜᴇʏ {message.from_user.mention},\n♻️ ʜᴇʀᴇ ɪ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ sᴇᴀʀᴄʜ {search}...</b>"
    CAP[key] = cap
    del_msg = f"\n\n<b>⚠️ ᴛʜɪs ᴍᴇssᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏ ᴅᴇʟᴇᴛᴇ ᴀꜰᴛᴇʀ <code>{get_readable_time(DELETE_TIME)}</code> ᴛᴏ ᴀᴠᴏɪᴅ ᴄᴏᴘʏʀɪɢʜᴛ ɪssᴜᴇs</b>" if settings["auto_delete"] else ''
    if imdb and imdb.get('poster'):
        try:
            if settings["auto_delete"]:
                await delSticker(thinkStc)
                k = await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), quote=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await delSticker(thinkStc)
                await message.reply_photo(photo=imdb.get('poster'), caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), quote=True)
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster')
            poster = pic.replace('.jpg', "._V1_UX360.jpg")
            if settings["auto_delete"]:
                await delSticker(thinkStc)
                k = await message.reply_photo(photo=poster, caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), quote=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await delSticker(thinkStc)
                await message.reply_photo(photo=poster, caption=cap[:1024] + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), quote=True)
        except Exception as e:
            if settings["auto_delete"]:
                await delSticker(thinkStc)
                k = await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, quote=True)
                await asyncio.sleep(DELETE_TIME)
                await k.delete()
                try:
                    await message.delete()
                except:
                    pass
            else:
                await delSticker(thinkStc)
                await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, quote=True)
    else:
        if settings["auto_delete"]:
            await delSticker(thinkStc)
            k = await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, quote=True)
            await asyncio.sleep(DELETE_TIME)
            await k.delete()
            try:
                await message.delete()
            except:
                pass
        else:
            await delSticker(thinkStc)
            await message.reply_text(cap + files_link + del_msg, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True, quote=True)

async def advantage_spell_chok(message):
    search = message.text
    google_search = search.replace(" ", "+")
    btn = [[
        InlineKeyboardButton("⚠️ Instructions ⚠️", callback_data='instructions'),
        InlineKeyboardButton("🔎 Search Google 🔍", url=f"https://www.google.com/search?q={google_search}")
    ]]
    try:
        movies = await get_poster(search, bulk=True)
    except:
        n = await message.reply_photo(photo=random.choice(PICS), caption=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return

    if not movies:
        n = await message.reply_photo(photo=random.choice(PICS), caption=script.NOT_FILE_TXT.format(message.from_user.mention, search), reply_markup=InlineKeyboardMarkup(btn))
        await asyncio.sleep(60)
        await n.delete()
        try:
            await message.delete()
        except:
            pass
        return

    user = message.from_user.id if message.from_user else 0
    buttons = [[
        InlineKeyboardButton(text=movie.get('title'), callback_data=f"spolling#{movie.movieID}#{user}")
    ]
        for movie in movies
    ]
    buttons.append(
        [InlineKeyboardButton("🚫 ᴄʟᴏsᴇ 🚫", callback_data="close_data")]
    )
    s = await message.reply_photo(photo=random.choice(PICS), caption=f"👋 Hello {message.from_user.mention},\n\nI couldn't find the <b>'{search}'</b> you requested.\nSelect if you meant one of these? 👇", reply_markup=InlineKeyboardMarkup(buttons), reply_to_message_id=message.id)
    await asyncio.sleep(300)
    await s.delete()
    try:
        await message.delete()
    except:
        pass

