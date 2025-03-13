import requests
import io
import os

from config.settings import BOT_TOKEN, TOKEN_API_URL, ALPH_PRICE_API, DEFAULT_SUPPLY  # Import from config.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

async def get_alph_price():
    """Fetch real-time ALPH to USD conversion rate"""
    try:
        response = requests.get(ALPH_PRICE_API)
        data = response.json()
        return float(data["alephium"]["usd"])  # Extract ALPH price in USD
    except:
        return None  # Return None if API fails

async def start(update: Update, context: CallbackContext):
    """Handles the /start command"""
    await update.message.reply_text("Send me a token symbol, name, or contract address, and I'll fetch its details for you!")

async def get_token_details(update: Update, context: CallbackContext, query: str):
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
            f"🔹 *{name}* ({symbol})\n"
            f"📜 Contract Address: `{contract}`\n"
            f"💰 Price: *{price} ℵ* (~${price_usd})\n"
            f"📊 Market Cap: *{market_cap_alph} ℵ* (~${market_cap_usd})\n"
            f"📈 Daily Volume: *{volume_alph} ℵ* (~${volume_usd})\n"
            f"📌 Status: *{status}*\n"
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

def main():
    """Start the bot"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers for /start and /{symbol}
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.COMMAND, handle_command))  # Handles /alpha, /moga, etc.
    
    # Message handler for plain text queries
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
