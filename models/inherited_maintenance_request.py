from odoo import api, fields, models


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"

    is_inspection_generated = fields.Boolean(
        string="Generated from Inspection",
        compute="_compute_is_inspection_generated",
        store=True,
        index=True,
        copy=False,
    )

    inspection_line_id = fields.Many2one(
        comodel_name="equipment.daily.report.line",
        string="Inspection Failure",
        ondelete="set null",
        index=True,
        copy=False,
        tracking=True,
        help="The failed checklist line that generated this maintenance request.",
    )

    inspection_report_id = fields.Many2one(
        comodel_name="equipment.daily.report",
        string="Inspection Report",
        related="inspection_line_id.report_id",
        store=True,
        readonly=True,
        index=True,
    )

    inspection_question_id = fields.Many2one(
        comodel_name="equipment.checklist.question",
        string="Failed Question",
        related="inspection_line_id.question_id",
        store=True,
        readonly=True,
        index=True,
    )

    inspection_failure_severity = fields.Selection(
        related="inspection_line_id.failure_severity",
        string="Failure Severity",
        store=True,
        readonly=True,
        index=True,
    )

    inspection_issue_description = fields.Text(
        string="Inspection Issue Description",
        related="inspection_line_id.issue_description",
        readonly=True,
    )

    inspection_image = fields.Image(
        string="Inspection Issue Photo",
        related="inspection_line_id.issue_image",
        readonly=True,
    )

    inspection_report_count = fields.Integer(
        string="Inspection Count",
        compute="_compute_inspection_report_count",
    )

    @api.depends("inspection_line_id")
    def _compute_is_inspection_generated(self):
        for request in self:
            request.is_inspection_generated = bool(request.inspection_line_id)

    def action_open_inspection_report(self):
        self.ensure_one()

        if not self.inspection_report_id:
            return False

        return {
            "type": "ir.actions.act_window",
            "name": "Daily Inspection",
            "res_model": "equipment.daily.report",
            "view_mode": "form",
            "res_id": self.inspection_report_id.id,
            "target": "current",
        }

    _sql_constraints = [
        (
            "inspection_line_unique",
            "unique(inspection_line_id)",
            "A maintenance request already exists for this inspection failure.",
        ),
    ]

    @api.depends("inspection_report_id")
    def _compute_inspection_report_count(self):
        for request in self:
            request.inspection_report_count = (
                1 if request.inspection_report_id else 0
            )