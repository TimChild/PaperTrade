"""JobExecutionStatus value object - lifecycle state of a scheduled-job run.

Phase J (Task #212 Layer 1) — job-health observability.

The status models the lifecycle of one scheduled-job invocation:

* ``RUNNING`` — ``record_start`` has been written; ``record_finish`` has
  not yet landed. A row left in this state for longer than a job's
  expected cadence indicates a crashed worker.
* ``SUCCEEDED`` — terminal happy path.
* ``FAILED`` — terminal sad path; ``error_message`` should be populated.

States are enforced at the service layer (the decorator). The entity
itself is a plain enum — it doesn't model transitions.
"""

from enum import Enum


class JobExecutionStatus(Enum):
    """Status of a single scheduled-job invocation.

    See module docstring for state semantics.
    """

    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
