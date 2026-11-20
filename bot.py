import asyncio
import os
import sys
import threading

from hydrogram import Client, filters
from hydrogram.enums import ChatType
from hydrogram.errors import FloodWait, SessionPasswordNeeded
from hydrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import API_HASH, API_ID, BOT_TOKEN, OWNER_ID, SESSION_DIR, START_IMG
from keep_alive import run_flask

# Flask server ko background thread mein start karein taaki Render port active rahe
threading.Thread(target=run_flask, daemon=True).start()

OWNER_ID = int(OWNER_ID)
os.makedirs(SESSION_DIR, exist_ok=True)

clients: list[Client] = []
login_states: dict[int, dict] = {}


def main_panel_caption() -> str:
  return (
      "✨ **ʙʀᴏᴀᴅᴄᴀsᴛ ᴍᴀsᴛᴇʀ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ** ✨\n\n"
      "⚡ **ᴍᴏᴅᴇ:** ʙᴏᴛ ᴛᴏᴋᴇɴ + ᴜʟᴛʀᴀ-ꜰᴀsᴛ ᴄᴏɴᴄᴜʀʀᴇɴᴛ\n\n"
      "┏ ⚙️ **sʏsᴛᴇᴍ sᴛᴀᴛᴜs:** ᴏɴʟɪɴᴇ (ʀᴜɴɴɪɴɢ)\n"
      f"┣ 📱 **ᴀᴄᴛɪᴠᴇ ᴀᴄᴄᴏᴜɴᴛs:** `{len(clients)}`\n"
      "┗ 🚀 **sᴘᴇᴇᴅ:** ᴍᴀxɪᴍɪᴢᴇᴅ (ᴀʟʟ ɢʀᴏᴜᴘs)\n\n"
      "_ᴄʜᴏᴏsᴇ ᴀɴ ᴏᴘᴛɪᴏɴ ʙᴇʟᴏᴡ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ:_"
  )


def main_panel_keyboard() -> InlineKeyboardMarkup:
  return InlineKeyboardMarkup([
      [
          InlineKeyboardButton("➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ", callback_data="add_account"),
          InlineKeyboardButton("📱 ᴀᴄᴄᴏᴜɴᴛs ʟɪsᴛ", callback_data="accounts_list"),
      ],
      [
          InlineKeyboardButton("📊 sᴛᴀᴛs", callback_data="stats"),
          InlineKeyboardButton("📚 ɢᴜɪᴅᴇ & ʜᴇʟᴘ", callback_data="guide"),
      ],
      [
          InlineKeyboardButton("🗑️ ʀᴇᴍᴏᴠᴇ ᴀʟʟ", callback_data="remove_all_cb"),
          InlineKeyboardButton("🔄 ᴜᴘᴅᴀᴛᴇ ᴀʟʟ", callback_data="update_all_cb"),
      ],
      [InlineKeyboardButton("🛠️ ᴍᴇɴᴜ", callback_data="menu")],
  ])


async def send_or_edit(
    message: Message, text: str, reply_markup=None, is_callback: bool = False
):
  if is_callback:
    try:
      if message.photo or message.caption:
        await message.edit_caption(caption=text, reply_markup=reply_markup)
      else:
        await message.edit_text(text=text, reply_markup=reply_markup)
      return
    except Exception:
      pass
  await message.reply(text, reply_markup=reply_markup)


async def _start_single_client(session_name: str, session_path: str):
  client = Client(session_path, api_id=API_ID, api_hash=API_HASH)
  try:
    await client.start()
    print(f"[+] Loaded session: {session_name}")
    return client
  except Exception as e:
    print(f"[-] Failed session {session_name}: {e}")
    return None


async def start_clients():
  global clients
  clients.clear()

  if not os.path.exists(SESSION_DIR):
    return

  session_tasks = []
  for filename in sorted(os.listdir(SESSION_DIR)):
    if filename.endswith(".session"):
      session_name = filename[:-8]
      session_path = os.path.join(SESSION_DIR, session_name)
      session_tasks.append(_start_single_client(session_name, session_path))

  if session_tasks:
    loaded = await asyncio.gather(*session_tasks)
    clients = [c for c in loaded if c is not None]


async def _stop_single_client(acc: Client):
  try:
    await acc.stop()
  except Exception as e:
    print(f"[-] Error stopping client: {e}")


async def stop_all_clients():
  global clients
  if not clients:
    return
  await asyncio.gather(*(_stop_single_client(acc) for acc in clients))
  clients.clear()


async def fast_restart_system(app: Client):
  await asyncio.gather(
      stop_all_clients(),
      app.stop(),
      return_exceptions=True,
  )
  os.execv(sys.executable, [sys.executable, *sys.argv])


async def main():
  print("[*] Initializing Bot Client...")

  app = Client(
      "bot_controller",
      api_id=API_ID,
      api_hash=API_HASH,
      bot_token=BOT_TOKEN,
      workdir=SESSION_DIR,
  )

  @app.on_message(filters.user(OWNER_ID) & filters.command("start"))
  async def start_cmd(client: Client, message: Message):
    print(f"[*] Received /start from Owner: {message.from_user.id}")
    caption = main_panel_caption()
    keyboard = main_panel_keyboard()

    try:
      if START_IMG:
        await message.reply_photo(
            photo=START_IMG, caption=caption, reply_markup=keyboard
        )
      else:
        await message.reply(caption, reply_markup=keyboard)
    except Exception as e:
      print(f"[-] Error sending start photo/message: {e}")
      await message.reply(caption, reply_markup=keyboard)

  @app.on_callback_query(filters.user(OWNER_ID))
  async def callback_handler(client: Client, callback: CallbackQuery):
    data = callback.data
    back_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_home")]]
    )

    if data == "add_account":
      await send_or_edit(
          callback.message,
          (
              "📲 **sᴇɴᴅ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ**\n\n_ᴇxᴀᴍᴘʟᴇ:_"
              " `+91xxxxxxxxxx`"
          ),
          reply_markup=back_kb,
          is_callback=True,
      )
      login_states[callback.from_user.id] = {"step": "waiting_phone"}
      await callback.answer()

    elif data == "accounts_list":
      await send_accounts_history(callback.message, is_callback=True)
      await callback.answer()

    elif data == "stats":
      stats_text = (
          "📊 **sʏsᴛᴇᴍ sᴛᴀᴛɪsᴛɪᴄs**\n\n"
          f"• **ʟᴏɢɢᴇᴅ-ɪɴ ᴀᴄᴄᴏᴜɴᴛs:** `{len(clients)}`\n"
          f"• **ᴏᴡɴᴇʀ ɪᴅ:** `{OWNER_ID}`\n"
          "• **ᴛᴀʀɢᴇᴛ:** ᴀʟʟ ɢʀᴏᴜᴘs & sᴜᴘᴇʀɢʀᴏᴜᴘs\n"
          "• **sᴛᴀᴛᴜs:** ʀᴜɴɴɪɴɢ sᴍᴏᴏᴛʜʟʏ & ғᴀsᴛ"
      )
      await send_or_edit(
          callback.message, stats_text, reply_markup=back_kb, is_callback=True
      )
      await callback.answer()

    elif data == "remove_all_cb":
      await execute_remove_all(callback.message)
      await callback.answer()

    elif data == "update_all_cb":
      await callback.answer("⚡ Fast updating all accounts...")
      await send_or_edit(
          callback.message,
          "⚡ **ꜰᴀsᴛ ᴜᴘᴅᴀᴛɪɴɢ & ʀᴇʟᴏᴀᴅɪɴɢ ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs...**",
          is_callback=True,
      )
      await fast_restart_system(app)

    elif data == "guide":
      guide_text = (
          "📚 **ᴄᴏᴍᴘʟᴇᴛᴇ ᴜsᴇʀ ɢᴜɪᴅᴇ**\n\n"
          "1️⃣ **ᴀᴅᴅɪɴɢ ᴀᴄᴄᴏᴜɴᴛs:** Click `➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ`, send phone number,"
          " OTP (`1 2 3 4 5`), and 2FA password.\n"
          "2️⃣ **ᴀᴄᴄᴏᴜɴᴛs ʟɪsᴛ:** Use `/accounts` or button to view active"
          " accounts.\n"
          "3️⃣ **ʀᴇᴍᴏᴠɪɴɢ ᴀʟʟ:** Use `/remove_all` to logout & delete all"
          " accounts instantly.\n"
          "4️⃣ **ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ:** Send any text/media message directly to bot;"
          " all added accounts will send it to all their groups!"
      )
      await send_or_edit(
          callback.message, guide_text, reply_markup=back_kb, is_callback=True
      )
      await callback.answer()

    elif data == "menu":
      menu_text = (
          "🛠️ **ᴀᴅᴠᴀɴᴄᴇᴅ ᴄᴏɴᴛʀᴏʟ ᴍᴇɴᴜ**\n\n"
          "• `/start` - ᴏᴘᴇɴ ᴍᴀɪɴ ᴘᴀɴᴇʟ\n"
          "• `/addaccount` - ᴅɪʀᴇᴄᴛ ʟᴏɢɪɴ\n"
          "• `/accounts` - ᴠɪᴇᴡ ᴀʟʟ ʟᴏɢɢᴇᴅ-ɪɴ ᴀᴄᴄᴏᴜɴᴛs\n"
          "• `/remove_all` - ʟᴏɢᴏᴜᴛ ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs\n"
          "• `/update_all` - ꜰᴀsᴛ ʀᴇʟᴏᴀᴅ & ʀᴇsᴛᴀʀᴛ ʙᴏᴛ"
      )
      menu_kb = InlineKeyboardMarkup([
          [InlineKeyboardButton("➕ ᴀᴅᴅ ᴀᴄᴄᴏᴜɴᴛ", callback_data="add_account")],
          [InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_home")],
      ])
      await send_or_edit(
          callback.message, menu_text, reply_markup=menu_kb, is_callback=True
      )
      await callback.answer()

    elif data == "back_home":
      await send_or_edit(
          callback.message,
          main_panel_caption(),
          reply_markup=main_panel_keyboard(),
          is_callback=True,
      )
      await callback.answer()

  @app.on_message(filters.user(OWNER_ID) & filters.command("accounts"))
  async def accounts_cmd(client: Client, message: Message):
    await send_accounts_history(message, is_callback=False)

  async def send_accounts_history(message: Message, is_callback: bool = False):
    if not clients:
      text = "⚠️ **No active accounts found!**\n\nUse `/addaccount` to login accounts."
    else:
      text = f"📱 **ᴀᴄᴛɪᴠᴇ ʟᴏɢɢᴇᴅ-ɪɴ ᴀᴄᴄᴏᴜɴᴛs ({len(clients)}):**\n\n"
      for idx, acc in enumerate(clients, 1):
        try:
          me = await acc.get_me()
          name = f"{me.first_name or ''} {me.last_name or ''}".strip()
          username = f"@{me.username}" if me.username else "No Username"
          phone = (
              f"+{me.phone_number}"
              if getattr(me, "phone_number", None)
              else "Hidden/Unknown"
          )
          text += (
              f"┏ **#{idx}**\n"
              f"┣ 👤 **ɴᴀᴍᴇ:** {name}\n"
              f"┣ 🆔 **ᴜsᴇʀɴᴀᴍᴇ:** {username}\n"
              f"┗ 📞 **ᴘʜᴏɴᴇ:** `{phone}`\n\n"
          )
        except Exception:
          text += (
              f"┏ **#{idx}**\n┗ ⚠️ Session active but info fetch failed.\n\n"
          )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("« ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data="back_home")]]
    )
    await send_or_edit(
        message, text, reply_markup=keyboard, is_callback=is_callback
    )

  @app.on_message(filters.user(OWNER_ID) & filters.command("addaccount"))
  async def add_account_cmd(client: Client, message: Message):
    await message.reply(
        "📲 **sᴇɴᴅ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ**\n\n_ᴇxᴀᴍᴘʟᴇ:_"
        " `+91xxxxxxxxxx`"
    )
    login_states[message.from_user.id] = {"step": "waiting_phone"}

  @app.on_message(filters.user(OWNER_ID) & filters.command("remove_all"))
  async def remove_all_cmd(client: Client, message: Message):
    await execute_remove_all(message)

  async def execute_remove_all(message: Message):
    count = len(clients)
    await stop_all_clients()

    if os.path.exists(SESSION_DIR):
      for filename in os.listdir(SESSION_DIR):
        if filename.endswith((".session", ".session-journal")):
          try:
            os.remove(os.path.join(SESSION_DIR, filename))
          except Exception:
            pass

    await message.reply(
        "🗑️ **ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs ʀᴇᴍᴏᴠᴇᴅ & ʟᴏɢɢᴇᴅ ᴏᴜᴛ!**\n\n• **ᴄʟᴇᴀʀᴇᴅ"
        f" sᴇssɪᴏɴs:** `{count}`"
    )

  @app.on_message(filters.user(OWNER_ID) & filters.command("update_all"))
  async def update_all_cmd(client: Client, message: Message):
    await message.reply(
        "⚡ **ꜰᴀsᴛ ᴜᴘᴅᴀᴛɪɴɢ & ʀᴇʟᴏᴀᴅɪɴɢ ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs...**"
    )
    await fast_restart_system(app)

  @app.on_message(
      filters.user(OWNER_ID)
      & ~filters.command(
          ["start", "addaccount", "accounts", "remove_all", "update_all"]
      )
  )
  async def handle_login_or_broadcast(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in login_states:
      await handle_ultra_fast_broadcast(client, message)
      return

    state = login_states[user_id]
    step = state.get("step")

    if step == "waiting_phone":
      if not message.text:
        await message.reply("❌ **Please send phone number as text.**")
        return

      phone_number = message.text.strip()
      state["phone_number"] = phone_number

      session_name = f"acc_{phone_number.replace('+', '')}"
      session_path = os.path.join(SESSION_DIR, session_name)

      temp_client = Client(session_path, api_id=API_ID, api_hash=API_HASH)
      state["temp_client"] = temp_client

      try:
        await temp_client.connect()
        sent_code = await temp_client.send_code(phone_number)
        state["phone_code_hash"] = sent_code.phone_code_hash
        state["step"] = "waiting_otp"
        await message.reply(
            "📩 **ᴇɴᴛᴇʀ ᴏᴛᴘ ᴡɪᴛʜ sᴘᴀᴄᴇs**\n\n_ᴇxᴀᴍᴘʟᴇ:_ `1 2 3 4 5`"
        )
      except Exception as e:
        await message.reply(f"❌ **Error:** `{e}`")
        try:
          await temp_client.disconnect()
        except Exception:
          pass
        login_states.pop(user_id, None)

    elif step == "waiting_otp":
      if not message.text:
        await message.reply("❌ **Please send OTP as text.**")
        return

      otp_code = message.text.replace(" ", "").strip()
      temp_client = state["temp_client"]
      phone_number = state["phone_number"]
      phone_code_hash = state["phone_code_hash"]

      try:
        await temp_client.sign_in(phone_number, phone_code_hash, otp_code)
        clients.append(temp_client)
        login_states.pop(user_id, None)
        await message.reply(
            "✅ **ᴀᴄᴄᴏᴜɴᴛ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴀᴅᴅᴇᴅ!**\nTotal active:"
            f" {len(clients)}"
        )
      except SessionPasswordNeeded:
        state["step"] = "waiting_2fa"
        await message.reply("🔐 **ᴇɴᴛᴇʀ ᴛᴡᴏ-sᴛᴇᴘ ᴘᴀssᴡᴏʀᴅ**")
      except Exception as e:
        await message.reply(f"❌ **OTP Error:** `{e}`")
        try:
          await temp_client.disconnect()
        except Exception:
          pass
        login_states.pop(user_id, None)

    elif step == "waiting_2fa":
      if not message.text:
        await message.reply("❌ **Please send 2FA password as text.**")
        return

      password = message.text.strip()
      temp_client = state["temp_client"]

      try:
        await temp_client.check_password(password)
        clients.append(temp_client)
        login_states.pop(user_id, None)
        await message.reply(
            "✅ **ᴀᴄᴄᴏᴜɴᴛ sᴜᴄᴄᴇssꜰᴜʟʟʏ ᴀᴅᴅᴇᴅ!**\nTotal active:"
            f" {len(clients)}"
        )
      except Exception as e:
        await message.reply(f"❌ **2FA Error:** `{e}`")
        try:
          await temp_client.disconnect()
        except Exception:
          pass
        login_states.pop(user_id, None)

  async def send_to_group(acc: Client, chat_id: int, source_message: Message):
    broadcast_text = source_message.text or source_message.caption or ""
    for _ in range(2):
      try:
        if source_message.media:
          await acc.copy_message(
              chat_id=chat_id,
              from_chat_id=source_message.chat.id,
              message_id=source_message.id,
          )
        elif broadcast_text:
          await acc.send_message(chat_id=chat_id, text=broadcast_text)
        else:
          return False
        return True
      except FloodWait as fw:
        await asyncio.sleep(fw.value + 1)
      except Exception as e:
        print(f"[-] Failed sending to group {chat_id}: {e}")
        return False
    return False

  async def broadcast_for_account(acc: Client, source_message: Message):
    group_chat_ids = []
    group_types = {ChatType.GROUP, ChatType.SUPERGROUP}

    try:
      async for dialog in acc.get_dialogs():
        if dialog.chat.type in group_types:
          group_chat_ids.append(dialog.chat.id)
    except Exception as e:
      print(f"[-] Error fetching dialogs for an account: {e}")
      return 0, 0, 0

    if not group_chat_ids:
      return 0, 0, 0

    results = await asyncio.gather(
        *(send_to_group(acc, chat_id, source_message) for chat_id in group_chat_ids)
    )
    success = sum(1 for ok in results if ok)
    fail = len(results) - success
    return len(group_chat_ids), success, fail

  async def handle_ultra_fast_broadcast(client: Client, message: Message):
    if message.text and message.text.startswith("/"):
      return
    if not clients:
      await message.reply(
          "⚠️ **No active accounts found!** Use `/addaccount` first."
      )
      return

    status_msg = await message.reply(
        "⚡ **ᴀʟʟ ᴀᴄᴄᴏᴜɴᴛs ɢʀᴏᴜᴘ ʙʀᴏᴀᴅᴄᴀsᴛ sᴛᴀʀᴛᴇᴅ...**"
    )
    tasks = [broadcast_for_account(acc, message) for acc in clients]
    results = await asyncio.gather(*tasks)

    total_groups = sum(r[0] for r in results)
    total_success = sum(r[1] for r in results)
    total_fail = sum(r[2] for r in results)

    await status_msg.edit(
        "🚀 **ᴀʟʟ ɢʀᴏᴜᴘs ʙʀᴏᴀᴅᴄᴀsᴛ ᴄᴏᴍᴘʟᴇᴛᴇᴅ!**\n\n"
        f"• **ᴀᴄᴄᴏᴜɴᴛs:** `{len(clients)}`\n"
        f"• **ᴛᴏᴛᴀʟ ɢʀᴏᴜᴘs:** `{total_groups}`\n"
        f"• **sᴜᴄᴄᴇss:** `{total_success}`\n"
        f"• **ꜰᴀɪʟᴇᴅ:** `{total_fail}`"
    )

  try:
    print("[*] Starting Saved Userbot Sessions...")
    await start_clients()
    print(f"[*] Total loaded broadcast accounts: {len(clients)}")

    print("[*] Starting Hydrogram Bot Polling...")
    await app.start()
    print("[*] Bot is fully running and listening for commands!")
    await asyncio.Event().wait()
  finally:
    print("[*] Shutting down clients...")
    await stop_all_clients()
    try:
      await app.stop()
    except Exception:
      pass


if __name__ == "__main__":
  try:
    asyncio.run(main())
  except KeyboardInterrupt:
    print("[!] Bot stopped manually.")
