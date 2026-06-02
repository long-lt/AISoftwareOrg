"""
tests/test_parallel.py
Kiểm tra Orchestrator chạy song song các dev tasks.
"""

import asyncio
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from core.graph.orchestrator import create_master_workflow

async def main():
    print("🚀 Khởi chạy Master Orchestrator (Parallel Mode)...")
    
    workflow = create_master_workflow()
    
    # Requirement đơn giản để Planner chia làm 2-3 tasks nhỏ
    requirement = "Viết 2 hàm tiện ích: một hàm tính giai thừa (factorial) và một hàm kiểm tra số nguyên tố (is_prime). Mỗi hàm để trong một file riêng."
    
    initial_state = {
        "requirement": requirement,
        "pm_spec": None,
        "plan": None,
        "tasks": [],
        "results": [],
        "error": None,
        "logs": [],
        "max_attempts": 3,
        "use_docker": False,
    }
    
    print("\n--- Đang thực thi workflow ---")
    final_state = await workflow.ainvoke(initial_state)
    
    print("\n--- Kết quả ---")
    if final_state.get("error"):
        print(f"❌ Lỗi: {final_state['error']}")
    else:
        results = final_state.get("results", [])
        print(f"✅ Hoàn thành: {len(results)} tasks")
        for res in results:
            task_id = res.get("task_id")
            status = res.get("test_result")
            print(f"   - Task [{task_id}]: {status}")
            
    # Kiểm tra xem có thực sự chạy song song không (qua logs thời gian nếu cần)
    # Nhưng quan trọng nhất là các task đều kết thúc và được tổng hợp vào state chung.

if __name__ == "__main__":
    asyncio.run(main())
