"""iCloud CalDAV integration — syncs events directly to iPhone calendar."""

import asyncio
import uuid
import logging
from datetime import datetime, timedelta

from config import settings

log = logging.getLogger(__name__)

_ICLOUD_URL = "https://caldav.icloud.com"


def _icloud_configured() -> bool:
    return bool(settings.ICLOUD_USERNAME and settings.ICLOUD_PASSWORD)


def _create_sync(title: str, start_dt: datetime, end_dt: datetime,
                 description: str, reminder_minutes: int) -> str:
    import caldav
    from icalendar import Calendar as iCal, Event, Alarm

    client = caldav.DAVClient(
        url=_ICLOUD_URL,
        username=settings.ICLOUD_USERNAME,
        password=settings.ICLOUD_PASSWORD,
    )
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("Нет доступных календарей iCloud")

    # Prefer a calendar named "Home", "Дом", "Personal" or fallback to first
    cal_obj = calendars[0]
    for c in calendars:
        try:
            if c.name.lower() in ("home", "дом", "personal", "личное", "основной"):
                cal_obj = c
                break
        except Exception:
            pass

    event_uid = str(uuid.uuid4())
    cal = iCal()
    event = Event()
    event.add("uid", event_uid)
    event.add("summary", title)
    event.add("dtstart", start_dt)
    event.add("dtend", end_dt)
    event.add("description", description)

    alarm = Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add("description", title)
    alarm.add("trigger", timedelta(minutes=-reminder_minutes))
    event.add_component(alarm)

    cal.add_component(event)
    cal_obj.add_event(cal.to_ical().decode("utf-8"))
    return event_uid


def _delete_sync(ical_uid: str):
    import caldav

    client = caldav.DAVClient(
        url=_ICLOUD_URL,
        username=settings.ICLOUD_USERNAME,
        password=settings.ICLOUD_PASSWORD,
    )
    principal = client.principal()
    for calendar in principal.calendars():
        try:
            events = calendar.search(uid=ical_uid)
            for e in events:
                e.delete()
                return
        except Exception:
            pass


async def create_event(title: str, start_dt: datetime, end_dt: datetime,
                       description: str = "", reminder_minutes: int = 30) -> str | None:
    if not _icloud_configured():
        return None
    try:
        loop = asyncio.get_event_loop()
        uid = await loop.run_in_executor(
            None, _create_sync, title, start_dt, end_dt, description, reminder_minutes
        )
        return uid
    except Exception as e:
        log.warning("iCloud create error: %s", e)
        return None


async def delete_event(ical_uid: str) -> bool:
    if not _icloud_configured() or not ical_uid:
        return False
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _delete_sync, ical_uid)
        return True
    except Exception as e:
        log.warning("iCloud delete error: %s", e)
        return False


def icloud_enabled() -> bool:
    return _icloud_configured()
