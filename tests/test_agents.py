"""
agents/test_agents.py
Test script cho Dev Agent và QA Agent.
"""

import sys
import os
from pathlib import Path

# Đảm bảo có thể import các package trong thư mục hiện tại
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import asyncio
import pytest
from agents import DevAgent, QAAgent, AgentTask


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Live LLM agent tests are opt-in. Set RUN_LIVE_LLM_TESTS=1 to run.",
)


async def test_dev_agent():
    print("=" * 50)
    print("TEST: Dev Agent")
    print("=" * 50)
    
    agent = DevAgent()
    task = AgentTask(
        id="dev-test-1",
        description="Viết một hàm Python `add(a, b)` trả về tổng của a và b."
    )
    
    print("⏳ Đang gọi Dev Agent...")
    result = await agent.run(task)
    
    if result.success:
        print("✅ Dev Agent trả về code thành công:")
        print("-" * 30)
        print(result.output)
        print("-" * 30)
    else:
        print("❌ Dev Agent thất bại:")
        print(result.reason)
        
    return result

async def run_qa_agent(code_to_test: str):
    print("\n" + "=" * 50)
    print("TEST: QA Agent (Local Sandbox)")
    print("=" * 50)
    
    agent = QAAgent(use_docker=False)
    task = AgentTask(
        id="qa-test-1",
        description="Viết một hàm Python `add(a, b)` trả về tổng của a và b.",
        context=code_to_test
    )
    
    print("⏳ Đang gọi QA Agent để sinh test và chạy...")
    result = await agent.run(task)
    
    if result.success:
        print("✅ QA Agent báo cáo code PASS!")
        print("Reason:\n", result.reason)
    else:
        print("❌ QA Agent báo cáo code FAIL!")
        print("Output:\n", result.output)
        print("Reason:\n", result.reason)

async def main():
    print("🔬 Running Task 3 — Agents Tests\n")
    
    dev_result = await test_dev_agent()
    if dev_result.success:
        # Nếu Dev Agent thành công, truyền code đó qua QA Agent
        await run_qa_agent(dev_result.output)
    else:
        print("⚠️ Bỏ qua test QA Agent vì Dev Agent thất bại. Cần kiểm tra API Key của OpenAI/DeepSeek.")

if __name__ == "__main__":
    asyncio.run(main())
