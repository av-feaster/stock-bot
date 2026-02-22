#!/usr/bin/env python3
"""
Test the switch command locally
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Temporarily enable polling
os.environ["BOT_SCHEDULER_ONLY"] = "0"

from bot import cmd_switch
from unittest.mock import Mock, AsyncMock

async def test_switch():
    print("🧪 Testing /switch command...")
    
    # Mock update and context
    update = Mock()
    update.effective_chat.id = "5932641837"  # Your chat ID
    update.message.reply_text = AsyncMock()
    
    context = Mock()
    context.args = []  # No args = show current mode
    
    # Test showing current mode
    await cmd_switch(update, context)
    print("✅ Current mode display works")
    
    # Test switching to polling
    context.args = ["polling"]
    await cmd_switch(update, context)
    print("✅ Switch to polling works")
    
    # Test switching to scheduler
    context.args = ["scheduler"]
    await cmd_switch(update, context)
    print("✅ Switch to scheduler works")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_switch())
