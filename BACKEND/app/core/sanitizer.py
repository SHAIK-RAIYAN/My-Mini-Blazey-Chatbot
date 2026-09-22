import json
from typing import Any

def _minimize_employee(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return item
    personal = item.get("personalInfo", {}) if isinstance(item.get("personalInfo"), dict) else {}
    contact = personal.get("contact", {}) if isinstance(personal.get("contact"), dict) else {}
    employment = item.get("employmentDetail", {}) if isinstance(item.get("employmentDetail"), dict) else {}

    title = employment.get("jobTitle", {}) if isinstance(employment.get("jobTitle"), dict) else {}
    title_name = title.get("name") or item.get("jobTitle") or ""

    first_name = personal.get("firstName") or item.get("firstName") or ""
    last_name = personal.get("lastName") or item.get("lastName") or ""
    email = contact.get("workEmail") or item.get("workEmail") or ""
    emp_id = item.get("employeeId") or ""
    raw_id = item.get("_id")
    if raw_id is not None:
        mongo_id = str(raw_id)
    elif item.get("id") and len(str(item.get("id"))) == 24:
        mongo_id = str(item.get("id"))
    else:
        mongo_id = ""

    return {
        "_id": mongo_id,
        "employeeId": emp_id,
        "firstName": first_name,
        "lastName": last_name,
        "workEmail": email,
        "jobTitle": title_name,
    }

def _minimize_task(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return item
    assignee = item.get("assignee")
    if isinstance(assignee, dict):
        assignee_val = assignee.get("name") or assignee.get("legalName") or assignee.get("workEmail") or assignee.get("employeeId") or ""
    else:
        assignee_val = str(assignee or "")

    if not assignee_val and isinstance(item.get("assignees"), list) and item["assignees"]:
        first_a = item["assignees"][0]
        if isinstance(first_a, dict):
            assignee_val = first_a.get("name") or first_a.get("legalName") or first_a.get("employeeId") or ""
        else:
            assignee_val = str(first_a)

    priority = item.get("priority")
    priority_val = priority.get("name") if isinstance(priority, dict) else str(priority or "")

    status = item.get("status")
    status_val = status.get("name") if isinstance(status, dict) else str(status or "")

    raw_id = item.get("_id")
    if raw_id is not None:
        mongo_id = str(raw_id)
    elif item.get("id") and len(str(item.get("id"))) == 24:
        mongo_id = str(item.get("id"))
    else:
        mongo_id = ""

    task_num = str(item.get("taskNumber") or item.get("number") or item.get("id") or "")

    return {
        "_id": mongo_id,
        "id": task_num or mongo_id,
        "title": item.get("title") or item.get("name") or "",
        "status": status_val,
        "priority": priority_val,
        "taskType": item.get("taskType") or item.get("type") or "",
        "assignee": assignee_val,
    }

def _minimize_record(item: dict[str, Any], entity_type: str | None = None) -> dict[str, Any]:
    if not isinstance(item, dict):
        return item
    if entity_type == "employee":
        return _minimize_employee(item)
    if entity_type == "task":
        return _minimize_task(item)
    if any(k in item for k in ("personalInfo", "employmentDetail", "workEmail", "firstName", "lastName", "employeeId")):
        return _minimize_employee(item)
    if any(k in item for k in ("taskType", "taskNumber", "assignee", "title")):
        return _minimize_task(item)
    return item

def project_tool_output(data: Any, entity_type: str | None = None) -> str:
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            return data
    if isinstance(data, dict):
        if "error" in data or "errors" in data:
            return json.dumps(data, separators=(",", ":"))
        if data.get("statusCode") and data["statusCode"] >= 400:
            return json.dumps(data, separators=(",", ":"))
        records = data.get("data")
        if isinstance(records, list):
            total_records = len(records)
            sliced = records[:5]
            minimized_records = [_minimize_record(r, entity_type) for r in sliced]
            result: dict[str, Any] = {
                "statusCode": data.get("statusCode", 200),
                "data": minimized_records,
            }
            if total_records > 5:
                result["meta"] = "Results truncated to top 5 to preserve token limits."
            for k in ("message", "total", "statusCode"):
                if k in data and k not in result:
                    result[k] = data[k]
            return json.dumps(result, separators=(",", ":"))
        elif isinstance(records, dict):
            minimized = _minimize_record(records, entity_type)
            result = {
                "statusCode": data.get("statusCode", 200),
                "data": minimized,
            }
            if "message" in data:
                result["message"] = data["message"]
            return json.dumps(result, separators=(",", ":"))
        return json.dumps(_minimize_record(data, entity_type), separators=(",", ":"))
    if isinstance(data, list):
        total_records = len(data)
        sliced = data[:5]
        minimized_records = [_minimize_record(r, entity_type) for r in sliced]
        result: dict[str, Any] = {"data": minimized_records}
        if total_records > 5:
            result["meta"] = "Results truncated to top 5 to preserve token limits."
        return json.dumps(result, separators=(",", ":"))
    return json.dumps(data, separators=(",", ":"))
