const app = document.getElementById("app");
const runtime = { cases: [], current: null, mode: "replay", round: 0, result: null, crm: null, events: [] };

const esc = (value) => String(value ?? "").replace(/[&<>\"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" }[char]));
const pretty = (value) => typeof value === "object" ? JSON.stringify(value, null, 2) : String(value ?? "未知");
const currentCase = () => runtime.cases.find((item) => item.id === runtime.current) || runtime.cases[0];

async function api(path, body, method = "POST") {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  const data = await response.json();
  if (!response.ok && !data.status) throw new Error(data.detail || data.error || `HTTP ${response.status}`);
  return data;
}

function factRows(caseData) {
  const facts = Object.entries(caseData?.facts || {});
  const unknowns = caseData?.unknowns || [];
  return `
    <div class="section-label">客户事实 / CRM 已知</div>
    <div class="fact-grid">${facts.map(([key, value]) => `<div class="fact"><span>${esc(key)}</span><strong>${esc(Array.isArray(value) ? value.join("、") : value)}</strong><em>客户事实</em></div>`).join("")}</div>
    <div class="section-label unknown-label">未知信息（不允许模型补写）</div>
    <div class="chips">${unknowns.map((item) => `<span class="chip unknown">${esc(item)}</span>`).join("")}</div>`;
}

function answerRows(answers) {
  if (!answers) return `<div class="empty">尚未判断。选择案例并点击“重新判断”。</div>`;
  const labels = { intent: "需求意图", lead_stage: "线索阶段", objection: "主要异议", next_action: "下一动作", high_value_lead: "高价值线索", human_needed: "需要人工", do_not_contact: "禁联判断", appointment_confirmed: "预约已确认" };
  return Object.entries(answers).map(([key, value]) => {
    const chosen = value.choice ?? (value.noul !== undefined ? (Number(value.noul) >= 0.7 ? "是" : "否") : value.score);
    const conf = value.confidence === undefined ? (value.noul === undefined ? "—" : Number(value.noul).toFixed(2)) : Number(value.confidence).toFixed(2);
    const risk = key === "human_needed" || key === "do_not_contact" || (value.confidence !== undefined && value.confidence < 0.45);
    return `<div class="answer-row ${risk ? "risk" : ""}"><span>${esc(labels[key] || key)}</span><strong>${esc(chosen)}</strong><small>置信度/概率 ${esc(conf)}</small></div>`;
  }).join("");
}

function telemetry(result) {
  const decision = result?.decision;
  if (!decision) return `<div class="empty">无请求元数据</div>`;
  return `<div class="telemetry">
    <div><span>模式</span><strong class="${decision.mode === "live" ? "live-text" : "replay-text"}">${decision.mode === "live" ? "LIVE · 真实 Jev" : "REPLAY · 固定案例"}</strong></div>
    <div><span>模型</span><strong>${esc(decision.model || "未知")}</strong></div>
    <div><span>请求 ID</span><strong>${esc(decision.request_id || "unavailable")}</strong></div>
    <div><span>延迟</span><strong>${esc(decision.latency_ms ?? "—")} ms</strong></div>
    <div><span>输入绑定</span><strong>${esc(decision.input_fingerprint || "—")}</strong></div>
  </div>`;
}

function proposalCard(proposal, withActions = true) {
  if (!proposal) return `<div class="empty">等待模型判断后生成策略卡。</div>`;
  const blocked = proposal.blocked_outreach;
  const canApprove = proposal.allowed_on_explicit_human_approval && !blocked;
  return `<div class="proposal ${blocked ? "blocked" : "pending"}">
    <div class="proposal-head"><span class="badge ${blocked ? "red" : "amber"}">${esc(proposal.action_band)}</span><strong>${esc(proposal.action)}</strong></div>
    <p>${esc(proposal.reason)}</p>
    <div class="policy-grid"><span>最小 Choice 置信度 <b>${Number(proposal.choice_min_confidence).toFixed(2)}</b></span><span>人工接管 <b>${proposal.human_needed ? "是" : "否"}</b></span><span>CRM 写入 <b>${proposal.crm_mutation ? "已写入" : "未写入"}</b></span></div>
    ${withActions ? `<div class="actions">
      <button id="approve" ${canApprove ? "" : "disabled"}>人工确认客户已明确同意到店 → 写入测试 CRM</button>
      <button id="reject" class="secondary">拒绝推进</button>
    </div>` : ""}
    <small>决策 ${esc(proposal.decision_id)} · epoch ${esc(proposal.epoch)} · revision ${esc(proposal.revision)}</small>
  </div>`;
}

function crmCard(crm) {
  const record = crm?.records?.["lead-zhang"];
  if (!record) return `<div class="empty">暂无 CRM 读回</div>`;
  return `<div class="crm-readback">
    <div><span>测试 CRM 客户</span><strong>${esc(record.name)}</strong></div>
    <div><span>阶段</span><strong>${esc(record.stage)}</strong></div>
    <div><span>预约状态</span><strong>${record.appointment ? esc(record.appointment.status) : "未写入"}</strong></div>
    <div><span>禁联</span><strong>${record.do_not_contact ? "是" : "否"}</strong></div>
    <div class="full"><span>独立读回备注</span><pre>${esc(record.notes.join("\n") || "暂无")}</pre></div>
    <div class="full"><span>独立读回跟进</span><pre>${esc(JSON.stringify(record.followups, null, 2))}</pre></div>
  </div>`;
}

function render() {
  const item = currentCase();
  if (!item) return;
  const result = runtime.result;
  const error = result?.status === "live_error" ? `<div class="error"><b>Live 请求失败，未降级：</b> ${esc(result.error_type)} / HTTP ${esc(result.http_status ?? "network")}</div>` : "";
  const status = result?.status === "ok" ? `<div class="success">本轮已完成判断；策略层未把客户意向自动写成预约。</div>` : "";
  app.innerHTML = `
    <header class="topbar"><div><div class="eyebrow">模拟销售场景 · 真实模型调用 · 测试 CRM 执行</div><h1>远航汽车 · 销售副驾驶挑战台</h1><p>把客户对话转成可核验跟进动作；未确认、拒绝或不确定时，阻止错误推进。</p></div><div class="top-actions"><span class="mode-pill ${runtime.mode === "live" ? "live" : "replay"}">${runtime.mode === "live" ? "LIVE · 真实 Jev" : "REPLAY · 可重复"}</span><select id="mode"><option value="replay" ${runtime.mode === "replay" ? "selected" : ""}>Replay：固定案例</option><option value="live" ${runtime.mode === "live" ? "selected" : ""}>Live：真实 Jev 请求</option></select><button id="reset" class="secondary">一键重置</button></div></header>
    <div class="notice"><b>边界声明：</b>这是模拟销售场景；Live 才会请求真实 Jev；所有 CRM 写入都是测试 CRM；没有真实预约系统，不声称预约成功。</div>
    ${error}${status}
    <main class="workbench">
      <section class="panel customer-panel"><div class="panel-title"><h2>1 · 客户对话</h2><span class="badge blue">输入事实</span></div><label class="case-label">预标注案例<select id="case">${runtime.cases.map((c) => `<option value="${esc(c.id)}" ${c.id === item.id ? "selected" : ""}>${esc(c.category)} · ${esc(c.title)}</option>`).join("")}</select></label><textarea id="message" aria-label="客户消息">${esc(item.message)}</textarea><div class="button-row"><button id="evaluate">重新判断本轮</button><span class="muted">round ${runtime.round || "—"} · 每轮输入独立绑定</span></div><div class="facts">${factRows(item)}</div></section>
      <section class="panel assistant-panel"><div class="panel-title"><h2>2 · 销售辅助卡</h2><span class="badge purple">模型推断</span></div>${telemetry(result)}<div class="answer-list">${answerRows(result?.decision?.answers)}</div><div class="panel-title sub"><h3>策略层输出</h3><span class="badge amber">概率不能越权</span></div>${proposalCard(result?.proposal, false)}</section>
      <section class="panel approval-panel"><div class="panel-title"><h2>3 · 待办 / 审批</h2><span class="badge amber">人工门禁</span></div><div class="approval-rules"><div>✓ 客户明确确认前：不写已预约</div><div>✓ 明确拒绝/禁联：阻止外呼</div><div>✓ 过时结果：丢弃，不写 CRM</div><div>✓ 网络失败：可见，不降级 Replay</div></div><div id="approval-card">${proposalCard(result?.proposal)}</div></section>
      <section class="panel crm-panel"><div class="panel-title"><h2>4 · CRM 独立读回</h2><span class="badge green">测试 CRM</span></div>${crmCard(runtime.crm)}<button id="readback" class="secondary">重新读取测试 CRM</button></section>
      <section class="panel audit-panel"><div class="panel-title"><h2>挑战记录</h2><span class="badge gray">可核验事件</span></div><div class="event-list">${(runtime.events || []).slice().reverse().map((event) => `<div class="event"><code>${esc(event.event)}</code><span>${esc(JSON.stringify(event))}</span></div>`).join("") || '<div class="empty">暂无事件</div>'}</div></section>
    </main>`;
  document.getElementById("mode").onchange = (event) => { runtime.mode = event.target.value; render(); };
  document.getElementById("case").onchange = async (event) => { const state = await api("/api/reset", { case_id: event.target.value }); syncState(state); render(); };
  document.getElementById("reset").onclick = async () => { const state = await api("/api/reset", { case_id: item.id }); syncState(state); render(); };
  document.getElementById("evaluate").onclick = evaluate;
  document.getElementById("readback").onclick = async () => { const data = await api("/api/crm", null, "GET"); runtime.crm = data.crm; render(); };
  const approve = document.getElementById("approve");
  if (approve) approve.onclick = () => approveProposal(true);
  const reject = document.getElementById("reject");
  if (reject) reject.onclick = () => approveProposal(false, true);
}

function syncState(state) {
  runtime.current = state.current_case_id;
  runtime.crm = state.crm;
  runtime.result = state.last_decision && state.last_proposal ? { status: "ok", decision: state.last_decision, proposal: state.last_proposal, crm: state.crm } : null;
  runtime.events = state.events || [];
}

async function evaluate() {
  const item = currentCase();
  const message = document.getElementById("message").value;
  runtime.round += 1;
  runtime.result = null;
  render();
  try {
    runtime.result = await api("/api/evaluate", { mode: runtime.mode, case_id: item.id, message, round_id: `${runtime.mode}-${runtime.round}` });
    runtime.crm = runtime.result.crm || runtime.crm;
    const state = await api("/api/state", null, "GET");
    runtime.events = state.events || [];
  } catch (error) {
    runtime.result = { status: "live_error", error_type: error.message, http_status: "client" };
  }
  render();
}

async function approveProposal(confirm, reject = false) {
  const proposal = runtime.result?.proposal;
  if (!proposal) return;
  const endpoint = reject ? "/api/reject" : "/api/approve";
  const body = reject ? { decision_id: proposal.decision_id } : { decision_id: proposal.decision_id, customer_confirmed: confirm, idempotency_key: `${proposal.decision_id}-human-confirmation`, epoch: proposal.epoch, revision: proposal.revision };
  const result = await api(endpoint, body);
  runtime.crm = result.crm;
  const state = await api("/api/state", null, "GET");
  runtime.events = state.events || [];
  runtime.result.approval = result;
  render();
}

(async function init() {
  const cases = await api("/api/cases", null, "GET");
  runtime.cases = cases.cases;
  const state = await api("/api/state", null, "GET");
  runtime.mode = state.mode;
  runtime.current = state.current_case_id;
  runtime.crm = state.crm;
  runtime.events = state.events || [];
  render();
})();
