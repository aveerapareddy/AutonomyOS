"""Mission planning: LLM when configured, otherwise deterministic rules."""

import os
from typing import Optional

import httpx

from backend.schemas.planner import MissionPlanRequest, MissionPlanResponse
from backend.services.planner_backends.llm_planner import try_plan_with_llm
from backend.services.planner_backends.rule_based_planner import plan_from_rules

DEFAULT_MODEL_ENV = "OPENAI_MODEL"
API_KEY_ENV = "OPENAI_API_KEY"
MODE_ENV = "AUTONOMY_PLANNER_MODE"


class PlannerService:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get(API_KEY_ENV)
        self._model = model if model is not None else os.environ.get(DEFAULT_MODEL_ENV, "gpt-4o-mini")
        self._http_client = http_client

    def plan(self, request: MissionPlanRequest) -> MissionPlanResponse:
        mode = (os.environ.get(MODE_ENV, "auto") or "auto").lower()
        if mode == "rule_based":
            return MissionPlanResponse(plan=plan_from_rules(request.mission_text))

        key = (self._api_key or "").strip()
        if mode in ("auto", "llm") and key:
            plan = try_plan_with_llm(
                request.mission_text,
                key,
                self._model.strip() or "gpt-4o-mini",
                client=self._http_client,
            )
            if plan is not None:
                return MissionPlanResponse(plan=plan)

        return MissionPlanResponse(plan=plan_from_rules(request.mission_text))
