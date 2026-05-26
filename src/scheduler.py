"""APScheduler wrapper.

Two firing modes:
1. Built-in named slots (morning_brief, evening_reflection, ...) — each
   fires once per day inside its random window.
2. Variable-reward background nudges — to top up `messages_per_day`,
   we schedule N additional random-time messages each morning.

Variability is intentional: dopamine fires hardest on *unpredictable*
reward, so a fixed cron schedule would dull the system over weeks.
We don't fire outside active_hours."""

from __future__ import annotations
import logging
import random
from datetime import datetime, time, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from .telegram_bot import Bot

log = logging.getLogger(__name__)


def _parse_hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


class Scheduler:
    def __init__(self, cfg: dict, bot: Bot, tz_name: str = "Asia/Seoul"):
        self.cfg = cfg
        self.bot = bot
        self.tz = pytz.timezone(tz_name)
        self.scheduler = AsyncIOScheduler(timezone=self.tz)

    def start(self) -> None:
        sched = self.cfg["scheduling"]

        # 1) Daily replanner — every day at 02:00 (very off-hours, won't
        # surprise the user). It clears yesterday's random jobs and
        # schedules today's.
        self.scheduler.add_job(
            self._plan_today,
            CronTrigger(hour=2, minute=0),
            id="daily_planner",
            replace_existing=True,
        )

        # And run once now so we don't wait until tomorrow to schedule.
        self.scheduler.add_job(
            self._plan_today,
            DateTrigger(run_date=datetime.now(self.tz) + timedelta(seconds=5)),
            id="initial_plan",
            replace_existing=True,
        )

        self.scheduler.start()
        log.info("Scheduler started; planner runs daily at 02:00 %s.", self.tz)

    async def _plan_today(self) -> None:
        """Schedule today's check-ins. Idempotent — wipes any previously-
        scheduled per-slot jobs first."""
        sched = self.cfg["scheduling"]
        now = datetime.now(self.tz)
        today = now.date()

        active_start = _parse_hhmm(sched["active_hours"]["start"])
        active_end = _parse_hhmm(sched["active_hours"]["end"])

        # Clear yesterday's slot jobs
        for job in self.scheduler.get_jobs():
            if job.id.startswith("slot_") or job.id.startswith("freejitter_"):
                job.remove()

        # 2) Named slots
        scheduled_times: list[datetime] = []
        for slot in sched["slots"]:
            win_start = _parse_hhmm(slot["window"][0])
            win_end = _parse_hhmm(slot["window"][1])
            fire_dt = self._random_dt_in_window(today, win_start, win_end)

            # Skip slots whose window has already passed today
            if fire_dt <= now + timedelta(seconds=10):
                continue

            self.scheduler.add_job(
                self.bot.send_proactive_async,
                DateTrigger(run_date=fire_dt),
                args=[slot["kind"]],
                id=f"slot_{slot['id']}_{today.isoformat()}",
                replace_existing=True,
            )
            scheduled_times.append(fire_dt)
            log.info("Scheduled %s at %s", slot["kind"], fire_dt.strftime("%H:%M"))

        # 3) Extra random-time freeform nudges (variable-reward top-up)
        needed = max(0, sched["messages_per_day"] - len(scheduled_times))
        for i in range(needed):
            fire_dt = self._random_dt_in_window(today, active_start, active_end)
            if fire_dt <= now + timedelta(minutes=10):
                continue
            # Skip if too close to an existing scheduled time (≥45min apart)
            if any(abs((fire_dt - t).total_seconds()) < 45 * 60 for t in scheduled_times):
                continue
            kind = random.choice(["focus_nudge", "pulse_check"])
            self.scheduler.add_job(
                self.bot.send_proactive_async,
                DateTrigger(run_date=fire_dt),
                args=[kind],
                id=f"freejitter_{today.isoformat()}_{i}",
                replace_existing=True,
            )
            scheduled_times.append(fire_dt)
            log.info("Extra %s at %s", kind, fire_dt.strftime("%H:%M"))

    def _random_dt_in_window(
        self, day, start: time, end: time
    ) -> datetime:
        start_dt = self.tz.localize(datetime.combine(day, start))
        end_dt = self.tz.localize(datetime.combine(day, end))
        span = (end_dt - start_dt).total_seconds()
        offset = random.uniform(0, max(span, 1))
        return start_dt + timedelta(seconds=offset)
