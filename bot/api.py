from datetime import date, timedelta
import httpx
from bot.config import API_BASE_URL


class DjangoAPIClient:

    def __init__(self):
        self.base_url = API_BASE_URL

    async def get_specialities(self, page=1):
        async with httpx.AsyncClient() as client:
            try:
                params = {"page": page}

                res = await client.get(
                    f"{self.base_url}/specialities/",
                    params=params
                )

                if res.status_code == 200:
                    data = res.json()

                    if isinstance(data, dict):
                        return {
                            "results": data.get("results", []),
                            "has_next": bool(data.get("next")),
                            "has_previous": bool(data.get("previous")),
                        }

                    elif isinstance(data, list):
                        return {
                            "results": data,
                            "has_next": False,
                            "has_previous": False,
                        }

                return {
                    "results": [],
                    "has_next": False,
                    "has_previous": False,
                }

            except Exception:
                return {
                    "results": [],
                    "has_next": False,
                    "has_previous": False,
                }

    async def get_doctors(self, speciality_id=None, page=1):
        """Shifokorlar ro'yxatini olish (mutaxassislik va sahifa bo'yicha)"""
        async with httpx.AsyncClient() as client:
            try:
                params = {"is_active": True, "page": page}
                if speciality_id:
                    params["speciality"] = speciality_id
                res = await client.get(f"{self.base_url}/doctors/", params=params)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, dict):
                        return {
                            "results": data.get("results", []),
                            "has_next": bool(data.get("next")),
                            "has_previous": bool(data.get("previous")),
                        }
                    elif isinstance(data, list):
                        return {"results": data, "has_next": False, "has_previous": False}
                return {"results": [], "has_next": False, "has_previous": False}
            except Exception:
                return {"results": [], "has_next": False, "has_previous": False}

    async def get_available_days(self, doctor_id):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(
                    f"{self.base_url}/slots/available-days/",
                    params={"doctor": doctor_id},
                )
                if res.status_code == 200:
                    data = res.json()
                    return data if isinstance(data, list) else []
                return []
            except Exception:
                return []

    async def get_slots(self, doctor_id, date_str):
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(
                    f"{self.base_url}/slots/",
                    params={"doctor": doctor_id, "date": date_str},
                )
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, dict):
                        return data.get("results", [])
                    elif isinstance(data, list):
                        return data
                return []
            except Exception:
                return []

    async def create_appointment(self, token, slot_id, complaint=""):
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/appointments/create/",
                    json={"slot": slot_id, "complaint": complaint},
                    headers=headers,
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def get_my_appointments(self, token):
        """Foydalanuvchining barcha navbatlarini olish (barcha sahifalar bo'yicha)"""
        headers = {"Authorization": f"Bearer {token}"}
        all_results = []
        url = f"{self.base_url}/my-appointments/"

        async with httpx.AsyncClient() as client:
            try:
                while url:
                    res = await client.get(url, headers=headers)
                    if res.status_code != 200:
                        break

                    data = res.json()

                    if isinstance(data, dict):
                        all_results.extend(data.get("results", []))
                        url = data.get("next")
                    elif isinstance(data, list):
                        all_results.extend(data)
                        url = None
                    else:
                        url = None

                return all_results
            except Exception:
                return all_results

    async def cancel_appointment(self, token, appointment_id):
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/appointments/{appointment_id}/cancel/",
                    headers=headers,
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def login_or_register(self, phone, telegram_id=None):
        payload = {"phone": phone}
        if telegram_id:
            payload["telegram_id"] = telegram_id

        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/auth/telegram/", json=payload
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def dev_switch_role(self, telegram_id, role):
        """FAQAT dev/test uchun — rolni almashtirish"""
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/dev/switch-role/",
                    json={"telegram_id": telegram_id, "role": role},
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def get_doctor_appointments(self, token, date_str):
        """Shifokorning berilgan kundagi navbatlari"""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(
                    f"{self.base_url}/appointments/",
                    params={"slot__date": date_str},
                    headers=headers,
                )
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, dict):
                        return data.get("results", [])
                    elif isinstance(data, list):
                        return data
                return []
            except Exception:
                return []

    async def update_appointment_status(self, token, appointment_id, new_status):
        """Navbat statusini 'keldi' yoki 'kelmadi' ga o'zgartirish"""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/appointments/{appointment_id}/status/",
                    json={"status": new_status},
                    headers=headers,
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def create_visit(self, token, appointment_id, diagnosis, recommendation=""):
        """Qabul natijasini (tashxis) yozish"""
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/visits/",
                    json={
                        "appointment": appointment_id,
                        "diagnosis": diagnosis,
                        "recommendation": recommendation,
                    },
                    headers=headers,
                )
                try:
                    response_data = res.json()
                except Exception:
                    response_data = {"detail": f"Server xatosi (HTTP {res.status_code})."}
                return res.status_code, response_data
            except Exception as e:
                return 500, {"error": str(e)}

    async def get_doctor_daily_report(self, token, date_str):
        """Shifokorning kunlik hisobotini olish va hisoblash"""
        appointments = await self.get_doctor_appointments(token, date_str)
        
        total_patients = len(appointments)
        visited_count = 0
        cancelled_count = 0
        total_income = 0

        patients_detail = []

        for app in appointments:
            status = app.get("status")
            price = float(app.get("price") or app.get("amount") or 0)
            patient_name = app.get("patient_name") or "-"
            start_time = app.get("start_time") or "-"

            if status == "keldi":
                visited_count += 1
                total_income += price
            elif status == "kelmadi":
                cancelled_count += 1

            patients_detail.append({
                "name": patient_name,
                "time": start_time,
                "status": status,
                "price": price
            })

        return {
            "date": date_str,
            "total_patients": total_patients,
            "visited_count": visited_count,
            "cancelled_count": cancelled_count,
            "total_income": total_income,
            "patients": patients_detail
        }


api_client = DjangoAPIClient()