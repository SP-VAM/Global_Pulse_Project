import asyncio
from datetime import date, timedelta
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import async_engine
from app.schemas.goal import GoalCreate
from app.services.goal_service import GoalService
from sqlalchemy.ext.asyncio import AsyncSession

async def debug_create():
    async with AsyncSession(async_engine) as session:
        service = GoalService(session)
        req = GoalCreate(
            goal_name="QA Retirement Fund",
            target_quantity=100000.00,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=180),
            unit="INR",
            notes="Testing Live Goal Triggers",
        )
        try:
            res = await service.create_goal(10, req)
            print("Success:", res)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_create())
