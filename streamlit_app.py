"""Streamlit workspace for the Acme Support Copilot FastAPI service."""

from __future__ import annotations

import html
import os
import uuid
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from app.agent_graph import (
    build_support_graph,
    resume_approved_action,
    run_investigation,
)
from app.support_agent import (
    PolicyPassage,
    external_model_available,
    make_case_brief,
)

ORDER_STATUSES = ("placed", "shipped", "delivered", "returned", "refunded")
TICKET_STATUSES = ("open", "in_progress", "resolved", "closed")
TICKET_PRIORITIES = ("low", "medium", "high")
TICKET_CHANNELS = ("email", "chat", "whatsapp", "phone")
ORDER_NEXT = dict(zip(ORDER_STATUSES, ORDER_STATUSES[1:]))
DEFAULT_API_URL = os.getenv("ACME_API_URL", "http://127.0.0.1:8000")


@st.cache_resource(show_spinner=False)
def get_support_graph(api_url: str):
    return build_support_graph(api_url)


st.set_page_config(
    page_title="Acme Support Workspace",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #202b2a;
        --muted: #687472;
        --line: #dce2dc;
        --paper: #fbfcfa;
        --accent: #b94b32;
        --teal: #287c72;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stMainBlockContainer"] { max-width: 1480px; padding-top: 2rem; }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
    h1, h2, h3 { color: var(--ink); }
    h1 { font-family: Georgia, "Times New Roman", serif; font-weight: 500; }
    h2, h3 { font-weight: 600; }
    [data-testid="stMetric"] {
        border-top: 2px solid var(--teal);
        padding: .8rem 0 .25rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); }
    div.stButton > button[kind="primary"],
    div.stFormSubmitButton > button[kind="primary"] {
        background: var(--accent); border-color: var(--accent); color: white;
    }
    div.stButton > button, div.stFormSubmitButton > button { border-radius: 4px; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    .eyebrow {
        color: var(--teal); font-size: .72rem; font-weight: 700;
        letter-spacing: .12em; text-transform: uppercase; margin-bottom: .35rem;
    }
    .page-deck { color: var(--muted); margin-top: -.25rem; }
    .status-line { font-size: .85rem; color: var(--muted); }
    .data-bars { display: grid; gap: .55rem; margin: .4rem 0 1.25rem; }
    .data-bar-row {
        align-items: center; display: grid; gap: .75rem;
        grid-template-columns: minmax(6rem, 9rem) 1fr minmax(3.5rem, auto);
    }
    .data-bar-label { color: var(--muted); font-size: .86rem; }
    .data-bar-track { background: #e8ece7; height: .55rem; overflow: hidden; }
    .data-bar-fill { display: block; height: 100%; }
    .data-bar-value { color: var(--ink); font-size: .84rem; text-align: right; }
    .table-wrap { border: 1px solid var(--line); max-height: 34rem; overflow: auto; }
    .ops-table { border-collapse: collapse; font-size: .88rem; width: 100%; }
    .ops-table th {
        background: #eef1ec; color: var(--muted); font-size: .72rem;
        letter-spacing: .06em; position: sticky; text-align: left;
        text-transform: uppercase; top: 0; z-index: 1;
    }
    .ops-table th, .ops-table td { border-bottom: 1px solid var(--line); padding: .65rem .75rem; }
    .ops-table tr:last-child td { border-bottom: 0; }
    .table-note { color: var(--muted); font-size: .8rem; margin: .4rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


class APIError(Exception):
    """An error returned by or while connecting to the FastAPI service."""


def api_request(base_url: str, method: str, path: str, **kwargs):
    try:
        response = requests.request(
            method, f"{base_url.rstrip('/')}{path}", timeout=15, **kwargs
        )
    except requests.RequestException as exc:
        raise APIError(
            f"Could not connect to the backend at {base_url}: {exc}"
        ) from exc

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise APIError(f"{response.status_code}: {detail}")
    return response.json()


def load_all(base_url: str, path: str, params: dict | None = None) -> pd.DataFrame:
    records = []
    total = None
    for page_number in range(1, 1001):
        payload = api_request(
            base_url,
            "GET",
            path,
            params={**(params or {}), "page": page_number, "page_size": 100},
        )
        records.extend(payload["items"])
        total = payload["total"]
        if len(records) >= total or not payload["items"]:
            break
    return pd.DataFrame(records)


def show_table(frame: pd.DataFrame, column_order: list[str] | None = None) -> None:
    if frame.empty:
        st.info("No records match these filters.")
        return

    frame = frame.copy()
    if "created_at" in frame.columns:
        frame["created_at"] = pd.to_datetime(frame["created_at"], format="mixed")
    columns = column_order or list(frame.columns)
    visible = frame.loc[:, columns]
    rows = []
    for row in visible.itertuples(index=False, name=None):
        cells = []
        for column, value in zip(columns, row):
            if pd.isna(value):
                text = ""
            elif column == "amount_inr":
                text = f"₹{float(value):,.2f}"
            elif column == "created_at":
                text = value.strftime("%d %b %Y, %H:%M")
            else:
                text = str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    headers = "".join(
        f"<th>{html.escape(column.replace('_', ' ').title())}</th>"
        for column in columns
    )
    table_markup = (
        "<div class='table-wrap'><table class='ops-table'><thead><tr>"
        f"{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    st.markdown(table_markup, unsafe_allow_html=True)
    if len(frame) > 100:
        st.markdown(
            f"<p class='table-note'>Showing all {len(frame):,} matching records.</p>",
            unsafe_allow_html=True,
        )
    st.download_button(
        "Download CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name="acme-records.csv",
        mime="text/csv",
        icon=":material/download:",
        key="download-" + str(len(columns)) + "-" + "-".join(columns),
    )


def render_bars(values: pd.Series, color: str, currency: bool = False) -> None:
    if values.empty:
        st.info("No data to display.")
        return

    maximum = max(float(value) for value in values)
    rows = []
    for label, value in values.items():
        numeric_value = float(value)
        width = numeric_value / maximum * 100 if maximum else 0
        label_text = html.escape(str(label).replace("_", " ").title())
        value_text = f"₹{numeric_value:,.0f}" if currency else f"{numeric_value:,.0f}"
        rows.append(
            "<div class='data-bar-row'>"
            f"<span class='data-bar-label'>{label_text}</span>"
            "<span class='data-bar-track'>"
            f"<span class='data-bar-fill' style='width:{width:.1f}%;background:{color}'></span>"
            "</span>"
            f"<b class='data-bar-value'>{value_text}</b>"
            "</div>"
        )
    st.markdown(f"<div class='data-bars'>{''.join(rows)}</div>", unsafe_allow_html=True)


def page_header(title: str, description: str) -> None:
    st.markdown(
        '<div class="eyebrow">Acme / Customer operations</div>', unsafe_allow_html=True
    )
    st.title(title)
    st.markdown(f'<p class="page-deck">{description}</p>', unsafe_allow_html=True)


def clear_and_refresh() -> None:
    st.cache_data.clear()
    st.rerun()


with st.sidebar:
    st.markdown("## ACME")
    st.caption("SUPPORT OPERATIONS")
    selected_page = st.radio(
        "Workspace",
        ["Overview", "Customers", "Orders", "Tickets", "Agent desk"],
        label_visibility="collapsed",
    )
    st.divider()
    backend_url = (
        st.text_input(
            "Backend URL",
            value=DEFAULT_API_URL,
            help="Set ACME_API_URL when running the UI in a separate container.",
        )
        .strip()
        .rstrip("/")
    )
    refresh_col, docs_col = st.columns(2)
    refresh_col.button(
        "Refresh",
        icon=":material/refresh:",
        use_container_width=True,
        on_click=clear_and_refresh,
    )
    docs_col.link_button(
        "API docs",
        f"{backend_url}/docs",
        icon=":material/open_in_new:",
        use_container_width=True,
    )
    try:
        health = api_request(backend_url, "GET", "/health")
        st.success(
            "Backend connected" if health.get("status") == "ok" else "Backend responded"
        )
    except APIError as exc:
        st.error("Backend unavailable")
        st.caption(str(exc))

try:
    health = api_request(backend_url, "GET", "/health")
    if health.get("status") != "ok":
        st.warning("The backend is responding with an unexpected health status.")
        st.stop()
except APIError as exc:
    page_header("Support workspace", "Customer, order, and ticket operations")
    st.error(str(exc))
    st.info(
        "Start the API in a separate terminal with `py -3.12 -m uvicorn app.main:app --reload`. "
        "For Docker, set `ACME_API_URL` to the backend container address."
    )
    st.stop()

try:
    if selected_page == "Overview":
        page_header("Support workspace", "A live view of customer care across Acme.")
        customers = load_all(backend_url, "/customers")
        orders = load_all(backend_url, "/orders")
        tickets = load_all(backend_url, "/tickets")

        metric_cols = st.columns(4)
        metric_cols[0].metric("Customers", f"{len(customers):,}")
        metric_cols[1].metric("Orders", f"{len(orders):,}")
        total_value = orders["amount_inr"].sum() if not orders.empty else 0
        metric_cols[2].metric("Order value", f"₹{total_value:,.0f}")
        active_tickets = (
            tickets["status"].isin(["open", "in_progress"]).sum()
            if not tickets.empty
            else 0
        )
        metric_cols[3].metric("Active tickets", f"{active_tickets:,}")

        chart_left, chart_right = st.columns([1.15, 1], gap="large")
        with chart_left:
            st.subheader("Order flow")
            if orders.empty:
                st.info("No orders are available.")
            else:
                status_counts = (
                    orders["status"]
                    .value_counts()
                    .reindex(ORDER_STATUSES, fill_value=0)
                )
                render_bars(status_counts, "#287c72")
            st.subheader("Order value by month")
            if not orders.empty:
                monthly = (
                    orders.assign(
                        month=pd.to_datetime(orders["created_at"])
                        .dt.to_period("M")
                        .astype(str)
                    )
                    .groupby("month")["amount_inr"]
                    .sum()
                )
                render_bars(monthly.tail(8), "#b94b32", currency=True)
        with chart_right:
            st.subheader("Ticket queue")
            if tickets.empty:
                st.info("No tickets are available.")
            else:
                ticket_counts = (
                    tickets["status"]
                    .value_counts()
                    .reindex(TICKET_STATUSES, fill_value=0)
                )
                render_bars(ticket_counts, "#b94b32")
            st.subheader("By priority")
            if not tickets.empty:
                priority_counts = (
                    tickets["priority"]
                    .value_counts()
                    .reindex(reversed(TICKET_PRIORITIES), fill_value=0)
                )
                render_bars(priority_counts, "#d49b36")

        st.divider()
        st.subheader("Latest tickets")
        latest_tickets = (
            tickets.sort_values(["created_at", "id"], ascending=False).head(8)
            if not tickets.empty
            else tickets
        )
        show_table(
            latest_tickets,
            ["id", "customer_id", "subject", "priority", "status", "created_at"],
        )

    elif selected_page == "Customers":
        page_header("Customers", "Find a customer and review their order history.")
        city_col, count_col = st.columns([2, 1])
        city = city_col.text_input("City", placeholder="Filter by city")
        customers = load_all(
            backend_url,
            "/customers",
            {"city": city.strip()} if city.strip() else None,
        )
        count_col.metric("Matching customers", f"{len(customers):,}")
        show_table(
            customers,
            ["id", "name", "email", "phone", "city", "state", "created_at"],
        )

        st.divider()
        st.subheader("Customer profile")
        with st.form("customer_lookup", clear_on_submit=False):
            customer_id = st.number_input("Customer ID", min_value=1, step=1, value=1)
            lookup_customer = st.form_submit_button("Open profile", type="primary")
        if lookup_customer:
            st.session_state["customer_profile"] = api_request(
                backend_url, "GET", f"/customers/{int(customer_id)}"
            )
        profile = st.session_state.get("customer_profile")
        if profile:
            profile_col, history_col = st.columns([1, 2], gap="large")
            with profile_col:
                st.markdown(f"### {profile['name']}")
                st.write(profile["email"])
                st.write(profile["phone"])
                st.caption(f"{profile['city']}, {profile['state']}")
                st.caption(f"Customer since {profile['created_at'][:10]}")
            with history_col:
                st.markdown("### Order history")
                history = pd.DataFrame(
                    api_request(
                        backend_url,
                        "GET",
                        f"/customers/{profile['id']}/orders",
                    )
                )
                show_table(
                    history,
                    ["id", "product", "quantity", "amount_inr", "status", "created_at"],
                )

    elif selected_page == "Orders":
        page_header(
            "Orders", "Search orders and advance each order by one lifecycle step."
        )
        with st.form("order_search"):
            filter_cols = st.columns(4)
            status = filter_cols[0].selectbox("Status", ["All", *ORDER_STATUSES])
            customer_filter = filter_cols[1].text_input("Customer ID")
            date_filter = filter_cols[2].checkbox("Use date range")
            from_date = filter_cols[3].date_input(
                "From",
                value=date.today() - timedelta(days=30),
                disabled=not date_filter,
            )
            to_date = st.date_input(
                "Through", value=date.today(), disabled=not date_filter
            )
            search_submitted = st.form_submit_button("Search orders", type="primary")

        if search_submitted or "order_results" not in st.session_state:
            order_params = {}
            if status != "All":
                order_params["status"] = status
            if customer_filter.strip():
                if not customer_filter.strip().isdigit():
                    st.error("Customer ID must be a whole number.")
                    st.stop()
                order_params["customer_id"] = int(customer_filter.strip())
            if date_filter:
                if from_date > to_date:
                    st.error("The start date must be on or before the end date.")
                    st.stop()
                order_params.update(
                    date_from=from_date.isoformat(), date_to=to_date.isoformat()
                )
            st.session_state["order_results"] = load_all(
                backend_url, "/orders/search", order_params
            )
            st.session_state["order_filter_signature"] = order_params

        orders = st.session_state.get("order_results", pd.DataFrame())
        st.caption(f"{len(orders):,} matching orders")
        show_table(
            orders,
            [
                "id",
                "customer_id",
                "product",
                "quantity",
                "amount_inr",
                "status",
                "created_at",
            ],
        )

        st.divider()
        st.subheader("Advance an order")
        with st.form("order_lookup"):
            order_id = st.text_input("Order ID", placeholder="A-1042")
            lookup_order = st.form_submit_button("Load order")
        if lookup_order:
            st.session_state["selected_order"] = api_request(
                backend_url, "GET", f"/orders/{order_id.strip()}"
            )
        order = st.session_state.get("selected_order")
        if order:
            detail_col, action_col = st.columns([2, 1], gap="large")
            with detail_col:
                st.markdown(f"### {order['id']} · {order['product']}")
                st.write(
                    f"Customer {order['customer_id']} · {order['quantity']} item(s) · "
                    f"₹{order['amount_inr']:,.2f}"
                )
                st.caption(f"Placed {order['created_at'][:10]}")
            with action_col:
                st.metric("Current status", order["status"].replace("_", " ").title())
                next_status = ORDER_NEXT.get(order["status"])
                if next_status:
                    if st.button(
                        f"Advance to {next_status.title()}",
                        type="primary",
                        key="advance_order",
                    ):
                        updated = api_request(
                            backend_url,
                            "PATCH",
                            f"/orders/{order['id']}/status",
                            json={"status": next_status},
                        )
                        st.session_state["selected_order"] = updated
                        st.session_state.pop("order_results", None)
                        st.cache_data.clear()
                        st.success("Order status updated.")
                        st.rerun()
                else:
                    st.info("This order is at its final status.")

    elif selected_page == "Agent desk":
        page_header(
            "Agent desk",
            "Investigate with policy-grounded RAG, then approve a guarded workflow action.",
        )
        st.info(
            "The agent can read support records and draft a reply. It cannot send messages or move money. "
            "Recording a refunded status changes workflow state only; it is not proof of payment."
        )
        with st.form("agent_ticket_lookup"):
            agent_ticket_id = st.number_input("Ticket ID", min_value=1, step=1)
            order_override = st.text_input(
                "Order ID if the ticket is not linked", placeholder="Optional"
            )
            action_labels = {
                "Investigate only": None,
                "Take ticket": "take_ticket",
                "Record refund workflow status": "record_refund_status",
                "Resolve ticket": "resolve_ticket",
            }
            action_label = st.selectbox("Proposed action", list(action_labels), index=0)
            use_external_model = False
            if external_model_available():
                use_external_model = st.checkbox(
                    "Allow this ticket and order data to be sent to the configured model provider",
                    value=False,
                )
            analyze_submitted = st.form_submit_button(
                "Investigate ticket", type="primary"
            )
        if analyze_submitted:
            thread_id = uuid.uuid4().hex
            st.session_state["agent_thread_id"] = thread_id
            st.session_state["agent_api_url"] = backend_url
            st.session_state.pop("agent_reply_key", None)
            try:
                with st.spinner("Reading case facts and retrieving policy..."):
                    graph = get_support_graph(backend_url)
                    st.session_state["agent_graph_result"] = run_investigation(
                        graph,
                        ticket_id=int(agent_ticket_id),
                        thread_id=thread_id,
                        order_id=order_override.strip() or None,
                        requested_action=action_labels[action_label],
                        use_external_model=use_external_model,
                    )
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))

        result = st.session_state.get("agent_graph_result")
        if result:
            ticket = result["ticket"]
            customer = result["customer"]
            order = result.get("order")
            analysis = result["analysis"]
            policies = result.get("policies", [])
            passages = [PolicyPassage(**item) for item in policies]
            graph_interrupts = result.get("__interrupt__", ())
            interrupt_data = None
            if graph_interrupts:
                interrupt_data = getattr(
                    graph_interrupts[0], "value", graph_interrupts[0]
                )

            info_cols = st.columns(4)
            info_cols[0].metric("Ticket", f"#{ticket['id']}")
            info_cols[1].metric("Customer", customer["name"])
            info_cols[2].metric("Intent", analysis["intent"].replace("_", " ").title())
            info_cols[3].metric(
                "Order status", order["status"].title() if order else "Not linked"
            )

            st.subheader("Recommended next step")
            st.write(analysis["recommendation"])
            if analysis["order_action"] == "record_refund_status":
                st.warning(
                    "Before recording this workflow step, verify the real payment in your approved finance system. "
                    "This API does not process or confirm a payment."
                )

            source_col, draft_col = st.columns([1, 1.25], gap="large")
            with source_col:
                st.subheader("Retrieved policy")
                if passages:
                    for passage in passages:
                        with st.expander(
                            f"[{passage.source_id}] {passage.title}", expanded=True
                        ):
                            st.caption(passage.source)
                            st.write(passage.text)
                else:
                    st.warning(
                        "No policy passages were found. Treat the case as manual review."
                    )
                trace = pd.DataFrame(result.get("tool_trace", []))
                if not trace.empty:
                    st.caption("Graph tool activity")
                    show_table(trace, ["tool", "result"])

            with draft_col:
                st.subheader("Customer reply draft")
                if result.get("model_error"):
                    st.warning(result["model_error"])
                thread_id = st.session_state["agent_thread_id"]
                reply_key = f"agent-reply-{thread_id}"
                if st.session_state.get("agent_reply_key") != reply_key:
                    st.session_state[reply_key] = result.get("draft_reply", "")
                    st.session_state["agent_reply_key"] = reply_key
                reply = st.text_area(
                    "Review and edit before sending",
                    key=reply_key,
                    height=200,
                    label_visibility="collapsed",
                )
                st.caption(
                    "The demo has no message-sending connector; copy this draft into an approved support channel."
                )

            st.divider()
            if interrupt_data:
                action = interrupt_data["action"]
                st.subheader("Action approval required")
                st.warning(action["description"])
                finance_verified = False
                reply_sent = False
                if interrupt_data.get("requires_finance_verification"):
                    finance_verified = st.checkbox(
                        "I verified the payment was issued in the finance system.",
                        key=f"finance-verified-{thread_id}",
                    )
                if interrupt_data.get("requires_reply_confirmation"):
                    reply_sent = st.checkbox(
                        "I sent the reviewed reply through an approved support channel.",
                        key=f"reply-sent-{thread_id}",
                    )
                approve_col, decline_col = st.columns(2)
                if approve_col.button(
                    "Approve action", type="primary", key=f"approve-{thread_id}"
                ):
                    try:
                        graph = get_support_graph(st.session_state["agent_api_url"])
                        st.session_state["agent_graph_result"] = resume_approved_action(
                            graph,
                            thread_id=thread_id,
                            decision={
                                "approved": True,
                                "finance_verified": finance_verified,
                                "reply_sent": reply_sent,
                            },
                        )
                        st.rerun()
                    except (RuntimeError, ValueError) as exc:
                        st.error(str(exc))
                if decline_col.button("Decline", key=f"decline-{thread_id}"):
                    graph = get_support_graph(st.session_state["agent_api_url"])
                    st.session_state["agent_graph_result"] = resume_approved_action(
                        graph,
                        thread_id=thread_id,
                        decision={"approved": False},
                    )
                    st.rerun()

            action_result = result.get("action_result") or {}
            if action_result.get("ok"):
                st.success(
                    "Workflow status updated. No payment was initiated and no customer message was sent."
                )
            elif action_result.get("detail"):
                st.warning(action_result["detail"])

            case_brief = make_case_brief(
                ticket, customer, order, analysis, reply, passages
            )
            st.download_button(
                "Download synthetic internal case brief",
                data=case_brief,
                file_name=f"synthetic-case-brief-ticket-{ticket['id']}.md",
                mime="text/markdown",
                icon=":material/download:",
            )
            st.caption(
                "Generated brief is stamped synthetic and is not a receipt, refund confirmation, or proof of transaction."
            )

    else:
        page_header(
            "Support tickets",
            "Triage the queue, raise a ticket, and update its status.",
        )
        filter_cols = st.columns(3)
        ticket_status = filter_cols[0].selectbox("Status", ["All", *TICKET_STATUSES])
        ticket_priority = filter_cols[1].selectbox(
            "Priority", ["All", *TICKET_PRIORITIES]
        )
        customer_filter = filter_cols[2].text_input(
            "Customer ID", key="ticket_customer_filter"
        )
        ticket_params = {}
        if ticket_status != "All":
            ticket_params["status"] = ticket_status
        if ticket_priority != "All":
            ticket_params["priority"] = ticket_priority
        if customer_filter.strip():
            if not customer_filter.strip().isdigit():
                st.error("Customer ID must be a whole number.")
                st.stop()
            ticket_params["customer_id"] = int(customer_filter.strip())
        tickets = load_all(backend_url, "/tickets", ticket_params)
        st.caption(f"{len(tickets):,} matching tickets")
        show_table(
            tickets,
            [
                "id",
                "customer_id",
                "order_id",
                "subject",
                "channel",
                "priority",
                "status",
                "created_at",
            ],
        )

        st.divider()
        create_col, update_col = st.columns([1.1, 1], gap="large")
        with create_col:
            st.subheader("Create a ticket")
            with st.form("new_ticket", clear_on_submit=True):
                customer_id = st.number_input("Customer ID", min_value=1, step=1)
                order_id = st.text_input("Related order ID", placeholder="Optional")
                subject = st.text_input("Subject", max_chars=200)
                message = st.text_area("Message", max_chars=5000, height=120)
                input_cols = st.columns(2)
                channel = input_cols[0].selectbox("Channel", TICKET_CHANNELS)
                priority = input_cols[1].selectbox(
                    "Priority", ["medium", "low", "high"]
                )
                create_submitted = st.form_submit_button(
                    "Create ticket", type="primary"
                )
            if create_submitted:
                if not 3 <= len(subject.strip()) <= 200:
                    st.error("Subject must contain between 3 and 200 characters.")
                elif not 5 <= len(message.strip()) <= 5000:
                    st.error("Message must contain between 5 and 5,000 characters.")
                else:
                    created = api_request(
                        backend_url,
                        "POST",
                        "/tickets",
                        json={
                            "customer_id": int(customer_id),
                            "order_id": order_id.strip() or None,
                            "subject": subject.strip(),
                            "message": message.strip(),
                            "channel": channel,
                            "priority": priority,
                        },
                    )
                    st.success(f"Created ticket #{created['id']}.")
                    st.rerun()

        with update_col:
            st.subheader("Update ticket status")
            with st.form("ticket_lookup"):
                ticket_id = st.number_input("Ticket ID", min_value=1, step=1)
                lookup_ticket = st.form_submit_button("Load ticket")
            if lookup_ticket:
                st.session_state["selected_ticket"] = api_request(
                    backend_url, "GET", f"/tickets/{int(ticket_id)}"
                )
            ticket = st.session_state.get("selected_ticket")
            if ticket:
                st.markdown(f"### #{ticket['id']} · {ticket['subject']}")
                st.caption(
                    f"Customer {ticket['customer_id']} · {ticket['channel']} · "
                    f"{ticket['priority']} priority"
                )
                st.write(ticket["message"])
                if ticket["status"] == "closed":
                    st.info("Closed tickets cannot be changed.")
                else:
                    with st.form("ticket_status_update"):
                        new_status = st.selectbox(
                            "New status",
                            TICKET_STATUSES,
                            index=TICKET_STATUSES.index(ticket["status"]),
                        )
                        save_status = st.form_submit_button(
                            "Save status", type="primary"
                        )
                    if save_status:
                        st.session_state["selected_ticket"] = api_request(
                            backend_url,
                            "PATCH",
                            f"/tickets/{ticket['id']}/status",
                            json={"status": new_status},
                        )
                        st.success("Ticket status updated.")
                        st.rerun()

except APIError as exc:
    st.error(str(exc))
