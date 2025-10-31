import os
from dotenv import load_dotenv
import requests
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

load_dotenv()

async def receive_message(update: Update, context: CallbackContext) -> None:
    await context.bot.send_chat_action(
        chat_id=update.message.chat_id, 
        action="typing"
    )
    requests.post(
        url="http://0.0.0.0:8000/send_message",
        json={
            "chat_id": str(update.message.chat_id),
            "message": update.message.text,
        }
    )

def main():
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_message))

    print("Bot iniciado...")
    app.run_polling()

if __name__ == "__main__":
    main()
