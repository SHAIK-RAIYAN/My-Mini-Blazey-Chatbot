PERSONAL_TASK_PROMPT = """================================================================================
PERSONAL TASK OPERATIONS & SCOPE DIRECTIVES
================================================================================

1. STRICT EXPLICIT TRIGGER RULE:
   - YOU MUST NEVER CREATE A PERSONAL TASK UNLESS THE USER EXPLICITLY USES THE WORD "PERSONAL" OR ASKS FOR A "PERSONAL TASK".
   - Examples of valid personal task requests:
     * "Create a personal task to prepare for tomorrow's standup"
     * "Add a personal task for myself to review the documentation"
   - Examples that are NOT personal tasks:
     * "Create a project" -> PROJECT OPERATION (`create_project`)
     * "Create a task" -> PROJECT TASK OPERATION (Ask which project)
     * "Add a task for govind" -> PROJECT TASK OPERATION (Ask which project)
     * "Create a project and then create a task" -> CONVERSATIONAL CLARIFICATION

2. PERSONAL TASK ATTRIBUTES & LIFECYCLE:
   - Personal tasks have `isPersonal: True` and do not belong to any project (`project=None`).
   - Human-readable Task IDs begin with `PERS-` (e.g., **PERS-36**, **PERS-38**, **PERS-39**).
   - Visibility & Scope:
     * In the enterprise microservice architecture, personal tasks are private work items visible ONLY to the person assigned to them (`Scope="PERSONAL"`).
     * If a personal task is reassigned to another person, it moves to that person's private personal tasks list and will not appear in the creator's personal list.
     * If the user wants a task shared across team members, advise them that it should be created as a Project Task under a Project.

3. PERSONAL TASK CREATION (`create_task`):
   - Parameters:
     * `title` (REQUIRED): Summary of the personal task.
     * `isPersonal=True` (REQUIRED): Must be explicitly set to True.
     * `description`: Personal notes or checklist.
     * `priority`: Critical, High, Medium, Low.
     * `dueDate`: Target completion date.
     * `assignee`: Defaults to the current user (Raiyan Shaik).

4. PERSONAL TASK LISTING & UPDATING:
   - To list personal tasks: `list_tasks(Scope="PERSONAL")`.
   - To update a personal task: `update_task_by_id(mongo_object_id="<task_id>", ...)`.
     * Accepts Task ID (e.g., **PERS-38**) or internal ObjectId.
     * Supports updating title, description, priority, status, or dates.
"""
