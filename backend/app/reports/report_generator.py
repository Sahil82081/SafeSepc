"""Automotive Safety & Verification Report Generator (Rule 9).

Generates both comprehensive Markdown and formatted PDF compliance reports:
- ISO 26262 ASIL risk assessment breakdown
- Z3 formal verification proofs and conflicts with counter-examples
- Deterministic simulation test results and coverage metrics
- Mutation testing scores
- Human engineering sign-off records and audit trail
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import pymupdf

from backend.app.config import REPORTS_DIR


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Generate structured markdown compliance report from run data."""
    run_id = data.get("run_id", "RUN-UNKNOWN")
    created_at = data.get("created_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ecu_version = data.get("ecu_version", "v1")
    reqs = data.get("requirements", [])
    formalized = data.get("formalized", [])
    conflicts = data.get("conflicts", [])
    tests = data.get("test_cases", [])
    results = data.get("test_results", [])
    diagnosis = data.get("diagnosis_report") or {}
    risk = data.get("risk_assessment") or {}
    approvals = data.get("approvals", [])

    passed_count = sum(1 for r in results if r.get("passed"))
    failed_count = len(results) - passed_count
    pass_rate = round((passed_count / len(results)) * 100, 1) if results else 100.0

    lines = [
        "# SafeSpec Formal Verification & Safety Report",
        f"**Run ID**: `{run_id}` | **Date**: `{created_at}` | **Target ECU Version**: `{ecu_version}`",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Total Requirements Ingested | {len(reqs)} |",
        f"| Successfully Formalized Rules | {len(formalized) - len(data.get('unformalizable', []))} |",
        f"| Unformalizable / Vague Requirements | {len(data.get('unformalizable', []))} |",
        f"| Z3 Formal Contradictions / Conflicts | {len(conflicts)} |",
        f"| Total Simulation Tests Run | {len(results)} |",
        f"| Tests Passed | {passed_count} |",
        f"| Tests Failed | {failed_count} |",
        f"| Overall Simulation Pass Rate | {pass_rate}% |",
        f"| Safety Risk Level | {risk.get('level', 'LOW')} ({risk.get('score', 0)}/100) |",
        f"| Human Sign-off Required | {'YES (ASIL C/D or High Risk)' if risk.get('requires_human_signoff') else 'NO'} |",
        "",
        "---",
        "",
        "## 2. ISO 26262 ASIL & Functional Safety Assessment",
        "",
        f"- **ASIL Classification**: {risk.get('asil', 'QM')}",
        f"- **Component Criticality**: {risk.get('criticality', 'DOOR')}",
        f"- **Risk Assessment Summary**: {risk.get('summary', 'Standard automated safety verification criteria satisfied.')}",
        "",
        "---",
        "",
        "## 3. Z3 SMT Formal Verification Proofs & Conflicts",
        "",
    ]

    if conflicts:
        lines.append(f"⚠️ **{len(conflicts)} formal conflict(s) detected by Z3 SMT solver:**")
        lines.append("")
        for idx, c in enumerate(conflicts, 1):
            rule_a = c.get("rule_a_id", "A")
            rule_b = c.get("rule_b_id", "B")
            lines.append(f"### Conflict {idx}: `{c.get('id', f'CONF-{idx}')}` ({rule_a} vs {rule_b})")
            lines.append(f"- **Description**: {c.get('description')}")
            lines.append(f"- **Counter-Example State**: `{c.get('counter_example')}`")
            lines.append("")
    else:
        lines.append("✅ **No formal contradictions detected.** All approved rules are mathematically consistent.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 4. Virtual ECU Simulation Results",
        "",
        "| Test ID | Requirement | Inputs | Expected | Actual | Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for res in results[:15]:
        tid = res.get("test_id", "")
        req_id = res.get("requirement_id", "")
        inputs = str(res.get("inputs", {}))
        exp = str(res.get("expected_value", ""))
        act = str(res.get("actual_value", ""))
        status = "✅ PASS" if res.get("passed") else "❌ FAIL"
        lines.append(f"| `{tid}` | `{req_id}` | `{inputs}` | `{exp}` | `{act}` | {status} |")

    if len(results) > 15:
        lines.append(f"| ... | ... | *(and {len(results) - 15} more test cases)* | ... | ... | ... |")

    lines.append("")

    if diagnosis and diagnosis.get("root_cause"):
        lines.extend([
            "---",
            "",
            "## 5. Root Cause Analysis & Automated ECU Fix",
            "",
            f"- **Initial Buggy Version**: `{diagnosis.get('initial_version')}`",
            f"- **Root Cause Identified**: {diagnosis.get('root_cause')}",
            f"- **Proposed Immutable Version**: `{diagnosis.get('proposed_version')}`",
            f"- **Full Regression Verification**: {'Passed 100%' if diagnosis.get('regression_passed') else 'Failed'}",
            f"- **Mutation Analysis Score**: {diagnosis.get('mutation_score', 0)}%",
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 6. Human Engineering Approvals (Rule 9)",
        "",
    ])

    if approvals:
        for app in approvals:
            lines.append(f"- **{app.get('id')}** ({app.get('req_id')}): status=`{app.get('status')}` by `{app.get('decided_by', 'pending')}`")
            if app.get("decision_note"):
                lines.append(f"  * Note: {app.get('decision_note')}")
    else:
        lines.append("No manual sign-offs required or logged for this cycle.")

    lines.extend([
        "",
        "---",
        "*Report automatically generated by SafeSpec Autonomous Verification Engine.*",
    ])

    return "\n".join(lines)


def generate_pdf_report(markdown_text: str, output_path: Path) -> Path:
    doc = pymupdf.open()
    margin_x = 50.0
    margin_y = 50.0
    page_width = 595.0
    page_height = 842.0

    lines = markdown_text.splitlines()
    page = doc.new_page(width=page_width, height=page_height)
    current_y = margin_y

    for line in lines:
        if current_y > page_height - margin_y:
            page = doc.new_page(width=page_width, height=page_height)
            current_y = margin_y

        clean = line.strip()
        if not clean:
            current_y += 10
            continue

        if clean.startswith("# "):
            font_size = 18
            text = clean.replace("# ", "")
            color = (0.1, 0.2, 0.5)
            current_y += 14
        elif clean.startswith("## "):
            font_size = 14
            text = clean.replace("## ", "")
            color = (0.15, 0.3, 0.6)
            current_y += 12
        elif clean.startswith("### "):
            font_size = 11
            text = clean.replace("### ", "")
            color = (0.2, 0.2, 0.2)
            current_y += 8
        elif clean.startswith("|"):
            font_size = 9
            text = clean
            color = (0.3, 0.3, 0.3)
            current_y += 4
        else:
            font_size = 9.5
            text = clean.replace("**", "").replace("`", "")
            color = (0.0, 0.0, 0.0)

        if len(text) > 95:
            text = text[:92] + "..."

        page.insert_text((margin_x, current_y), text, fontsize=font_size, color=color)
        current_y += font_size + 4

    doc.save(str(output_path))
    doc.close()
    return output_path


def create_verification_report(
    data: Dict[str, Any], output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    out_dir = output_dir if output_dir is not None else REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    run_id = data.get("run_id", f"RUN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    md_content = generate_markdown_report(data)

    md_path = out_dir / f"report_{run_id}.md"
    md_path.write_text(md_content, encoding="utf-8")

    pdf_path = out_dir / f"report_{run_id}.pdf"
    try:
        generate_pdf_report(md_content, pdf_path)
    except Exception:
        pdf_path = None

    return {
        "run_id": run_id,
        "markdown_content": md_content,
        "markdown_path": str(md_path),
        "pdf_path": str(pdf_path) if pdf_path and pdf_path.exists() else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
