# WORKFLOW_CONTEXT.md: Blazeup Agentic Orchestrator

## 1. System Topology & Directory Layout
BACKEND/
├── .env
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── core/ (security.py, logging.py)
│   ├── clients/ (http_client.py, task_client.py, employee_client.py)
│   ├── models/ (agent_state.py, task_models.py, employee_models.py)
│   ├── tools/ (task_tools.py, employee_tools.py, web_tools.py)
│   ├── agent/ (graph.py, state.py, nodes.py, prompts.py)
│   └── db/ (mongo.py)
FRONTEND/

## 2. API Integration Specifications
### 2.1 Project Service (Tasks)
- URL: `http://api.stg.blazeup.ai/project-api`
- Mandatory Rule: Pass `"isPersonal": true` on all created tasks.
- List Tasks: Pass `Scope=PERSONAL` and `flat=true`.
- Update Target: `PATCH /project-api/task/multiple?ids={taskId}`
- Plural Queries: Use `taskNumbers` and `assignees`.

### 2.2 Employee Service
- URL: `http://api.stg.blazeup.ai/employees-api`
- Create Rule: `emergencyContacts` must have exactly one `"isPrimary": true`.
- Read Scopes: `scope=team` is mandatory for regular lookup.

## 3. Agent Execution Rules
- Max 2 clarifying questions for ambiguous intents. No looping.
- HITL (Human-in-the-loop) required for all bulk updates or status mutations.
