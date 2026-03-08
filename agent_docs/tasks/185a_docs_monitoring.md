# Docs Refactorer Task: Monitoring Consolidation

**Target**: `docs/monitoring/`

## Instructions

1.  **Analyze `docs/monitoring/`**:
    - `alert-configuration.md`
    - `grafana-cloud-setup.md`
    - `monitoring-runbook.md`
    - `dashboards/README.md`
    - `dashboards/application-overview.md`
    - `dashboards/trading-activity.md`
    - `dashboards/external-services.md`

2.  **Consolidate**:
    - Create a primary `docs/monitoring/README.md`.
    - Integrate `grafana-cloud-setup.md` as a "Setup" section.
    - Integrate `alert-configuration.md` as an "Alerts" section.
    - Integrate `monitoring-runbook.md` as a "Runbook" section or keep as separate linked file if large (it was ~280 lines in the count, probably keep separate but link clearly).
    - Summarize the Dashboards in the README.

3.  **Cleanup**:
    - Move detailed dashboard JSONs or descriptors to `docs/monitoring/assets/` or `infra/monitoring/` if they aren't documentation.
    - Delete the loose files once their content is merged.

4.  **Verification**:
    - Ensure new README links work.
    - Ensure no critical info is lost.
