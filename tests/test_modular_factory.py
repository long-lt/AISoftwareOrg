from factory_core import FactoryRequest, PipelineBuilder


def test_build_mobile_flutter_pipeline():
    request = FactoryRequest(
        name="PantrySaver",
        slug="pantry-saver",
        description="Food expiry tracker and meal planner",
        project_type="mobile_app",
        targets=["mobile"],
        stack={
            "mobile": "flutter",
        },
        features=["inventory", "expiry_reminders", "meal_planner"],
    )

    plan = PipelineBuilder().build(request)

    assert plan.workflow.id == "mobile_app"
    assert any(step.module_id == "mobile.flutter" for step in plan.steps)
    assert any(step.module_id == "common.qa" for step in plan.steps)
    assert any(step.module_id == "common.export" for step in plan.steps)


def test_build_fullstack_saas_pipeline():
    request = FactoryRequest(
        name="AISaaS",
        slug="ai-saas",
        description="Fullstack SaaS with web dashboard and backend API",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "nextjs",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth", "dashboard", "billing"],
    )

    plan = PipelineBuilder().build(request)

    module_ids = [step.module_id for step in plan.steps]

    assert plan.workflow.id == "fullstack_saas"
    assert "frontend.nextjs" in module_ids
    assert "backend.fastapi" in module_ids
    assert "database.supabase" in module_ids
    assert "common.security" in module_ids
    assert "common.export" in module_ids


def test_pipeline_plan_to_dict():
    request = FactoryRequest(
        name="Backend API",
        slug="backend-api",
        description="Simple backend API",
        project_type="fullstack_saas",
        targets=["web", "backend"],
        stack={
            "frontend": "react",
            "backend": "fastapi",
            "database": "supabase",
        },
        features=["auth"],
    )

    plan = PipelineBuilder().build(request)
    payload = plan.to_dict()

    assert payload["project"]["name"] == "Backend API"
    assert payload["workflow"]["id"] == "fullstack_saas"
    assert len(payload["steps"]) > 0
