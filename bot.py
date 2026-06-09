import json
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, ChatJoinRequestHandler, ContextTypes

BOT_TOKEN = "8562085984:AAGxwlLneP_8300_FEtH_X6jxsABaiuFmHU"
VIP_CHANNEL_ID = -1003923980912
DB_FILE = "vip_users.json"

WELCOME_MESSAGE = "✅ Your VIP join request has been approved.\n\nWelcome to FFM VIP 💎"

LEFT_MESSAGE = (
    "👋 Aap VIP channel se left ho gaye ho.\n\n"
    "Agar signals miss nahi karna chahte to wapas join kar lo ✅\n\n"
    "Support: @ffm_support"
)

def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    users = load_users()
    user_id = str(user.id)

    try:
        await update.chat_join_request.approve()
    except Exception as e:
        print("Approve error:", e)

    users[user_id] = {
        "id": user.id,
        "name": user.first_name,
        "username": user.username,
        "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "left_message_sent": False,
        "last_status": "approved"
    }
    save_users(users)

    try:
        await context.bot.send_message(chat_id=user.id, text=WELCOME_MESSAGE)
        print(f"✅ Approved + message sent: {user.id} - {user.first_name}")
    except Exception as e:
        print(f"Welcome DM error {user.id}: {e}")

async def check_members(context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    print(f"\n🔍 Checking users... total saved: {len(users)}")

    if not users:
        return

    changed = False

    for user_id, data in list(users.items()):
        if data.get("left_message_sent") is True:
            print(f"⏭️ Skip already sent: {user_id}")
            continue

        try:
            member = await context.bot.get_chat_member(
                chat_id=VIP_CHANNEL_ID,
                user_id=int(user_id)
            )

            status = member.status
            users[user_id]["last_status"] = status
            users[user_id]["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True

            print(f"👤 {user_id} | {data.get('name')} | status = {status}")

            if status in ["left", "kicked"]:
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=LEFT_MESSAGE
                    )
                    users[user_id]["left_message_sent"] = True
                    users[user_id]["left_detected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    changed = True
                    print(f"📩 LEFT DM SENT: {user_id}")

                except Exception as dm_error:
                    print(f"❌ LEFT DM FAILED {user_id}: {dm_error}")
                    users[user_id]["dm_error"] = str(dm_error)
                    changed = True

        except Exception as e:
            err = str(e)
            print(f"⚠️ Check error {user_id}: {err}")

            users[user_id]["last_status"] = "error"
            users[user_id]["last_error"] = err
            users[user_id]["last_checked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changed = True

            if "not found" in err.lower() or "participant" in err.lower():
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=LEFT_MESSAGE
                    )
                    users[user_id]["left_message_sent"] = True
                    users[user_id]["left_detected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"📩 LEFT DM SENT after not found: {user_id}")
                    changed = True
                except Exception as dm_error:
                    print(f"❌ LEFT DM FAILED after not found {user_id}: {dm_error}")
                    users[user_id]["dm_error"] = str(dm_error)
                    changed = True

    if changed:
        save_users(users)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatJoinRequestHandler(join_request))

    app.job_queue.run_repeating(
        check_members,
        interval=15,
        first=5
    )

    print("Bot started...")
    print("Status check every 15 seconds...")
    app.run_polling()

if __name__ == "__main__":
    main()
