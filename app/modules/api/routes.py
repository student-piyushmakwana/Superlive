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

async def run_worker(livestream_id, worker_id, proxy_url):
    """
    Individual worker task that performs the gift loop using a specific proxy.
    """
    global GIFT_LOOP_ACTIVE
    logger.info(f"[Worker {worker_id}] Started with proxy {proxy_url}")
    
    # Initialize a dedicated client for this worker
    # We replicate the header structure from SuperliveClient here for the isolated instance
    from app.core.config import config
    
    proxies_config = None
    if proxy_url:
        proxies_config = proxy_url # httpx 'proxy' argument expects string for all protocols or dict. 
                                   # We used 'proxy' arg in client.py which takes string.
                                   # But here we want to use 'proxies' dict if we want to be explicit, 
                                   # or just pass the string to 'proxy' param if we use the same call.
                                   # Let's use the same headers as the main client.

    headers = {
        "accept": "application/json",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/json",
        "device-id": config.DEVICE_ID, # Will be updated per cycle
        "origin": config.ORIGIN,
        "priority": "u=1, i",
        "referer": config.REFERER,
        "sec-ch-ua": '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": config.USER_AGENT
    }

    import httpx
    
    while GIFT_LOOP_ACTIVE:
        # Create a new client session for each identity cycle (Register -> Signup -> Gift -> Logout)
        # This closely mimics the previous flow but isolated per worker
        async with httpx.AsyncClient(
            timeout=config.REQUEST_TIMEOUT,
            follow_redirects=True,
            proxy=proxy_url,
            verify=False,
            headers=headers
        ) as client:
            
            try:
                # --- 1. Register Device ---
                logger.info(f"[Worker {worker_id}] Registering new device")
                from app.core.device import register_device
                
                try:
                    # Register device using the same proxy
                    device_id = await register_device(proxy=proxy_url)
                    # Update this client's device-id header
                    client.headers["device-id"] = device_id
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"[Worker {worker_id}] Device registration failed: {e.response.status_code}")
                    if e.response.status_code == 400:
                        logger.critical(f"[Worker {worker_id}] Stopping due to 400 Bad Request")
                        # If one worker fails with 400, strictly we should probably stop all? 
                        # Or just this one? The user said "imedialy stop the loops".
                        # So we kill the global flag.
                        GIFT_LOOP_ACTIVE = False
                        break
                    await asyncio.sleep(5)
                    continue
                except Exception as e:
                    logger.error(f"[Worker {worker_id}] Device reg error: {e}")
                    await asyncio.sleep(5)
                    continue

                # --- 2. Temp Mail & Signup ---
                logger.info(f"[Worker {worker_id}] Fetching Temp Mail")
                request_time = int(time.time() * 1000)
                tm_cookies = {}
                token = None
                
                try:
                    inbox_resp = await temp_mail_viewmodel.get_inbox(request_time)
                    inbox_data = inbox_resp.json()
                    email = inbox_data.get("data", {}).get("name")
                    tm_cookies = dict(inbox_resp.cookies)
                    
                    if not email:
                        raise Exception("No email found")
                    
                    # Verify Code Flow
                    # Pass 'client' to use this worker's session/proxy
                    send_resp = await api_viewmodel.send_verification_code(email, client=client)
                    email_verification_id = send_resp.get("email_verification_id") or send_resp.get("data", {}).get("email_verification_id")
                    
                    if not email_verification_id:
                        raise Exception("No verification ID")
                        
                    # Poll OTP
                    otp = None
                    poll_start = time.time()
                    while time.time() - poll_start < 40:
                        try:
                            # TempMail viewmodel creates its own client, which is fine (no proxy needed usually)
                            # But if needed we can add proxy support there too. 
                            # For now assumption: tempmail doesn't need the rotate proxy.
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
                        
                    logger.info(f"[Worker {worker_id}] Signup success")
                    
                except Exception as e:
                    logger.error(f"[Worker {worker_id}] Signup failed: {e}")
                    await asyncio.sleep(2)
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
                        logger.info(f"[Worker {worker_id}] Gift Sent (200 OK)")
                        await asyncio.sleep(0.25) 
                    except SuperliveError as se:
                         if se.status_code in [400, 401]:
                             logger.warning(f"[Worker {worker_id}] Gift 400/401. cleaning up.")
                             break 
                         if se.status_code == 403:
                             break
                         break # Break on other errors too to be safe
                    except Exception as e:
                        logger.error(f"[Worker {worker_id}] Gift error: {e}")
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
                    
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Main loop error: {e}")
                await asyncio.sleep(5)

    logger.info(f"[Worker {worker_id}] Stopped")

async def run_auto_gift_loop(livestream_id, worker_count=1):
    """
    Orchestrator that spawns N workers.
    """
    global GIFT_LOOP_ACTIVE
    from app.core.config import config
    
    tasks = []
    available_proxies = config.PROXIES if hasattr(config, 'PROXIES') else []
    
    # Ensure we don't exceed max workers or proxy count if valid
    # User said "ten proxy means 10 worker... maximum worker 10"
    count = min(worker_count, 10)
    if not available_proxies:
        logger.warning("No proxies found! Workers will run without proxy (or share IP).")
        # Fallback if no proxies? 
        # For now let's just run them.
    
    logger.info(f"Spawning {count} workers for stream {livestream_id}")
    
    for i in range(count):
        # Assign proxy round-robin or just index based since count <= len(proxies) hopefully
        proxy = None
        if available_proxies:
            proxy = available_proxies[i % len(available_proxies)]
            
        task = asyncio.create_task(run_worker(livestream_id, i+1, proxy))
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
            worker_count = req_data.get('worker', 1)
            GIFT_LOOP_ACTIVE = True
            
            # Start background task
            # In Quart/Asyncio, we can use create_task
            CURRENT_TASK = asyncio.create_task(run_auto_gift_loop(livestream_id, worker_count))
            
            return jsonify({"message": f"Auto gift loop started with {worker_count} workers"}), 200
            
        return jsonify({"error": "Invalid code. Use 10 to start, 12 to stop."}), 400
        
    except Exception as e:
        logger.error(f"Auto gift route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500