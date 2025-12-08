from quart import Blueprint, request, jsonify
from app.modules.tempmail.viewmodel import temp_mail_viewmodel
import time
import logging

logger = logging.getLogger("superlive.modules.tempmail")

temp_mail_bp = Blueprint("tempmail", __name__, url_prefix="/temp-mail")

@temp_mail_bp.route('/inbox', methods=['GET'])
async def get_inbox():
    try:
        # Extract parameters
        request_time = request.args.get('requestTime', int(time.time() * 1000))
        lang = request.args.get('lang', 'us')
        
        # Extract cookies from the incoming request to forward them
        cookies = dict(request.cookies)
        
        if not cookies and request.headers.get('Cookie'):
             pass

        upstream_response = await temp_mail_viewmodel.get_inbox(request_time, lang, cookies)
        data = upstream_response.json()
        
        response = jsonify(data)
        
        # Forward cookies from upstream to client
        for name, value in upstream_response.cookies.items():
            response.set_cookie(name, value)
            
        return response, 200
        
    except Exception as e:
        logger.error(f"Get inbox route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@temp_mail_bp.route('/otp', methods=['GET'])
async def get_otp():
    try:
        request_time = request.args.get('requestTime', int(time.time() * 1000))
        lang = request.args.get('lang', 'us')
        cookies = dict(request.cookies)
        
        if not cookies and request.headers.get('Cookie'):
             pass

        upstream_response = await temp_mail_viewmodel.get_inbox(request_time, lang, cookies)
        inbox_data = upstream_response.json()
        otp = temp_mail_viewmodel.extract_otp(inbox_data)
        
        if otp:
            return jsonify({"success": True, "otp": otp}), 200
        else:
            return jsonify({"success": False, "message": "OTP not found in inbox"}), 404
            
    except Exception as e:
        logger.error(f"Get OTP route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@temp_mail_bp.route('/delete-inbox', methods=['DELETE'])
async def delete_inbox():
    try:
        # Extract parameters from args (query string) to match get_otp style
        request_time = request.args.get('requestTime')
        if not request_time:
            request_time = int(time.time() * 1000)
            
        lang = request.args.get('lang', 'us')
        
        # Extract cookies from request headers
        cookies = dict(request.cookies)
        
        if not cookies:
            return jsonify({"error": "Missing cookies"}), 400
            
        upstream_response = await temp_mail_viewmodel.delete_inbox(cookies, request_time, lang)
        
        return jsonify(upstream_response.json()), 200
        
    except Exception as e:
        logger.error(f"Delete inbox route error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
