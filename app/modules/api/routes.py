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

async def run_auto_gift_loop(livestream_id):
    """
    Background task that loops:
    1. Register Device
    2. Get Temp Mail & Signup
    3. Inner Loop: Send Gift until 400/401
    4. Cleanup: Logout & Delete Inbox
    """
    global GIFT_LOOP_ACTIVE
    
    logger.info(f"Starting Auto Gift Loop for livestream {livestream_id}")
    
    while GIFT_LOOP_ACTIVE:
        try:
            # --- 0. Configure Proxy ---
            import random
            from app.core.config import config
            
            selected_proxy = None
            if hasattr(config, 'PROXIES') and config.PROXIES:
                selected_proxy = random.choice(config.PROXIES)
                
            from app.core.client import SuperliveClient
            SuperliveClient.init_client(proxy=selected_proxy)
            
            # --- 1. Register Device ---
            logger.info(">>> [Loop Start] Registering new device")
            from app.core.device import register_device
            import httpx
            
            try:
                device_id = await register_device(proxy=selected_proxy)
                SuperliveClient.update_device_id(device_id)
            except httpx.HTTPStatusError as e:
                logger.error(f"Device registration failed with status {e.response.status_code}")
                if e.response.status_code == 400:
                    logger.critical("Stopping Auto Gift Loop due to 400 Bad Request on registration")
                    GIFT_LOOP_ACTIVE = False
                    break
                await asyncio.sleep(5)
                continue
            except Exception as e:
                logger.error(f"Device registration failed: {e}")
                await asyncio.sleep(5)
                continue

            # --- 2. Temp Mail & Signup ---
            logger.info(">>> Fetching Temp Mail")
            request_time = int(time.time() * 1000)
            token = None
            tm_cookies = {}
            
            try:
                inbox_resp = await temp_mail_viewmodel.get_inbox(request_time)
                inbox_data = inbox_resp.json()
                email = inbox_data.get("data", {}).get("name")
                tm_cookies = dict(inbox_resp.cookies)
                
                if not email:
                    raise Exception("No email found in tempmail")
                    
                logger.info(f"Using email: {email}")
                
                # Verify Code Flow
                send_resp = await api_viewmodel.send_verification_code(email)
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
                    await asyncio.sleep(3)
                    if not GIFT_LOOP_ACTIVE: break 
                
                if not otp:
                    raise Exception("OTP Timeout")
                    
                await api_viewmodel.verify_email(email_verification_id, otp)
                signup_res = await api_viewmodel.complete_signup(email, email)
                token = signup_res.get("data", {}).get("token") or signup_res.get("token")
                
                if not token:
                    raise Exception("No token after signup")
                    
                logger.info(f"Signup success: {token[:10]}...")
                
            except Exception as e:
                logger.error(f"Signup sequence failed: {e}")
                # If we have an inbox but failed signup, try to clean it?
                # But better just retry outer loop
                await asyncio.sleep(2)
                continue

            # --- 3. Inner Loop: Send Gift ---
            logger.info(">>> Starting Gift Loop")
            gift_payload = {
                "token": token,
                "livestream_id": livestream_id,
                "gift_id": 5141,
                "gift_context": 1
            }
            
            while GIFT_LOOP_ACTIVE:
                try:
                    await api_viewmodel.send_gift(token, gift_payload)
                    logger.info("Gift Sent (200 OK)")
                    await asyncio.sleep(1) # Small delay to avoid hammering
                except SuperliveError as se:
                    logger.warning(f"Gift failed with {se.status_code}. Stopping inner loop.")
                    if se.status_code in [400, 401]:
                        break # Stop inner loop, proceed to cleanup
                    if se.status_code == 403:
                         break # Also break on forbidden
                    # For other errors (500 etc), maybe retry? 
                    # User said "while you not getting 400 or 401". So keep trying if 500?
                    # Let's break to be safe and recycle.
                    break
                except Exception as e:
                    logger.error(f"Gift error: {e}")
                    break
            
            # --- 4. Cleanup ---
            logger.info(">>> Cleanup: Logout and Delete Inbox")
            try:
                await api_viewmodel.logout(token)
                logger.info("Logged out")
            except Exception as e:
                logger.warning(f"Logout failed: {e}")
                
            try:
                await temp_mail_viewmodel.delete_inbox(tm_cookies, int(time.time() * 1000))
                logger.info("Inbox deleted")
            except Exception as e:
                logger.warning(f"Delete inbox failed: {e}")
                
        except Exception as e:
            logger.error(f"Outer loop error: {e}")
            await asyncio.sleep(5)

    logger.info("Auto Gift Loop Stopped")


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
            GIFT_LOOP_ACTIVE = True
            
            # Start background task
            # In Quart/Asyncio, we can use create_task
            CURRENT_TASK = asyncio.create_task(run_auto_gift_loop(livestream_id))
            
            return jsonify({"message": "Auto gift loop started in background"}), 200
            
        return jsonify({"error": "Invalid code. Use 10 to start, 12 to stop."}), 400
        
    except Exception as e:
        logger.error(f"Auto gift route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500