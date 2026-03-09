import os
import subprocess
import re
import time
import urllib.request
import sys

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    cf_exe = os.path.join(root_dir, "cloudflared.exe")
    env_file = os.path.join(root_dir, ".env")
    
    if not os.path.exists(cf_exe):
        print("Downloading cloudflared.exe (this will take a few seconds)...")
        # Forcing 64-bit because Windows 32-bit execution handlers corrupt the file
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(cf_exe, 'wb') as out_file:
                out_file.write(response.read())
            print("✅ Download complete.")
        except Exception as e:
            print(f"❌ Failed to download cloudflared: {e}")
            return

    print("Starting Cloudflare tunnel...")
    # Kill any stuck existing tunnels
    os.system("taskkill /F /IM cloudflared.exe 2>nul")
    
    # Start cloudflare pointing to localhost:8000 (uvicorn)
    cmd = f'"{cf_exe}" tunnel --url http://127.0.0.1:8000'
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    url_found = None
    url_pattern = re.compile(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)')
    
    print("Waiting for Cloudflare to assign a URL...")
    
    try:
        # Cloudflared outputs its connection info to stderr
        for line in iter(process.stderr.readline, ''):
            match = url_pattern.search(line)
            if match and not url_found:
                url_found = match.group(1)
                print(f"\n=======================================================")
                print(f"✅ TUNNEL IS LIVE: {url_found}")
                print(f"=======================================================\n")
                
                # Update the .env file automatically
                if os.path.exists(env_file):
                    with open(env_file, "r") as f:
                        content = f.read()
                    
                    if "BACKEND_BASE_URL=" in content:
                        content = re.sub(
                            r'BACKEND_BASE_URL=.*', 
                            f'BACKEND_BASE_URL={url_found}', 
                            content
                        )
                    else:
                        content += f"\nBACKEND_BASE_URL={url_found}\n"
                        
                    with open(env_file, "w") as f:
                        f.write(content)
                    print(f"✅ Successfully updated .env file with the new URL!")
                    print(f"⚠️  Restart your Uvicorn backend now so it picks up the new URL.")
                else:
                    print("❌ Could not find .env file to update.")
                
                print("\nKeep this window open! If you close it, email tracking stops.")
                print("Press Ctrl+C to stop the tunnel.")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping tunnel...")
        os.system("taskkill /F /IM cloudflared.exe 2>nul")

if __name__ == "__main__":
    main()
