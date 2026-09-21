# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import api, fields, models


class EquipmentInspectionDashboard(models.AbstractModel):
    _name = "equipment.inspection.dashboard"
    _description = "Equipment Inspection Dashboard"

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}

        Equipment = self.env["maintenance.equipment"]
        Report = self.env["equipment.daily.report"]
        Line = self.env["equipment.daily.report.line"]
        Maintenance = self.env["maintenance.request"]
        SparePart = self.env["equipment.spare.part"]

        category_id = self._to_int(filters.get("category_id"))
        equipment_id = self._to_int(filters.get("equipment_id"))
        location = (filters.get("location") or "").strip()
        severity = filters.get("severity") or False
        operational_status = filters.get("operational_status") or False

        today = fields.Date.context_today(self)

        default_from = today - timedelta(days=29)

        date_from = (
            self._to_date(filters.get("date_from"))
            or default_from
        )

        date_to = (
            self._to_date(filters.get("date_to"))
            or today
        )

        if date_from > date_to:
            date_from, date_to = date_to, date_from

        # =====================================================
        # Equipment filters
        # =====================================================

        equipment_domain = []

        if category_id:
            equipment_domain.append(
                ("category_id", "=", category_id)
            )

        if equipment_id:
            equipment_domain.append(
                ("id", "=", equipment_id)
            )

        if location:
            equipment_domain.append(
                ("location", "=", location)
            )

        if operational_status:
            equipment_domain.append(
                (
                    "operational_status",
                    "=",
                    operational_status,
                )
            )

        equipment_records = Equipment.search(
            equipment_domain
        )

        equipment_ids = equipment_records.ids

        # =====================================================
        # Inspection domain
        # =====================================================

        report_domain = [
            ("equipment_id", "in", equipment_ids),
        ]

        report_domain += self._datetime_domain(
            "report_date",
            date_from,
            date_to,
        )

        # =====================================================
        # Failed inspection lines
        # =====================================================

        failed_line_domain = [
            ("answer", "=", "no"),
            (
                "report_id.equipment_id",
                "in",
                equipment_ids,
            ),
        ]

        failed_line_domain += self._datetime_domain(
            "report_id.report_date",
            date_from,
            date_to,
        )

        if severity:
            failed_line_domain.append(
                (
                    "failure_severity",
                    "=",
                    severity,
                )
            )

        # =====================================================
        # Inspection-generated maintenance requests
        # =====================================================

        maintenance_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            ),
            (
                "is_inspection_generated",
                "=",
                True,
            ),
            (
                "archive",
                "=",
                False,
            ),
        ]

        maintenance_domain += self._date_domain(
            "request_date",
            date_from,
            date_to,
        )

        if severity:
            maintenance_domain.append(
                (
                    "inspection_failure_severity",
                    "=",
                    severity,
                )
            )

        # =====================================================
        # Equipment KPIs
        # =====================================================

        total_equipment = len(
            equipment_records
        )

        active_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status == "active"
            )
        )

        maintenance_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                == "maintenance"
            )
        )

        out_of_service_equipment = len(
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                == "out_of_service"
            )
        )

        availability_rate = self._percent(
            active_equipment,
            total_equipment,
        )

        # =====================================================
        # Inspection KPIs
        # =====================================================

        total_inspections = Report.search_count(
            report_domain
        )

        today_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            )
        ]

        today_domain += self._datetime_domain(
            "report_date",
            today,
            today,
        )

        inspections_today = Report.search_count(
            today_domain
        )

        draft_inspections = Report.search_count(
            report_domain
            + [
                ("state", "=", "draft"),
            ]
        )

        submitted_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "submitted",
                    )
                ]
            )
        )

        approved_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "approved",
                    )
                ]
            )
        )

        closed_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "state",
                        "=",
                        "closed",
                    )
                ]
            )
        )

        failed_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "has_issue",
                        "=",
                        True,
                    )
                ]
            )
        )

        critical_inspections = (
            Report.search_count(
                report_domain
                + [
                    (
                        "has_critical_issue",
                        "=",
                        True,
                    )
                ]
            )
        )

        completed_domain = (
            report_domain
            + [
                (
                    "state",
                    "in",
                    [
                        "submitted",
                        "approved",
                        "closed",
                    ],
                )
            ]
        )

        completed_inspections = (
            Report.search_count(
                completed_domain
            )
        )

        passed_completed = (
            Report.search_count(
                completed_domain
                + [
                    (
                        "has_issue",
                        "=",
                        False,
                    )
                ]
            )
        )

        pass_rate = self._percent(
            passed_completed,
            completed_inspections,
        )

        # =====================================================
        # Maintenance KPIs
        # =====================================================

        open_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "stage_id.done",
                        "=",
                        False,
                    )
                ]
            )
        )

        completed_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "stage_id.done",
                        "=",
                        True,
                    )
                ]
            )
        )

        critical_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "inspection_failure_severity",
                        "=",
                        "critical",
                    )
                ]
            )
        )

        in_progress_maintenance = (
            Maintenance.search_count(
                maintenance_domain
                + [
                    (
                        "stage_id.done",
                        "=",
                        False,
                    ),
                    (
                        "kanban_state",
                        "=",
                        "normal",
                    ),
                ]
            )
        )

        # =====================================================
        # Spare parts
        # =====================================================

        spare_part_domain = [
            (
                "equipment_id",
                "in",
                equipment_ids,
            ),
            (
                "active",
                "=",
                True,
            ),
        ]

        spare_parts = SparePart.search(
            spare_part_domain
        )

        warning_date = (
            today
            + timedelta(days=7)
        )

        overdue_parts = (
            spare_parts.filtered(
                lambda part:
                part.next_maintenance_date
                and
                part.next_maintenance_date
                < today
            )
        )

        due_soon_parts = (
            spare_parts.filtered(
                lambda part:
                part.next_maintenance_date
                and
                today
                <= part.next_maintenance_date
                <= warning_date
            )
        )

        healthy_parts = (
            spare_parts
            - overdue_parts
            - due_soon_parts
        )

        # =====================================================
        # Analytics
        # =====================================================

        severity_counts = (
            self._severity_counts(
                failed_line_domain,
                Line,
            )
        )

        top_defects = (
            self._top_defects(
                failed_line_domain,
                Line,
            )
        )

        category_failures = (
            self._category_failures(
                report_domain,
                Report,
            )
        )

        location_failures = (
            self._location_failures(
                report_domain,
                Report,
            )
        )

        inspection_trend = (
            self._inspection_trend(
                report_domain,
                Report,
                date_from,
                date_to,
            )
        )

        # =====================================================
        # Detail tables
        # =====================================================

        recent_critical = (
            self._recent_critical(
                report_domain,
                Report,
            )
        )

        equipment_attention = (
            self._equipment_attention(
                equipment_records
            )
        )

        overdue_parts_rows = (
            self._overdue_parts_rows(
                overdue_parts,
                today,
            )
        )

        recent_maintenance = (
            self._recent_maintenance(
                maintenance_domain,
                Maintenance,
            )
        )

        return {

            "filters": {
                "date_from":
                    fields.Date.to_string(
                        date_from
                    ),

                "date_to":
                    fields.Date.to_string(
                        date_to
                    ),

                "category_id":
                    category_id or False,

                "equipment_id":
                    equipment_id or False,

                "location":
                    location or False,

                "severity":
                    severity or False,

                "operational_status":
                    operational_status
                    or False,
            },

            "filter_options":
                self._get_filter_options(),

            "alerts": {
                "critical_inspections":
                    critical_inspections,

                "open_maintenance":
                    open_maintenance,

                "out_of_service":
                    out_of_service_equipment,

                "overdue_parts":
                    len(overdue_parts),

                "pending_approval":
                    submitted_inspections,
            },

            "equipment": {
                "total":
                    total_equipment,

                "active":
                    active_equipment,

                "maintenance":
                    maintenance_equipment,

                "out_of_service":
                    out_of_service_equipment,

                "availability_rate":
                    availability_rate,
            },

            "inspections": {
                "total":
                    total_inspections,

                "today":
                    inspections_today,

                "draft":
                    draft_inspections,

                "submitted":
                    submitted_inspections,

                "approved":
                    approved_inspections,

                "closed":
                    closed_inspections,

                "failed":
                    failed_inspections,

                "critical":
                    critical_inspections,

                "pass_rate":
                    pass_rate,
            },

            "maintenance": {
                "open":
                    open_maintenance,

                "in_progress":
                    in_progress_maintenance,

                "critical":
                    critical_maintenance,

                "completed":
                    completed_maintenance,
            },

            "spare_parts": {
                "total":
                    len(spare_parts),

                "healthy":
                    len(healthy_parts),

                "due_soon":
                    len(due_soon_parts),

                "overdue":
                    len(overdue_parts),
            },

            "analytics": {
                "severity":
                    severity_counts,

                "top_defects":
                    top_defects,

                "category_failures":
                    category_failures,

                "location_failures":
                    location_failures,

                "inspection_trend":
                    inspection_trend,
            },

            "details": {
                "recent_critical":
                    recent_critical,

                "equipment_attention":
                    equipment_attention,

                "overdue_parts":
                    overdue_parts_rows,

                "recent_maintenance":
                    recent_maintenance,
            },
        }

    # =========================================================
    # Dashboard navigation
    # =========================================================

    @api.model
    def action_open_equipment(
        self,
        equipment_id,
    ):
        equipment = (
            self.env[
                "maintenance.equipment"
            ]
            .browse(
                int(equipment_id)
            )
            .exists()
        )

        if not equipment:
            return False

        # Explicitly open OUR custom equipment view.
        # This avoids changing/using the standard Odoo
        # Maintenance equipment form.
        view = self.env.ref(
            "daily_equipment_report."
            "view_daily_inspection_equipment_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                equipment.display_name,

            "res_model":
                "maintenance.equipment",

            "res_id":
                equipment.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    @api.model
    def action_open_inspection(
        self,
        inspection_id,
    ):
        report = (
            self.env[
                "equipment.daily.report"
            ]
            .browse(
                int(inspection_id)
            )
            .exists()
        )

        if not report:
            return False

        view = self.env.ref(
            "daily_equipment_report."
            "view_equipment_daily_report_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                report.display_name,

            "res_model":
                "equipment.daily.report",

            "res_id":
                report.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    @api.model
    def action_open_maintenance_request(
        self,
        request_id,
    ):
        request = (
            self.env[
                "maintenance.request"
            ]
            .browse(
                int(request_id)
            )
            .exists()
        )

        if not request:
            return False

        view = self.env.ref(
            "maintenance."
            "hr_equipment_request_view_form"
        )

        return {
            "type":
                "ir.actions.act_window",

            "name":
                request.display_name,

            "res_model":
                "maintenance.request",

            "res_id":
                request.id,

            "view_mode":
                "form",

            "views": [
                (
                    view.id,
                    "form",
                )
            ],

            "target":
                "current",
        }

    # =========================================================
    # Filter data
    # =========================================================

    @api.model
    def _get_filter_options(self):

        Equipment = self.env[
            "maintenance.equipment"
        ]

        Category = self.env[
            "maintenance.equipment.category"
        ]

        equipments = Equipment.search(
            [],
            order="name, id",
        )

        categories = Category.search(
            [],
            order="name, id",
        )

        locations = sorted(
            {
                rec.location.strip()
                for rec in equipments
                if rec.location
                and rec.location.strip()
            }
        )

        return {

            "categories": [
                {
                    "id":
                        rec.id,

                    "name":
                        rec.display_name,
                }
                for rec in categories
            ],

            "equipments": [
                {
                    "id":
                        rec.id,

                    "name":
                        rec.display_name,

                    "category_id":
                        rec.category_id.id
                        or False,

                    "location":
                        rec.location or "",
                }
                for rec in equipments
            ],

            "locations":
                locations,

            "severities": [
                {
                    "value": "low",
                    "label": "Low",
                },
                {
                    "value": "medium",
                    "label": "Medium",
                },
                {
                    "value": "high",
                    "label": "High",
                },
                {
                    "value": "critical",
                    "label": "Critical",
                },
            ],

            "operational_statuses": [
                {
                    "value":
                        "active",

                    "label":
                        "Active",
                },
                {
                    "value":
                        "maintenance",

                    "label":
                        "Under Maintenance",
                },
                {
                    "value":
                        "out_of_service",

                    "label":
                        "Out of Service",
                },
            ],
        }

    # =========================================================
    # Failure severity
    # =========================================================

    @api.model
    def _severity_counts(
        self,
        domain,
        Line,
    ):

        result = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0,
        }

        grouped = Line._read_group(
            domain,
            [
                "failure_severity",
            ],
            [
                "__count",
            ],
        )

        for severity, count in grouped:

            if severity in result:
                result[
                    severity
                ] = count

        result["total"] = sum(
            result.values()
        )

        return result

    # =========================================================
    # Top defects
    # =========================================================

    @api.model
    def _top_defects(
        self,
        domain,
        Line,
    ):

        rows = []

        grouped = Line._read_group(
            domain,
            [
                "question_id",
            ],
            [
                "__count",
            ],
            order="__count desc",
            limit=10,
        )

        for question, count in grouped:

            if question:

                rows.append({
                    "id":
                        question.id,

                    "name":
                        question.display_name,

                    "count":
                        count,
                })

        return rows

    # =========================================================
    # Failures by category
    # =========================================================

    @api.model
    def _category_failures(
        self,
        report_domain,
        Report,
    ):

        rows = []

        grouped = Report._read_group(

            report_domain
            + [
                (
                    "has_issue",
                    "=",
                    True,
                )
            ],

            [
                "category_id",
            ],

            [
                "__count",
            ],

            order="__count desc",

            limit=10,
        )

        for category, count in grouped:

            if category:

                rows.append({
                    "id":
                        category.id,

                    "name":
                        category.display_name,

                    "count":
                        count,
                })

        return rows

    # =========================================================
    # Failures by location
    # =========================================================

    @api.model
    def _location_failures(
        self,
        report_domain,
        Report,
    ):

        counts = defaultdict(int)

        grouped = Report._read_group(

            report_domain
            + [
                (
                    "has_issue",
                    "=",
                    True,
                )
            ],

            [
                "equipment_id",
            ],

            [
                "__count",
            ],
        )

        for equipment, count in grouped:

            location = (
                equipment.location
                or "Unspecified"
            ).strip()

            if not location:
                location = "Unspecified"

            counts[
                location
            ] += count

        sorted_rows = sorted(
            counts.items(),
            key=lambda item:
                item[1],
            reverse=True,
        )

        return [
            {
                "name":
                    location,

                "count":
                    count,
            }
            for location, count
            in sorted_rows[:10]
        ]

    # =========================================================
    # Inspection trend
    # =========================================================

    @api.model
    def _inspection_trend(
        self,
        report_domain,
        Report,
        date_from,
        date_to,
    ):

        counts = defaultdict(int)

        reports = Report.search(
            report_domain
        )

        for report in reports:

            if report.report_date:

                local_dt = (
                    fields.Datetime
                    .context_timestamp(
                        report,
                        report.report_date,
                    )
                )

                counts[
                    local_dt.date()
                ] += 1

        total_days = (
            date_to
            - date_from
        ).days + 1

        if total_days <= 14:

            step = 1

        elif total_days <= 60:

            step = 7

        else:

            step = 30

        points = []

        cursor = date_from

        while cursor <= date_to:

            bucket_end = min(
                cursor
                + timedelta(
                    days=step - 1
                ),
                date_to,
            )

            bucket_days = (
                bucket_end
                - cursor
            ).days + 1

            count = sum(
                counts.get(
                    cursor
                    + timedelta(
                        days=offset
                    ),
                    0,
                )
                for offset
                in range(bucket_days)
            )

            label = (
                cursor.strftime(
                    "%d %b"
                )
            )

            points.append({
                "label":
                    label,

                "count":
                    count,
            })

            cursor = (
                bucket_end
                + timedelta(days=1)
            )

        return points[-18:]

    # =========================================================
    # Critical inspections table
    # =========================================================

    @api.model
    def _recent_critical(
        self,
        report_domain,
        Report,
    ):

        reports = Report.search(

            report_domain
            + [
                (
                    "has_critical_issue",
                    "=",
                    True,
                )
            ],

            order=(
                "report_date desc, "
                "id desc"
            ),

            limit=10,
        )

        rows = []

        for report in reports:

            critical_lines = (
                report.line_ids.filtered(
                    lambda line:
                    line.answer == "no"
                    and
                    line.failure_severity
                    == "critical"
                )
            )

            defects = ", ".join(
                critical_lines
                .mapped(
                    "question_id.name"
                )[:3]
            )

            rows.append({

                "id":
                    report.id,

                "name":
                    report.display_name,

                "equipment":
                    report
                    .equipment_id
                    .display_name,

                "category":
                    report
                    .category_id
                    .display_name
                    or "",

                "location":
                    report
                    .equipment_id
                    .location
                    or "",

                "defects":
                    defects,

                "inspector":
                    report
                    .user_id
                    .display_name,

                "date":
                    self._format_datetime(
                        report.report_date,
                        report,
                    ),

                "state":
                    report.state,
            })

        return rows

    # =========================================================
    # Equipment requiring attention
    # =========================================================

    @api.model
    def _equipment_attention(
        self,
        equipment_records,
    ):

        records = (
            equipment_records.filtered(
                lambda rec:
                rec.operational_status
                in (
                    "maintenance",
                    "out_of_service",
                )
            )
        )

        records = records.sorted(
            key=lambda rec: (
                rec.operational_status
                != "out_of_service",

                rec.name or "",
            )
        )[:10]

        return [

            {
                "id":
                    rec.id,

                "name":
                    rec.display_name,

                "category":
                    rec
                    .category_id
                    .display_name
                    or "",

                "location":
                    rec.location or "",

                "status":
                    rec.operational_status,

                "last_inspection":
                    self._format_datetime(
                        rec.last_report_date,
                        rec,
                    ),

                "open_maintenance":
                    rec.maintenance_open_count,
            }

            for rec in records
        ]

    # =========================================================
    # Overdue spare parts table
    # =========================================================

    @api.model
    def _overdue_parts_rows(
        self,
        overdue_parts,
        today,
    ):

        parts = overdue_parts.sorted(
            key=lambda part:
                part.next_maintenance_date
                or today
        )[:10]

        return [

            {
                "id":
                    part.id,

                "name":
                    part.display_name,

                "equipment":
                    part
                    .equipment_id
                    .display_name,

                "category":
                    part
                    .category_id
                    .display_name
                    or "",

                "last_date":
                    (
                        fields.Date
                        .to_string(
                            part
                            .last_maintenance_date
                        )
                        if
                        part.last_maintenance_date
                        else ""
                    ),

                "next_date":
                    (
                        fields.Date
                        .to_string(
                            part
                            .next_maintenance_date
                        )
                        if
                        part.next_maintenance_date
                        else ""
                    ),

                "days_overdue":
                    (
                        today
                        - part
                        .next_maintenance_date
                    ).days
                    if
                    part.next_maintenance_date
                    else 0,
            }

            for part in parts
        ]

    # =========================================================
    # Maintenance table
    # =========================================================

    @api.model
    def _recent_maintenance(
        self,
        maintenance_domain,
        Maintenance,
    ):

        requests = Maintenance.search(
            maintenance_domain,
            order=(
                "request_date desc, "
                "id desc"
            ),
            limit=10,
        )

        return [

            {
                "id":
                    req.id,

                "name":
                    req.display_name,

                "equipment":
                    (
                        req
                        .equipment_id
                        .display_name
                        if req.equipment_id
                        else ""
                    ),

                "inspection":
                    (
                        req
                        .inspection_report_id
                        .display_name
                        if
                        req.inspection_report_id
                        else ""
                    ),

                "severity":
                    (
                        req
                        .inspection_failure_severity
                        or ""
                    ),

                "stage":
                    (
                        req
                        .stage_id
                        .display_name
                        or ""
                    ),

                "technician":
                    (
                        req
                        .user_id
                        .display_name
                        if req.user_id
                        else "Unassigned"
                    ),

                "priority":
                    req.priority or "0",
            }

            for req in requests
        ]

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _to_int(value):

        try:

            return (
                int(value)
                if value
                not in (
                    None,
                    False,
                    "",
                    0,
                    "0",
                )
                else False
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    @staticmethod
    def _to_date(value):

        if not value:
            return False

        try:

            return fields.Date.to_date(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

    @staticmethod
    def _percent(
        numerator,
        denominator,
    ):

        if not denominator:
            return 0.0

        return round(
            (
                numerator
                / denominator
            )
            * 100,
            1,
        )

    @staticmethod
    def _datetime_domain(
        field_name,
        date_from,
        date_to,
    ):

        start_dt = datetime.combine(
            date_from,
            time.min,
        )

        end_dt = datetime.combine(
            date_to
            + timedelta(days=1),
            time.min,
        )

        return [
            (
                field_name,
                ">=",
                fields.Datetime
                .to_string(
                    start_dt
                ),
            ),
            (
                field_name,
                "<",
                fields.Datetime
                .to_string(
                    end_dt
                ),
            ),
        ]

    @staticmethod
    def _date_domain(
        field_name,
        date_from,
        date_to,
    ):

        return [
            (
                field_name,
                ">=",
                fields.Date.to_string(
                    date_from
                ),
            ),
            (
                field_name,
                "<=",
                fields.Date.to_string(
                    date_to
                ),
            ),
        ]

    @staticmethod
    def _format_datetime(
        value,
        record,
    ):

        if not value:
            return ""

        local_dt = (
            fields.Datetime
            .context_timestamp(
                record,
                value,
            )
        )

        return local_dt.strftime(
            "%Y-%m-%d %H:%M"
        )