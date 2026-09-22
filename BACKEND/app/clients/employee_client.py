from typing import Any
from app.config import settings
from app.clients.http_client import BaseAPIClient

class EmployeeClient(BaseAPIClient):
    def __init__(self, base_url: str | None = None):
        target_url = base_url or settings.EMPLOYEE_API_BASE_URL
        super().__init__(base_url=target_url)

    async def create_employee(self, payload: dict) -> dict:
        data = dict(payload)
        personal_info = data.get("personalInfo")
        if isinstance(personal_info, dict):
            if "dob" not in personal_info:
                personal_info["dob"] = "1995-01-01"
            if "gender" not in personal_info:
                personal_info["gender"] = "PREFER_NOT_TO_SAY"
            contacts = personal_info.get("emergencyContacts")
            if isinstance(contacts, list) and contacts:
                primary_found = False
                for c in contacts:
                    if isinstance(c, dict):
                        if c.get("isPrimary") and not primary_found:
                            primary_found = True
                        else:
                            c["isPrimary"] = False
                if not primary_found and isinstance(contacts[0], dict):
                    contacts[0]["isPrimary"] = True
            elif not contacts:
                personal_info["emergencyContacts"] = [
                    {
                        "name": "Primary Contact",
                        "relationship": "OTHER",
                        "isPrimary": True,
                        "phone": {"countryCode": "+1", "number": "0000000000"},
                    }
                ]
        elif isinstance(data.get("emergencyContacts"), list) and data["emergencyContacts"]:
            contacts = data["emergencyContacts"]
            primary_found = False
            for c in contacts:
                if isinstance(c, dict):
                    if c.get("isPrimary") and not primary_found:
                        primary_found = True
                    else:
                        c["isPrimary"] = False
            if not primary_found and isinstance(contacts[0], dict):
                contacts[0]["isPrimary"] = True

        return await self.post("/employees", json=data)

    async def list_employees(self, params: dict | None = None) -> dict:
        query_params = dict(params or {})
        if "scope" not in query_params:
            query_params["scope"] = "company"
        return await self.get("/employees", params=query_params)

    async def get_employee(self, employee_id: str, response_fields: str | None = None) -> dict:
        params = {}
        if response_fields:
            params["responseFields"] = response_fields
        return await self.get(f"/employees/{employee_id}", params=params or None)

    async def update_employee(self, employee_id: str, payload: dict) -> dict:
        return await self.patch(f"/employees/{employee_id}", json=payload)

    async def update_personal_info(self, employee_id: str, payload: dict) -> dict:
        return await self.patch(f"/employees/{employee_id}/personal-info", json=payload)
