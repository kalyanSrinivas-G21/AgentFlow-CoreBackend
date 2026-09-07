# backend/app/agents/graph.py
import json
import logging
import asyncio
import os
from typing import TypedDict, List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from app.models_ai.ollama_provider import OllamaProvider
from app.models_ai.router import ModelRouter
from app.tools.base import get_tool_catalog

logger = logging.getLogger(__name__)

class ToolCall(BaseModel):
    tool: str = Field(description="Name of the tool to call")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="Arguments matching the tool's JSON schema")

class AgentPlan(BaseModel):
    steps: List[ToolCall] = Field(description="Sequential tools to execute")
    reasoning: str = Field(description="Explanation of the plan")

class AgentState(TypedDict):
    objective: str
    project_id: str
    task_id: str
    context: List[Dict[str, str]]
    plan: List[Dict[str, Any]]
    current_step_index: int
    step_results: List[Dict[str, Any]]
    step_count: int
    max_steps: int
    final_answer: str

class WorkflowGraph:
    def __init__(self, db, redis, executor):
        self.db = db
        self.redis = redis
        self.executor = executor
        
        base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        # Step 12: Override default HTTPX timeout. Local Llama 8b planning takes > 5s.
        self.provider = OllamaProvider(base_url=base_url, timeout_s=120.0)
        
        self.router = ModelRouter()
        self.model = self.router.route(required_capabilities=["tool_calling"])

    async def plan_node(self, state: AgentState) -> AgentState:
        await asyncio.sleep(0)
        logger.info(f"LangGraph: Planning iteration for {state['task_id']}")
        catalog = json.dumps(get_tool_catalog(), indent=2)
        
        system = f"You are an AI Agent. Plan steps to solve the objective. Available Tools:\n{catalog}"
        history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state['context']])
        prompt = f"Objective: {state['objective']}\n\nHistory:\n{history}\n\nEmit a JSON array of tool calls."

        try:
            response = await self.provider.generate(self.model, prompt=prompt, system=system)
            start = response.find("{")
            end = response.rfind("}") + 1
            clean_json = response[start:end] if start != -1 and end != 0 else response
            plan_data = AgentPlan.model_validate_json(clean_json)
            state['plan'] = [step.model_dump() for step in plan_data.steps]
        except Exception as e:
            logger.warning(f"Failed to parse LLM plan: {e}. Defaulting to empty plan.")
            state['plan'] = []
            
        state['current_step_index'] = 0
        state['step_count'] += 1
        return state

    async def execute_node(self, state: AgentState) -> AgentState:
        await asyncio.sleep(0) 
        if state['current_step_index'] >= len(state['plan']):
            return state

        step_data = state['plan'][state['current_step_index']]
        
        class MockPlanStep:
            def __init__(self, t_name, t_args):
                from uuid import uuid4
                self.id = uuid4()
                self.step_number = state['current_step_index'] + 1
                self.tool_name = t_name
                self.tool_args = t_args
                self.status = "PENDING"
                
        mock_step = MockPlanStep(step_data['tool'], step_data['tool_args'])
        tool_result = await self.executor.execute_step(mock_step, state['task_id'])
        
        state['step_results'].append({
            "step": mock_step.step_number,
            "tool": mock_step.tool_name,
            "success": tool_result.success,
            "output": tool_result.output,
            "error": tool_result.error
        })
        
        state['current_step_index'] += 1
        return state

    async def observe_node(self, state: AgentState) -> AgentState:
        await asyncio.sleep(0)
        last_result = state['step_results'][-1] if state['step_results'] else None
        if last_result:
            outcome = f"Tool {last_result['tool']} returned: {last_result['output'] or last_result['error']}"
            state['context'].append({"role": "system", "content": outcome})
        return state

    async def reason_node(self, state: AgentState) -> AgentState:
        await asyncio.sleep(0) 
        if state['step_count'] >= state['max_steps']:
            state['final_answer'] = "Max steps reached without completion."
            return state
            
        system = "You are evaluating the agent's progress. Has the objective been met? Reply strictly with 'COMPLETE: <answer>' or 'CONTINUE: <reason>'."
        history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in state['context']])
        prompt = f"Objective: {state['objective']}\n\nHistory:\n{history}"
        
        try:
            response = await self.provider.generate(self.model, prompt=prompt, system=system)
            if response.strip().upper().startswith("COMPLETE"):
                state['final_answer'] = response.replace("COMPLETE:", "").strip()
            else:
                state['final_answer'] = ""
        except Exception:
            state['final_answer'] = "Internal Error"
            
        return state

    def should_continue(self, state: AgentState) -> str:
        if state['step_count'] >= state['max_steps'] or state['final_answer'] != "":
            return END
        if state['current_step_index'] < len(state['plan']):
            return "execute"
        return "plan"

    def build(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("plan", self.plan_node)
        workflow.add_node("execute", self.execute_node)
        workflow.add_node("observe", self.observe_node)
        workflow.add_node("reason", self.reason_node)
        workflow.set_entry_point("plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "observe")
        workflow.add_edge("observe", "reason")
        workflow.add_conditional_edges("reason", self.should_continue)
        return workflow.compile()