import requests
import io
import os

from config import BOT_TOKEN, TOKEN_API_URL, ALPH_PRICE_API, DEFAULT_SUPPLY  # Import from config.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.constants import ChatAction

async def send_typing(update: Update, context: CallbackContext):
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action=ChatAction.TYPING)


async def get_alph_price():
    """Fetch real-time ALPH to USD conversion rate"""
    try:
        response = requests.get(ALPH_PRICE_API)
        data = response.json()
        return float(data["alephium"]["usd"])  # Extract ALPH price in USD
    except:
        return None  # Return None if API fails

async def start(update: Update, context: CallbackContext):
    await send_typing(update, context)  # Show typing action
    """Handles the /start command with styling"""
    keyboard = [
        # [InlineKeyboardButton("🔍 Search Token", switch_inline_query="")],
        [InlineKeyboardButton("📊 MyOnion.fun", url="https://myonion.fun")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        "👋 *Welcome to the MyOnion Token Bot!* 🍔\n\n"
        "💡 Send me a *token symbol or name*, and I'll fetch its details instantly!\n\n"
        "🔹 Try searching for `/layld` or `layld` to get started!\n"
    )
    await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def get_token_details(update: Update, context: CallbackContext, query: str):
    await send_typing(update, context)
    """Fetches token details using symbol, name, or contract address (ID)"""
    alph_price = await get_alph_price()

    params = {
        "pageSize": 10,
        "page": 0,
        "bondingPair": True,
        "dexPair": True,
        "search": query,
        "orderBy": "createdTimestamp"
    }

    response = requests.get(TOKEN_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get("data", [])

        if not data:
            await update.message.reply_text("❌ Token not found.")
            return

        token = data[0]

        name = token.get('name', 'Unknown')
        symbol = token.get('symbol', 'Unknown')
        contract = token.get('id', 'N/A')
        market_cap_alph = round(token.get('marketCap', 0), 2)
        volume_alph = round(token.get('volumeDaily', 0), 2)
        
        bonding_curve = token.get('bondingCurve', None)
        dex_pair = token.get('dexPair', None)
        
        logo_filename = token.get('logo', None)
        
        # Determine Status
        if bonding_curve and dex_pair:
            status = "Bonding Curve / AMM DEX"
        elif bonding_curve and not dex_pair:
            status = "Bonding Curve"
        else:
            status = "N/A"

        price = f"{market_cap_alph / DEFAULT_SUPPLY:.10f}" if market_cap_alph else "N/A"
        
        if alph_price:
            market_cap_usd = f"{market_cap_alph * alph_price:.2f}"
            volume_usd = f"{volume_alph * alph_price:.2f}"
            price_usd = f"{float(price) * alph_price:.10f}" if price != "N/A" else "N/A"
        else:
            market_cap_usd = "N/A"
            volume_usd = "N/A"
            price_usd = "N/A"

        if logo_filename:
            logo_url = f"https://file.myonion.fun/cdn-cgi/image/width=800,height=800,fit=crop,format=webp,quality=100/{logo_filename}"
        else:
            logo_url = None

        message = (
            f"🚀 *{name}* (`{symbol}`)\n\n"
            f"📜 *Contract:* `{contract}`\n"
            f"💰 *Price:* `{price} ℵ`  _(≈ ${price_usd})_\n"
            f"🏦 *Market Cap:* `{market_cap_alph} ℵ` _(≈ ${market_cap_usd})_\n"
            f"📈 *Daily Volume:* `{volume_alph} ℵ` _(≈ ${volume_usd})_\n"
            f"🔗 *Status:* `{status}`\n"
        )

        keyboard = [
            [InlineKeyboardButton("🔗 View on MyOnion.fun", url=f"https://myonion.fun/trade?tokenId={contract}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if logo_url:
            logo_response = requests.get(logo_url)
            if logo_response.status_code == 200:
                image_stream = io.BytesIO(logo_response.content)
                image_stream.name = "logo.jpg"
                await update.message.reply_photo(photo=InputFile(image_stream), caption=message, parse_mode="Markdown", reply_markup=reply_markup)
                return

        await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)

    else:
        await update.message.reply_text("⚠️ Failed to fetch token details. Try again later.")

async def handle_text(update: Update, context: CallbackContext):
    """Handles plain text queries (e.g., 'alpha')"""
    query = update.message.text.strip()
    await get_token_details(update, context, query)

async def handle_command(update: Update, context: CallbackContext):
    """Handles command-style queries (e.g., '/alpha')"""
    command = update.message.text.strip().lower()
    query = command.lstrip("/")  # Remove the leading '/' to get the symbol
    await get_token_details(update, context, query)

# trending command
async def trending_tokens(update: Update, context: CallbackContext):
    """Fetch and display the top trending tokens"""
    await send_typing(update, context)

    params = {"pageSize": 5, "page": 0, "orderBy": "volumeDaily", "desc": True}
    response = requests.get(TOKEN_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get("data", [])

        if not data:
            await update.message.reply_text("❌ No trending tokens found.")
            return

        message = "🔥 *Trending Tokens (by Volume)*:\n\n"
        for i, token in enumerate(data, 1):
            name = token.get('name', 'Unknown')
            symbol = token.get('symbol', 'Unknown')
            volume = round(token.get('volumeDaily', 0), 2)
            message += f"{i}. *{name}* ({symbol}) - {volume} ℵ\n"

        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Failed to fetch trending tokens.")
        
async def leaderboard(update: Update, context: CallbackContext):
    """Fetch and display the top tokens by market cap"""
    await send_typing(update, context)

    params = {"pageSize": 5, "page": 0, "orderBy": "marketCap", "desc": True}
    response = requests.get(TOKEN_API_URL, params=params)

    if response.status_code == 200:
        data = response.json().get("data", [])

        if not data:
            await update.message.reply_text("❌ No leaderboard data found.")
            return

        message = "🏆 *Top Tokens (by Market Cap)*:\n\n"
        for i, token in enumerate(data, 1):
            name = token.get('name', 'Unknown')
            symbol = token.get('symbol', 'Unknown')
            market_cap = round(token.get('marketCap', 0), 2)
            message += f"{i}. *{name}* ({symbol}) - {market_cap} ℵ\n"

        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Failed to fetch leaderboard data.")

async def help_command(update: Update, context: CallbackContext):
    """Handles the /help command"""
    await send_typing(update, context)  # Show typing action
    
    message = (
        "🤖 *How to Use the Bot:*\n\n"
        "🔍 *Search Tokens:* Send a token symbol, name, or contract address.\n"
        "📈 *Trending Tokens:* Use /trending to see the hottest tokens.\n"
        "🏆 *Leaderboard:* Use /leaderboard to see the top tokens.\n"
        "ℹ️ *More Info:* Visit [MyOnion.fun](https://myonion.fun) for detailed insights."
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")

def main():
    """Start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Correct order of handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))  # Ensure this comes before handle_command
    app.add_handler(CommandHandler("trending", trending_tokens))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    
    # Handles /{symbol} commands (like /alph, /moga)
    app.add_handler(MessageHandler(filters.COMMAND, handle_command))  
    
    # Message handler for plain text queries
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
