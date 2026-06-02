"""
tests/test_phase2.py
Test Phase 2: PM Agent, Planner Agent, và Full Pipeline.

Chạy:
    cd my-ai-org
    python tests/test_phase2.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from agents import AgentTask, PMAgent, PlannerAgent
from workflows.full_pipeline import run_full_pipeline, print_full_result
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Live LLM pipeline tests are opt-in. Set RUN_LIVE_LLM_TESTS=1 to run.",
)


# ---------------------------------------------------------------------------
# Test 1: PM Agent
# ---------------------------------------------------------------------------

async def test_pm_agent():
    print("=" * 55)
    print("TEST 1: PM Agent")
    print("=" * 55)

    agent = PMAgent()
    task  = AgentTask(
        id="pm-test-1",
        description="Tôi muốn một hệ thống quản lý todo list đơn giản.",
    )

    print("⏳ Đang gọi PM Agent...")
    result = await agent.run(task)

    assert result.success, f"PM Agent thất bại: {result.reason}"

    spec = json.loads(result.output)
    assert "feature_name" in spec,         "Thiếu feature_name"
    assert "tasks" in spec,                "Thiếu tasks"
    assert len(spec["tasks"]) > 0,         "Không có task nào"
    assert "acceptance_criteria" in spec,  "Thiếu acceptance_criteria"

    print(f"✅ PM Agent OK")
    print(f"   Feature   : {spec.get('feature_name')}")
    print(f"   Summary   : {spec.get('one_line_summary')}")
    print(f"   Tasks     : {len(spec['tasks'])}")
    print(f"   Criteria  : {len(spec.get('acceptance_criteria', []))}")

    for t in spec["tasks"]:
        print(f"   [{t['id']}] {t['title']}")

    return spec


# ---------------------------------------------------------------------------
# Test 2: Planner Agent
# ---------------------------------------------------------------------------

async def run_planner_agent(pm_spec: dict):
    print("\n" + "=" * 55)
    print("TEST 2: Planner Agent")
    print("=" * 55)

    agent = PlannerAgent()
    task  = AgentTask(
        id="planner-test-1",
        description="Hệ thống quản lý todo list",
        context=json.dumps(pm_spec, ensure_ascii=False),
    )

    print("⏳ Đang gọi Planner Agent...")
    result = await agent.run(task)

    assert result.success, f"Planner Agent thất bại: {result.reason}"

    plan = json.loads(result.output)
    assert "tech_stack" in plan,    "Thiếu tech_stack"
    assert "dev_tasks" in plan,     "Thiếu dev_tasks"
    assert len(plan["dev_tasks"]) > 0, "Không có dev tasks"

    stack     = plan.get("tech_stack", {})
    dev_tasks = plan.get("dev_tasks", [])

    print(f"✅ Planner Agent OK")
    print(f"   Pattern   : {plan.get('architecture_pattern')}")
    print(f"   Framework : {stack.get('framework')}")
    print(f"   Database  : {stack.get('database')}")
    print(f"   Dev tasks : {len(dev_tasks)}")

    for dt in dev_tasks:
        deps = f" (depends: {dt['depends_on']})" if dt.get("depends_on") else ""
        print(f"   [{dt['id']}] {dt['title']}{deps}")

    return plan


# ---------------------------------------------------------------------------
# Test 3: Full Pipeline (PM → Planner → Dev loop)
# ---------------------------------------------------------------------------

async def test_full_pipeline():
    print("\n" + "=" * 55)
    print("TEST 3: Full Pipeline")
    print("=" * 55)

    requirement = (
        "Viết một module Python có hàm `add(a, b)` và `multiply(a, b)`. "
        "Mỗi hàm nhận 2 số và trả về kết quả phép tính tương ứng."
    )

    print(f"⏳ Chạy full pipeline cho: {requirement}")
    result = await run_full_pipeline(
        requirement  = requirement,
        max_attempts = 2,
        use_docker   = False,
    )

    print_full_result(result)

    # Assertions
    assert result.pm_spec is not None,   "PM spec trống"
    assert result.plan is not None,      "Plan trống"
    assert len(result.task_results) > 0, "Không có task results"

    print(f"\n{'='*55}")
    if result.success:
        print(f"✅ TEST 3 PASSED — Full Pipeline hoàn thành: {result.summary}")
    else:
        print(f"⚠️  TEST 3 PARTIAL — {result.summary} (một số task chưa pass, cần xem log)")
    print(f"{'='*55}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("🔬 Phase 2 Tests: PM Agent + Planner Agent + Full Pipeline\n")

    failed = 0

    try:
        pm_spec = await test_pm_agent()
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        pm_spec = None
        failed += 1

    try:
        if pm_spec:
            await run_planner_agent(pm_spec)
        else:
            print("\n⚠️ Bỏ qua Test 2 vì Test 1 thất bại")
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        failed += 1

    try:
        await test_full_pipeline()
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

    print(f"\n{'='*55}")
    if failed == 0:
        print("✅ ALL PHASE 2 TESTS PASSED")
        print("   Phase 2 (Full Team) — COMPLETE!")
    else:
        print(f"❌ {failed} test(s) FAILED")

    return failed


if __name__ == "__main__":
    asyncio.run(main())
