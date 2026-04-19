"""Delivery Dron — Analytics Dashboard (Streamlit + Plotly)."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(
    page_title="Delivery Dron — Dashboard",
    page_icon="\U0001F681",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background: rgba(102, 126, 234, 0.08);
        border-radius: 10px;
        padding: 12px 16px;
        border-left: 4px solid #667eea;
    }
    [data-testid="stMetricValue"] { font-size: 1.4rem; color: #667eea; }
    [data-testid="stMetricLabel"] { opacity: 0.7; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

MONTH_MAP = {5: "Май", 6: "Июнь", 7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь"}
PALETTE = px.colors.qualitative.Set2


@st.cache_data
def load_data():
    data = pd.read_csv("data.csv", sep=";")
    data.columns = data.columns.str.strip().str.lower().str.replace(" ", "_")
    df = data.dropna(subset=["region"]).copy()

    df["region"] = df["region"].replace({
        "Unjted States": "United States",
        "Fr\u0430nce": "France", "Fr\u0430nc\u0435": "France",
        "Fran\u0441e": "France", "germany": "Germany", "U\u041a": "UK",
    })
    df["device"] = df["device"].replace({"android": "Android"})
    df["channel"] = df["channel"].replace({"\u043a\u043e\u043d\u0442\u0435\u043a\u0441\u043d\u0430\u044f \u0440\u0435\u043a\u043b\u0430\u043c\u0430": "\u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u043d\u0430\u044f \u0440\u0435\u043a\u043b\u0430\u043c\u0430"})
    df.loc[(df["promo_code"] != 0) & (df["promo_code"] != 1), "promo_code"] = 0
    df = df.drop_duplicates()

    for col in ["session_start", "session_end", "session_date", "order_dt"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    df["revenue_with_promo"] = df["revenue"] * (1 - df["promo_code"] * 0.1)
    df = df[(df["revenue"] <= 20000) | (df["order_dt"].isna())]

    def _time(t):
        h = t.hour
        if 6 <= h < 10: return "Утро"
        if 10 <= h < 17: return "День"
        if 17 <= h < 22: return "Вечер"
        return "Ночь"

    df["time_visit"] = df["session_start"].apply(_time)
    df["payer"] = df["order_dt"].notna().astype(int)
    df["month_name"] = df["month"].map(MONTH_MAP)
    return df


df = load_data()

# ════════════════ Sidebar Filters ════════════════
st.sidebar.markdown("## Фильтры")

channels = ["Все"] + sorted(df["channel"].unique().tolist())
sel_channel = st.sidebar.selectbox("Рекламный канал", channels)

min_d, max_d = df["session_date"].min().date(), df["session_date"].max().date()
sel_dates = st.sidebar.date_input("Период", value=(min_d, max_d), min_value=min_d, max_value=max_d)

regions = ["Все"] + sorted(df["region"].unique().tolist())
sel_region = st.sidebar.selectbox("Регион", regions)

payments = ["Все"] + sorted(df["payment_type"].dropna().unique().tolist())
sel_payment = st.sidebar.selectbox("Тип оплаты", payments)

# Apply filters
fdf = df.copy()
if sel_channel != "Все":
    fdf = fdf[fdf["channel"] == sel_channel]
if sel_region != "Все":
    fdf = fdf[fdf["region"] == sel_region]
if sel_payment != "Все":
    fdf = fdf[(fdf["payment_type"] == sel_payment) | fdf["payment_type"].isna()]
if len(sel_dates) == 2:
    fdf = fdf[(fdf["session_date"].dt.date >= sel_dates[0]) &
              (fdf["session_date"].dt.date <= sel_dates[1])]

# ════════════════ Header ════════════════
st.title("Delivery Dron — Аналитический дашборд")
st.markdown("---")

# ════════════════ KPIs ════════════════
k1, k2, k3, k4, k5 = st.columns(5)
total_rev = fdf["revenue_with_promo"].sum()
avg_check = fdf.loc[fdf["payer"] == 1, "revenue_with_promo"].mean()
total_users = fdf["user_id"].nunique()
paying = fdf.loc[fdf["payer"] == 1, "user_id"].nunique()
avg_sess = fdf["sessiondurationsec"].mean() / 60

k1.metric("Сумма продаж", f"${total_rev:,.0f}")
k2.metric("Средний чек", f"${avg_check:,.0f}" if pd.notna(avg_check) else "—")
k3.metric("Пользователей", f"{total_users:,}")
k4.metric("Платящих", f"{paying:,}")
k5.metric("Ср. сессия (мин)", f"{avg_sess:.1f}" if pd.notna(avg_sess) else "—")

st.markdown("---")

# ════════════════ Row 1: Regions & Devices ════════════════
c1, c2 = st.columns(2)

with c1:
    rg = fdf.groupby("region")["user_id"].nunique().reset_index(name="users")
    fig = px.pie(rg, values="users", names="region", hole=0.4,
                 title="Пользователи по регионам", color_discrete_sequence=PALETTE)
    fig.update_layout(height=360, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    dv = fdf.groupby("device")["user_id"].nunique().reset_index(name="users")
    fig = px.pie(dv, values="users", names="device", hole=0.4,
                 title="Пользователи по устройствам", color_discrete_sequence=PALETTE)
    fig.update_layout(height=360, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

# ════════════════ Row 2: Monthly trends ════════════════
mo = (fdf.groupby(["month", "month_name"])
      .agg(users=("user_id", "nunique"), revenue=("revenue_with_promo", "sum"))
      .reset_index().sort_values("month"))

fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=mo["month_name"], y=mo["users"], name="Пользователи",
                     marker_color="#667eea", opacity=0.8), secondary_y=False)
fig.add_trace(go.Scatter(x=mo["month_name"], y=mo["revenue"], name="Выручка ($)",
                         mode="lines+markers", line=dict(color="#f64c72", width=2.5),
                         marker=dict(size=8)), secondary_y=True)
fig.update_layout(title="Пользователи и выручка по месяцам", height=380,
                  legend=dict(orientation="h", yanchor="bottom", y=1.02),
                  margin=dict(t=60, b=30))
fig.update_yaxes(title_text="Пользователи", secondary_y=False)
fig.update_yaxes(title_text="Выручка ($)", secondary_y=True)
st.plotly_chart(fig, use_container_width=True)

# ════════════════ Row 3: Revenue by channel + Paying by region ════════════════
c1, c2 = st.columns(2)

with c1:
    ch = (fdf.groupby("channel")["revenue_with_promo"].sum()
          .reset_index().sort_values("revenue_with_promo", ascending=False))
    fig = px.bar(ch, x="channel", y="revenue_with_promo",
                 title="Сумма продаж по рекламному каналу",
                 color="revenue_with_promo", color_continuous_scale="Blues",
                 text_auto=".0f")
    fig.update_layout(height=400, showlegend=False, coloraxis_showscale=False,
                      margin=dict(t=40, b=30))
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    pr = (fdf[fdf["payer"] == 1]
          .groupby(["region", "channel"])["user_id"].nunique()
          .reset_index(name="paying"))
    fig = px.bar(pr, x="region", y="paying", color="channel",
                 title="Платящие пользователи по региону и каналу",
                 barmode="stack", color_discrete_sequence=PALETTE)
    fig.update_layout(height=400, margin=dict(t=40, b=30))
    st.plotly_chart(fig, use_container_width=True)

# ════════════════ Row 4: Session duration + Payment types ════════════════
st.markdown("---")
c1, c2 = st.columns(2)

with c1:
    sc = fdf.groupby("channel")["sessiondurationsec"].mean().reset_index()
    sc["mins"] = sc["sessiondurationsec"] / 60
    sc = sc.sort_values("mins", ascending=False)
    fig = px.bar(sc, x="channel", y="mins",
                 title="Средняя длительность сессии по каналу (мин)",
                 color="mins", color_continuous_scale="Teal",
                 text=sc["mins"].round(1))
    fig.update_layout(height=380, showlegend=False, coloraxis_showscale=False,
                      margin=dict(t=40, b=30))
    fig.update_traces(textposition="outside")
    fig.update_xaxes(tickangle=-25)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    pt = fdf.loc[fdf["payer"] == 1, "payment_type"].value_counts().reset_index()
    pt.columns = ["payment_type", "count"]
    fig = px.bar(pt, x="payment_type", y="count",
                 title="Покупки по типу оплаты",
                 color="payment_type", color_discrete_sequence=px.colors.qualitative.Pastel2)
    fig.update_layout(height=380, showlegend=False, margin=dict(t=40, b=30))
    st.plotly_chart(fig, use_container_width=True)

# ════════════════ Footer ════════════════
st.markdown("---")
st.caption("Delivery Dron Analytics Dashboard | Данные: Май–Октябрь 2025")
