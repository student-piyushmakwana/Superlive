from quart import Blueprint, request, jsonify
from app.modules.api.viewmodel import api_viewmodel, SuperliveError
from app.modules.tempmail.viewmodel import temp_mail_viewmodel

import logging
import asyncio
import time

logger = logging.getLogger("superlive.modules.api")

api_bp = Blueprint("api", __name__)

# Global state to control the loop
GIFT_LOOP_ACTIVE = False
CURRENT_TASK = None

async def run_worker(livestream_id, worker_index, total_workers, proxy_enabled=True):
    """
    Individual worker task that performs the gift loop using dynamic proxy rotation.
    Proxy Strategy: (worker_index + attempt * total_workers) % len(proxies)
    This ensures "First N workers use First N proxies. If they retry, they use Next N proxies".
    """
    global GIFT_LOOP_ACTIVE
    from app.core.config import config
    
    proxies = config.PROXIES or []
    attempt = 0
    worker_display_id = worker_index + 1
    
    worker_display_id = worker_index + 1
    
    current_domain_idx = 0
    consecutive_errors = 0
    MAX_RETRIES = 3 # "Maximum sathe worker 3 attempt to marne hi chahiye"

    logger.info(f"➡️ [Worker {worker_display_id}] Started")

    while GIFT_LOOP_ACTIVE:
        if consecutive_errors >= MAX_RETRIES:
            current_domain_idx = (current_domain_idx + 1) % len(config.DOMAINS)
            consecutive_errors = 0
            logger.warning(f"🔄 [Worker {worker_display_id}] Max retries reached. Switching to domain: {config.DOMAINS[current_domain_idx]['origin']}")
            # break # Don't break, just continue with new domain

        # Determine Proxy for this cycle/attempt
        current_proxy = None
        
        if proxy_enabled and proxies:
            # Calculate index based on the "Next N" strategy
            # worker_index is 0-based unique slot for this worker
            proxy_idx = (worker_index + (attempt * total_workers)) % len(proxies)
            current_proxy = proxies[proxy_idx]
            
        # logger.info(f"[Worker {worker_display_id}] Starting Cycle {attempt+1} with Proxy: {current_proxy}")
        
        # Prepare headers (standard)
        domain_config = config.DOMAINS[current_domain_idx]
        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            # device-id updated later
            "origin": domain_config["origin"],
            "priority": "u=1, i",
            "referer": domain_config["referer"],
            "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": config.USER_AGENT
        }

        import httpx
        
        # Create a new client session for this identity cycle
        async with httpx.AsyncClient(
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            proxy=current_proxy, # Dynamic proxy
            verify=False,
            headers=headers
        ) as client:
            
            try:
                # --- 1. Register Device ---
                # logger.info(f"[Worker {worker_display_id}] Registering new device")
                from app.core.device import register_device
                
                try:
                    # Register device using the same proxy
                    device_id = await register_device(proxy=current_proxy)
                    client.headers["device-id"] = device_id
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 400:
                        logger.critical(f"🛑 [Worker {worker_display_id}] Critical 400 Device Error. Stopping this worker.")
                        break
                    
                    consecutive_errors += 1
                    logger.warning(f"⚠️ [Worker {worker_display_id}] Device Reg Failed ({e.response.status_code}). Retrying ({consecutive_errors}/{MAX_RETRIES})...")
                    await asyncio.sleep(2)
                    attempt += 1 
                    continue
                except Exception as e:
                    consecutive_errors += 1
                    logger.warning(f"⚠️ [Worker {worker_display_id}] Device Reg Error: {e}. Retrying ({consecutive_errors}/{MAX_RETRIES})...")
                    await asyncio.sleep(2)
                    attempt += 1
                    continue

                # --- 2. Temp Mail & Signup ---
                # --- 2. Temp Mail & Signup ---
                request_time = int(time.time() * 1000)
                tm_cookies = {}
                token = None
                
                # --- 2. Temp Mail & Signup ---
                request_time = int(time.time() * 1000)
                tm_cookies = {}
                token = None
                
                try:
                    # Default TempMail.so Logic
                    inbox_resp = await temp_mail_viewmodel.get_inbox(request_time)
                    inbox_data = inbox_resp.json()
                    email = inbox_data.get("data", {}).get("name")
                    tm_cookies = dict(inbox_resp.cookies)
                    
                    if not email:
                        raise Exception("No email found")
                    
                    # Verify Code Flow
                    try:
                        send_resp = await api_viewmodel.send_verification_code(email, client=client)
                    except SuperliveError as se:
                         error_data = se.details.get("error", {}) if se.details else {}
                         if isinstance(error_data, dict) and error_data.get("code") == 12:
                             logger.warning(f"⚠️ [Worker {worker_display_id}] Verification Limit Reached (Code 12). Sleeping 10s and retrying...")
                             await asyncio.sleep(10)
                             attempt += 1 # Rotate proxy
                             continue # Retry loop
                         raise se

                    email_verification_id = send_resp.get("email_verification_id") or send_resp.get("data", {}).get("email_verification_id")
                    
                    if not email_verification_id:
                        raise Exception("No verification ID")
                        
                    # Poll OTP
                    otp = None
                    poll_start = time.time()
                    while time.time() - poll_start < 40:
                        try:
                            poll_resp = await temp_mail_viewmodel.get_inbox(int(time.time() * 1000), "us", tm_cookies)
                            otp = temp_mail_viewmodel.extract_otp(poll_resp.json())
                            if otp:
                                break
                        except:
                            pass
                        await asyncio.sleep(2)
                        if not GIFT_LOOP_ACTIVE: break
                    
                    if not otp:
                         raise Exception("OTP Timeout")
                         
                    await api_viewmodel.verify_email(email_verification_id, otp, client=client)
                    signup_res = await api_viewmodel.complete_signup(email, email, client=client)
                    token = signup_res.get("data", {}).get("token") or signup_res.get("token")
                    
                    if not token:
                        raise Exception("No token")
                        
                    logger.info(f"✅ [Worker {worker_display_id}] Signup Success ({email})")
                    consecutive_errors = 0 # Reset errors on success
                    
                    # Update Profile Logic
                    try:
                        await api_viewmodel.update_profile(token, client=client)
                        logger.info(f"👤 [Worker {worker_display_id}] Profile Updated")
                        await asyncio.sleep(0.5) # Short pause after update
                    except Exception as e:
                        logger.warning(f"⚠️ [Worker {worker_display_id}] Profile Update Failed: {e}")
                        # Continue anyway
                    
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"❌ [Worker {worker_display_id}] Signup Failed: {str(e)[:50]}... ({consecutive_errors}/{MAX_RETRIES})")
                    await asyncio.sleep(1)
                    attempt += 1 # Rotate proxy on failure
                    continue

                # --- 3. Inner Gift Loop ---
                gift_payload = {
                     "token": token,
                     "livestream_id": livestream_id,
                     "gift_id": 5141,
                     "gift_context": 1
                }
                
                while GIFT_LOOP_ACTIVE:
                    try:
                        await api_viewmodel.send_gift(token, gift_payload, client=client)
                        logger.info(f"🎁 [Worker {worker_display_id}] Gift Sent")
                        await asyncio.sleep(1.0) # Increased delay to avoid detection
                    except SuperliveError as se:
                         if se.status_code in [400, 401]:
                             logger.warning(f"⚠️ [Worker {worker_display_id}] Gift 400/401. Restarting cycle.")
                             break 
                         if se.status_code == 403:
                             break
                         break 
                    except Exception as e:
                        logger.error(f"⚠️ [Worker {worker_display_id}] Gift Error: {e}")
                        break
                
                # --- 4. Cleanup ---
                try:
                    await api_viewmodel.logout(token, client=client)
                except:
                     pass
                try:
                    await temp_mail_viewmodel.delete_inbox(tm_cookies, int(time.time()*1000))
                except:
                    pass
                
                # Cycle finished successfully (or broke from inner loop)
                attempt += 1

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"❌ [Worker {worker_display_id}] Main Loop Error: {e}. ({consecutive_errors}/{MAX_RETRIES})")
                await asyncio.sleep(2)
                attempt += 1

    logger.info(f"🛑 [Worker {worker_display_id}] Stopped safely")

async def run_auto_gift_loop(livestream_id, worker_count=1, proxy_enabled=True):
    """
    Orchestrator that spawns N workers.
    """
    global GIFT_LOOP_ACTIVE
    from app.core.config import config
    
    tasks = []
    
    proxies = config.PROXIES or []
    if proxy_enabled and not proxies:
        logger.warning("No proxies found! Workers might get rate limited.")

    # Max workers = 100 or unlimited? User has 100+ proxies.
    # Let's cap at 50 to be safe? Or just trust user input.
    # User said "maximux worker 10" previously, but now gave 100 proxies.
    # Let's respect user input but maybe cap sanity at 30?
    count = min(worker_count, 100) 
    
    logger.info(f"Spawning {count} workers (Pool: {len(proxies)} proxies, Proxy Enabled: {proxy_enabled})")
    
    for i in range(count):
        # Pass 0-based index and total count for rotation logic
        task = asyncio.create_task(run_worker(livestream_id, i, count, proxy_enabled))
        tasks.append(task)
        
    await asyncio.gather(*tasks)



@api_bp.route('/login', methods=['POST'])
async def login():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400
            
        result = await api_viewmodel.login(email, password)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Login route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/profile', methods=['POST'])
async def profile():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.get_profile(token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Profile route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/update-profile', methods=['POST'])
async def update_profile():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.update_profile(token)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Update profile route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/send-gift', methods=['POST'])
async def send_gift():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        if not token:
            return jsonify({"error": "Missing token"}), 400
            
        result = await api_viewmodel.send_gift(token, data)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Send gift route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/signup', methods=['POST'])
async def signup():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        # Extract cookies from request headers
        cookies = dict(request.cookies)
        
        if not email or not password or not cookies:
            return jsonify({"error": "Missing email, password, or cookies"}), 400
            
        # 1. Send Verification Code
        logger.info(f"Step 1: Sending verification code to {email}")
        send_resp = await api_viewmodel.send_verification_code(email)
        
        # Extract email_verification_id from response
        # Try direct access or inside 'data'
        email_verification_id = send_resp.get("email_verification_id") or send_resp.get("data", {}).get("email_verification_id")
        
        if not email_verification_id:
            logger.error(f"Failed to get email_verification_id. Response: {send_resp}")
            return jsonify({"error": "Failed to get verification ID"}), 500
            
        logger.info(f"Verification ID: {email_verification_id}")
        
        # 2. Poll for OTP
        import asyncio
        import time
        logger.info("Step 2: Polling for OTP...")
        otp = None
        start_time = time.time()
        timeout = 30 # seconds
        
        while time.time() - start_time < timeout:
            request_time = int(time.time() * 1000)
            try:
                inbox_resp = await temp_mail_viewmodel.get_inbox(request_time, "us", cookies)
                inbox_data = inbox_resp.json()
                otp = temp_mail_viewmodel.extract_otp(inbox_data)
                
                if otp:
                    logger.info(f"Found OTP: {otp}")
                    break
            except Exception as w:
                 logger.warning(f"Error checking inbox: {w}")
                 
            await asyncio.sleep(3) # Wait 3 seconds before next poll
            
        if not otp:
            return jsonify({"error": "OTP timeout", "details": "Could not retrieve OTP from tempmail within timeout"}), 408
            
        # 3. Verify Email
        logger.info(f"Step 3: Verifying email with OTP {otp}")
        await api_viewmodel.verify_email(email_verification_id, otp)
        
        # 4. Complete Signup
        logger.info("Step 4: Completing signup")
        result = await api_viewmodel.complete_signup(email, password)
        
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Signup route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/livestream', methods=['POST'])
async def livestream():
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        token = data.get('token')
        livestream_id = data.get('livestream_id')
        
        if not token or not livestream_id:
            return jsonify({"error": "Missing token or livestream_id"}), 400
            
        result = await api_viewmodel.get_livestream(token, livestream_id)
        return jsonify(result), 200
        
    except SuperliveError as e:
        return jsonify({"error": e.details or e.message}), e.status_code
    except Exception as e:
        logger.error(f"Livestream route error: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@api_bp.route('/auto/gift', methods=['POST'])
async def auto_gift():
    global GIFT_LOOP_ACTIVE, CURRENT_TASK
    
    try:
        req_data = await request.get_json()
        if not req_data:
            return jsonify({"error": "Missing JSON body"}), 400
            
        code = req_data.get('code')
        
        if code == 12:
            logger.info("Received Stop Signal (Code 12)")
            GIFT_LOOP_ACTIVE = False
            return jsonify({"message": "Stopping auto gift loop received"}), 200

        if code == 10:
            if GIFT_LOOP_ACTIVE:
                return jsonify({"message": "Loop is already running"}), 200
                
            livestream_id = req_data.get('livestream_id') or 127902815
            worker_count = req_data.get('worker', 2)
            proxy_on = req_data.get('proxy_on', True)
            GIFT_LOOP_ACTIVE = True
            
            # Start background task
            # In Quart/Asyncio, we can use create_task
            CURRENT_TASK = asyncio.create_task(run_auto_gift_loop(livestream_id, worker_count, proxy_on))
            
            return jsonify({"message": f"Auto gift loop started with {worker_count} workers (Proxy: {proxy_on})"}), 200
            
        return jsonify({"error": "Invalid code. Use 10 to start, 12 to stop."}), 400
        
    except Exception as e:
        logger.error(f"Auto gift route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

