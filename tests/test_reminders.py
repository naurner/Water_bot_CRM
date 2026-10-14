from datetime import datetime, timedelta

import pytest

from reminder_service import ReminderScheduler


class FakeJob:
    def __init__(self, name):
        self.name = name
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class FakeJobQueue:
    def __init__(self):
        self.jobs = []

    def run_once(self, callback, when, chat_id, name, data):
        self.jobs.append(FakeJob(name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name and not j.removed]


class FakeContext:
    def __init__(self):
        self.job_queue = FakeJobQueue()


@pytest.mark.asyncio
async def test_future_delivery_gets_two_reminders():
    ctx = FakeContext()
    day = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')

    result = await ReminderScheduler.schedule_reminders(ctx, 1, "W-1", day, "14:00", "Ахунбаева 1")

    assert result['morning']['scheduled'] and result['pre_delivery']['scheduled']
    assert {j.name for j in ctx.job_queue.jobs} == {"W-1:morning", "W-1:pre_delivery"}


@pytest.mark.asyncio
async def test_past_times_are_not_scheduled():
    ctx = FakeContext()
    day = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    result = await ReminderScheduler.schedule_reminders(ctx, 1, "W-2", day, "14:00", "x")

    assert not result['morning']['scheduled'] and not result['pre_delivery']['scheduled']
    assert ctx.job_queue.jobs == []


@pytest.mark.asyncio
async def test_cancel_removes_order_jobs_only():
    ctx = FakeContext()
    day = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    await ReminderScheduler.schedule_reminders(ctx, 1, "W-3", day, "14:00", "x")
    await ReminderScheduler.schedule_reminders(ctx, 1, "W-4", day, "15:00", "x")

    assert await ReminderScheduler.cancel_reminders_for_order(ctx, "W-3") == 2
    assert len(ctx.job_queue.get_jobs_by_name("W-4:morning")) == 1


@pytest.mark.parametrize("hours, expected", [(5, True), (3, False)])
def test_can_reschedule(hours, expected):
    when = datetime.now() + timedelta(hours=hours)
    assert ReminderScheduler.can_reschedule(when.strftime('%Y-%m-%d'), when.strftime('%H:%M')) is expected
