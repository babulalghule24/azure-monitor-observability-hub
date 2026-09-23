"""STEP 6 - Concurrent: three specialists read the same week at once.

WHAT THIS ADDS: fan-out / fan-in. Signal, Resilience and CaseReview each read a different
source. None needs another's output, so running them one at a time is wasted latency.

This is the honest case for "parallel". Most people reach for concurrent when they should
not - so learn the test: if agent B should read agent A's answer, this is the wrong pattern.

Run:  python src/step6_concurrent_gather.py
"""

import asyncio

from agent_framework.orchestrations import ConcurrentBuilder

from common import THIS_WEEK, build_desk, get_client


async def main():
    desk = build_desk(get_client())

    workflow = (
        ConcurrentBuilder()
        .participants([desk["signal"], desk["resilience"], desk["cases"]])
        .build()
    )

    async for event in workflow.run_stream(THIS_WEEK):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())

# CHECK YOUR UNDERSTANDING
# * Nobody merged the three answers. The default aggregator returns one message per
#   participant. Who should merge - a custom aggregator, or the Reporter in step 5?
# * What do you do when Signal and Resilience contradict each other? Decide that now,
#   not in production.
# * Stretch: add the Reporter as a fourth concurrent participant and watch it write a
#   service review based on nothing. That failure IS the lesson.
