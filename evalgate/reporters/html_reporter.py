"""
Self-contained interactive HTML Evaluation Scorecard for EvalGate.
"""
import html
import datetime
from ..core.models import SuiteSummary


def generate_html_report(summary: SuiteSummary) -> str:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    gate_cls = "gate-pass" if summary.passed_gate else "gate-fail"
    gate_label = "CI GATE PASSED" if summary.passed_gate else "CI GATE BLOCKED"
    mock_banner = (
        '<div class="mock-banner">⚠ Provider = <strong>mock</strong>：本报告使用预置的演示回答，用于展示断言与报告格式，'
        '<strong>不代表任何真实模型的表现</strong>。真实评测请使用 <code>--provider http</code>。'
        f' 另有 {summary.skipped_assertions} 条断言因未配置裁判模型被跳过。</div>'
        if summary.provider == "mock"
        else ""
    )

    rows_html = []
    for idx, r in enumerate(summary.results):
        badge_cls = "badge-pass" if r.passed else "badge-fail"
        badge_txt = "PASS" if r.passed else "FAIL"
        tags_html = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in r.tags)
        assertions_html = []
        for ar in r.assertion_results:
            if ar.skipped:
                a_cls, a_icon = "ar-skip", "–"
            else:
                a_cls = "ar-pass" if ar.passed else "ar-fail"
                a_icon = "✓" if ar.passed else "✕"
            assertions_html.append(
                f'<div class="ar-row {a_cls}">'
                f'<span class="ar-icon">{a_icon}</span>'
                f'<span class="ar-type">{html.escape(ar.type.value)}</span>'
                f'<span class="ar-score">score={ar.score:.2f}</span>'
                f'<span class="ar-msg">{html.escape(ar.message)}</span>'
                f'</div>'
            )

        rows_html.append(f"""
        <div class="case-card" data-status="{'pass' if r.passed else 'fail'}">
          <div class="case-header" onclick="toggleDetail('detail-{idx}')">
            <div class="case-left">
              <span class="badge {badge_cls}">{badge_txt}</span>
              <span class="case-id">{html.escape(r.case_id)}</span>
              <span class="case-desc">{html.escape(r.description)}</span>
              {tags_html}
            </div>
            <div class="case-right">
              <span class="metric-pill">Score: <strong>{r.score:.2f}</strong></span>
              <span class="metric-pill">{r.latency_ms:.1f} ms</span>
              <span class="chevron">▾</span>
            </div>
          </div>
          <div class="case-detail" id="detail-{idx}">
            <div class="io-grid">
              <div class="io-box">
                <div class="io-title">PROMPT INPUT</div>
                <pre>{html.escape(r.prompt)}</pre>
              </div>
              <div class="io-box">
                <div class="io-title">MODEL RESPONSE</div>
                <pre>{html.escape(r.response or r.error or '')}</pre>
              </div>
            </div>
            <div class="assertions-block">
              <div class="io-title">DETERMINISTIC ASSERTIONS &amp; SAFETY TELEMETRY</div>
              {''.join(assertions_html)}
            </div>
          </div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EvalGate Scorecard — {html.escape(summary.suite_name)}</title>
<style>
  :root {{
    --bg: #09090b; --card: #121215; --border: #27272a; --text: #fafafa;
    --muted: #a1a1aa; --pass: #10b981; --fail: #ef4444; --accent: #3b82f6;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; padding: 32px 20px; }}
  .container {{ max-width: 1080px; margin: 0 auto; }}
  .topbar {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 28px; flex-wrap: wrap; }}
  .brand {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); font-weight: 600; }}
  h1 {{ font-size: 24px; font-weight: 700; margin-top: 4px; letter-spacing: -0.02em; }}
  .meta {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .gate-banner {{ padding: 10px 18px; border-radius: 999px; font-size: 13px; font-weight: 700; letter-spacing: 0.04em; border: 1px solid; }}
  .gate-pass {{ background: rgba(16,185,129,0.12); color: #34d399; border-color: rgba(16,185,129,0.35); }}
  .gate-fail {{ background: rgba(239,68,68,0.12); color: #f87171; border-color: rgba(239,68,68,0.35); }}
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 24px; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; }}
  .kpi-label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }}
  .kpi-val {{ font-size: 28px; font-weight: 700; margin-top: 6px; font-variant-numeric: tabular-nums; }}
  .kpi-sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .filters {{ display: flex; gap: 8px; margin-bottom: 16px; }}
  .filter-btn {{ background: var(--card); color: var(--muted); border: 1px solid var(--border); padding: 6px 14px; border-radius: 8px; font-size: 13px; cursor: pointer; font-weight: 500; }}
  .filter-btn.active {{ background: #fafafa; color: #09090b; border-color: #fafafa; }}
  .case-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 10px; overflow: hidden; }}
  .case-header {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; cursor: pointer; gap: 12px; flex-wrap: wrap; }}
  .case-header:hover {{ background: rgba(255,255,255,0.02); }}
  .case-left {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
  .case-right {{ display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); }}
  .badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.04em; }}
  .badge-pass {{ background: rgba(16,185,129,0.15); color: #34d399; }}
  .badge-fail {{ background: rgba(239,68,68,0.15); color: #f87171; }}
  .case-id {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; font-weight: 600; color: #e4e4e7; }}
  .case-desc {{ font-size: 14px; color: #d4d4d8; }}
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 999px; background: #1f1f23; color: #a1a1aa; border: 1px solid #2e2e34; }}
  .metric-pill {{ background: #18181b; border: 1px solid var(--border); padding: 3px 9px; border-radius: 6px; font-variant-numeric: tabular-nums; }}
  .case-detail {{ display: none; border-top: 1px solid var(--border); padding: 16px 18px; background: #0d0d10; }}
  .case-detail.open {{ display: block; }}
  .io-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }}
  @media (max-width: 720px) {{ .io-grid {{ grid-template-columns: 1fr; }} }}
  .io-box {{ background: #141418; border: 1px solid var(--border); border-radius: 8px; padding: 12px; }}
  .io-title {{ font-size: 11px; font-weight: 700; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 8px; }}
  pre {{ white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12.5px; color: #e4e4e7; }}
  .ar-row {{ display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 8px; font-size: 13px; margin-top: 6px; border: 1px solid; }}
  .ar-pass {{ background: rgba(16,185,129,0.06); border-color: rgba(16,185,129,0.2); }}
  .ar-fail {{ background: rgba(239,68,68,0.08); border-color: rgba(239,68,68,0.28); }}
  .ar-skip {{ background: rgba(161,161,170,0.06); border-color: rgba(161,161,170,0.25); color: #a1a1aa; }}
  .mock-banner {{ margin-bottom: 18px; padding: 10px 14px; border-radius: 10px; font-size: 13px; background: rgba(234,179,8,0.10); border: 1px solid rgba(234,179,8,0.35); color: #fde68a; }}
  .ar-type {{ font-family: ui-monospace, monospace; font-size: 12px; font-weight: 600; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; }}
  .ar-score {{ font-family: ui-monospace, monospace; font-size: 12px; color: var(--muted); }}
</style>
</head>
<body>
<div class="container">
  <div class="topbar">
    <div>
      <div class="brand">EvalGate · Deterministic AI Quality &amp; Red-Team Harness</div>
      <h1>{html.escape(summary.suite_name)}</h1>
      <div class="meta">{html.escape(summary.gate_reason)} · Generated {now_str}</div>
    </div>
    <div class="gate-banner {gate_cls}">{gate_label}</div>
  </div>

  {mock_banner}

  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">Pass Rate</div>
      <div class="kpi-val">{summary.pass_rate*100:.1f}%</div>
      <div class="kpi-sub">{summary.passed_cases} / {summary.total_cases} deterministic scenarios passed</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Composite Score</div>
      <div class="kpi-val">{summary.avg_score:.3f}</div>
      <div class="kpi-sub">Groundedness + Schema + Safety</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Mean Latency</div>
      <div class="kpi-val">{summary.avg_latency_ms:.1f} ms</div>
      <div class="kpi-sub">End-to-end provider completion</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Failed / Blocked</div>
      <div class="kpi-val" style="color: {'#f87171' if summary.failed_cases else '#34d399'}">{summary.failed_cases}</div>
      <div class="kpi-sub">Zero tolerance for Red-Team leaks</div>
    </div>
  </div>

  <div class="filters">
    <button class="filter-btn active" onclick="filterCases('all', this)">All ({summary.total_cases})</button>
    <button class="filter-btn" onclick="filterCases('pass', this)">Passed ({summary.passed_cases})</button>
    <button class="filter-btn" onclick="filterCases('fail', this)">Failed ({summary.failed_cases})</button>
  </div>

  <div id="cases-list">
    {''.join(rows_html)}
  </div>
</div>
<script>
  function toggleDetail(id) {{
    document.getElementById(id).classList.toggle('open');
  }}
  function filterCases(status, btn) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.case-card').forEach(c => {{
      c.style.display = (status === 'all' || c.dataset.status === status) ? 'block' : 'none';
    }});
  }}
  // Open first failed or first card automatically
  const firstFail = document.querySelector('.case-card[data-status="fail"] .case-detail');
  if (firstFail) firstFail.classList.add('open');
  else {{
    const first = document.querySelector('.case-detail');
    if (first) first.classList.add('open');
  }}
</script>
</body>
</html>"""
