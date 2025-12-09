import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock
from app.modules.api.viewmodel import api_viewmodel, SuperliveError, httpx

class TestApiFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_on_network_error(self):
        # Mock client
        client = AsyncMock()
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"success": True}
        
        # Side effect: Raise NetworkError first, then return success_response
        client.request.side_effect = [
            httpx.NetworkError("Connection refused"),
            success_response
        ]
        
        print("\nTesting NetworkError fallback...")
        result = await api_viewmodel._make_request("POST", "/test", client)
        
        self.assertEqual(result, {"success": True})
        self.assertEqual(client.request.call_count, 2)
        print("✅ NetworkError fallback worked")
        
        args1, _ = client.request.call_args_list[0]
        self.assertIn("api.spl-web-live.link", args1[1])
        
        args2, _ = client.request.call_args_list[1]
        self.assertIn("api.spl-web.link", args2[1])

    async def test_fallback_on_503(self):
        client = AsyncMock()
        
        fail_response = MagicMock()
        fail_response.status_code = 503
        err = httpx.HTTPStatusError("Service Unavailable", request=None, response=fail_response)
        fail_response.raise_for_status.side_effect = err
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"success": True}
        
        client.request.side_effect = [fail_response, success_response]
        
        print("\nTesting 503 fallback...")
        result = await api_viewmodel._make_request("POST", "/test", client)
        
        self.assertEqual(result, {"success": True})
        self.assertEqual(client.request.call_count, 2)
        print("✅ 503 fallback worked")

    async def test_no_fallback_on_404(self):
        client = AsyncMock()
        
        fail_response = MagicMock()
        fail_response.status_code = 404
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError("Not Found", request=None, response=fail_response)
        fail_response.json.return_value = {"error": "Not Found"}
        fail_response.text = '{"error": "Not Found"}'
        
        client.request.return_value = fail_response
        
        print("\nTesting 404 NO fallback...")
        with self.assertRaises(SuperliveError) as cm:
            await api_viewmodel._make_request("POST", "/test", client)
            
        self.assertEqual(client.request.call_count, 1)
        self.assertEqual(cm.exception.status_code, 404)
        print("✅ 404 correctly raised error without fallback")

if __name__ == '__main__':
    unittest.main()
