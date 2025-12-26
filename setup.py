#!/usr/bin/env python3
"""
Setup script for AI Girlfriend Voice Chat with async file operations
"""

import os
import sys
import subprocess  # Used safely: list format, shell=False, static arguments
import asyncio
import aiofiles

async def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

async def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        # Use subprocess for pip installation
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            print("✅ Requirements installed successfully")
            # Also try to install with subprocess fallback if needed
            if b"error" in stdout.lower() or b"failed" in stdout.lower():
                print("⚠️  Trying alternative installation method...")
                result = subprocess.run([
                    sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
                ], capture_output=True, text=True, shell=False)
                if result.returncode != 0:
                    print(f"❌ Alternative installation failed: {result.stderr}")
                    return False
            return True
        else:
            print(f"❌ Failed to install requirements: {stderr.decode()}")
            return False
    except Exception as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

async def setup_env_file():
    """Setup environment file with async I/O"""
    if not os.path.exists('.env'):
        print("📝 Creating .env file...")
        try:
            async with aiofiles.open('.env.example', 'r') as example:
                content = await example.read()
            
            async with aiofiles.open('.env', 'w') as env:
                await env.write(content)
            
            print("✅ .env file created from template")
            print("⚠️  Please edit .env with your API keys")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
            return False
    else:
        print("✅ .env file already exists")
    return True

async def check_audio_system():
    """Check if audio system is available"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        
        # Check for input devices
        input_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(info['name'])
        
        # Check for output devices  
        output_devices = []
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                output_devices.append(info['name'])
        
        p.terminate()
        
        if input_devices and output_devices:
            print("✅ Audio system ready")
            print(f"🎤 Input devices found: {len(input_devices)}")
            print(f"🔊 Output devices found: {len(output_devices)}")
            return True
        else:
            print("⚠️  Audio devices not found - check your audio setup")
            return False
            
    except Exception as e:
        print(f"⚠️  Audio system check failed: {e}")
        return False

async def create_default_config():
    """Create default configuration file"""
    try:
        from async_config_loader import AsyncConfigLoader
        
        config_loader = AsyncConfigLoader()
        await config_loader.create_default_config()
        print("✅ Default configuration file created")
        return True
    except Exception as e:
        print(f"⚠️  Could not create config file: {e}")
        return False

async def run_health_check():
    """Run a comprehensive health check"""
    print("\n🔍 Running health check...")
    
    try:
        from modules import APIKeyManager, AsyncConfigLoader
        
        # Check API key manager
        key_manager = APIKeyManager()
        await key_manager.load_keys()
        key_stats = await key_manager.get_key_stats()
        
        print(f"🔑 API Keys: {key_stats['total_keys']} total, {key_stats['active_keys']} active")
        
        # Check config loader
        config_loader = AsyncConfigLoader()
        config_status = await config_loader.get_config_status()
        
        print(f"⚙️  Config file: {'✅' if config_status['config_file_exists'] else '❌'}")
        print(f"🔐 Environment keys: {'✅' if config_status['environment_variables']['GEMINI_API_KEY'] else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Health check failed: {e}")
        return False

async def main():
    """Main setup function with async operations"""
    print("🔥 Setting up AI Girlfriend Voice Chat...")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    if not await check_python_version():
        success = False
    
    # Install requirements
    if success and not await install_requirements():
        success = False
    
    # Setup environment file
    if success and not await setup_env_file():
        success = False
    
    # Create default config
    if success:
        await create_default_config()
    
    # Check audio system
    if success:
        await check_audio_system()
    
    # Run health check
    if success:
        await run_health_check()
    
    print("=" * 50)
    
    if success:
        print("✅ Setup completed successfully!")
        print("\n📋 Next steps:")
        print("1. Edit .env with your API keys")
        print("   - Get Gemini API key: https://ai.google.dev/")
        print("   - Get Picovoice key: https://console.picovoice.ai/ (optional)")
        print("2. Run: python main.py")
        print("\n💋 Your AI girlfriend will be ready to chat!")
    else:
        print("❌ Setup failed - please check the errors above")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled!")
        sys.exit(1)