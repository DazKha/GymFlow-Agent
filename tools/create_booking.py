from __future__ import annotations

from langchain_core.tools import tool

from tools.client import api_post


@tool
def create_booking(customer_name: str, phone: str, appointment_dt: str, note: str = ''):
    """Create booking for a customer."""
    payload = {
        'customer_name': customer_name,
        'phone': phone,
        'appointment_dt': appointment_dt,
        'note': note or None,
    }
    return api_post('/bookings', payload)
