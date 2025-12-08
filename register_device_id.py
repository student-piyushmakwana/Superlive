import asyncio
import os
from app.core.device import register_device

async def main():
    try:
        device_id = await register_device()
        print(f"\nSUCCESS: New Device ID Registered: {device_id}")
        
        env_file = ".env"
        
        # Check if .env exists, if so read it to see if DEVICE_ID is already there
        lines = []
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                lines = f.readlines()
        
        # simple check/update
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("DEVICE_ID="):
                if not found:
                    new_lines.append(f"DEVICE_ID={device_id}\n")
                    found = True
                # Skip duplicate DEVICE_ID lines
            else:
                new_lines.append(line)
        
        if not found:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            new_lines.append(f"DEVICE_ID={device_id}\n")
            
        with open(env_file, "w") as f:
            f.writelines(new_lines)
            
        print(f"Updated {env_file} with DEVICE_ID={device_id}")
        
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
