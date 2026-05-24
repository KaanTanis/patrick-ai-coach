from arq.cron import cron

from app.config import get_settings

settings = get_settings()


def build_cron_jobs(task_functions: dict) -> list:
    interval = settings.outreach_eval_interval_minutes
    if interval >= 60:
        hours = set(range(0, 24, interval // 60))
        outreach_cron = cron(task_functions["adaptive_outreach_task"], hour=hours, minute=0)
    else:
        minutes = set(range(0, 60, interval))
        outreach_cron = cron(task_functions["adaptive_outreach_task"], minute=minutes)

    return [
        cron(task_functions["summarize_stale_sessions"], hour={0, 6, 12, 18}, minute=0),
        cron(task_functions["analyze_behavioral_patterns"], hour=6, minute=0),
        outreach_cron,
        cron(task_functions["decay_memory_importance"], weekday=0, hour=3, minute=0),
        cron(task_functions["consolidate_memories_task"], hour=2, minute=30),
        cron(task_functions["generate_weekly_reflection"], weekday=6, hour=18, minute=0),
        cron(task_functions["generate_monthly_archetype"], day=1, hour=18, minute=0),
        cron(task_functions["cleanup_old_conversations"], hour=4, minute=0),
        cron(task_functions["cleanup_old_photos"], hour=4, minute=30),
    ]
