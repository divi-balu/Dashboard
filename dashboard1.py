import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(layout="wide")

# ---------- Load Data ----------
df = pd.read_csv("all_data_timing_edited.csv")
df.columns = df.columns.str.strip()

# Clean Jitter
if 'Jitter' in df.columns:
    df['Jitter'] = df['Jitter'].astype(str).str.replace('ms', '').str.strip()
    df['Jitter'] = pd.to_numeric(df['Jitter'], errors='coerce')

# Normalize Device and Traffic
df['Device'] = df['Device'].str.lower()
df['Traffic'] = df['Traffic'].str.upper()

# Classify RSSI
def classify_rssi(rssi):
    if rssi >= -50:
        return 'Excellent (≥ -50 dBm)'
    elif -65 <= rssi < -50:
        return 'Good (-65 to -50 dBm)'
    elif -75 <= rssi < -65:
        return 'Fair (-75 to -65 dBm)'
    else:
        return 'Poor (< -75 dBm)'

df['RSSI_Category'] = df['RSSI_avg(dBm)'].apply(classify_rssi)

# ---------- Filters ----------
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    rssi_order = ['Excellent (≥ -50 dBm)', 'Good (-65 to -50 dBm)', 'Fair (-75 to -65 dBm)', 'Poor (< -75 dBm)']
    available_rssi = [r for r in rssi_order if r in df['RSSI_Category'].unique()]
    selected_rssi = st.selectbox("RSSI Quality", ['All'] + available_rssi)
with col2:
    selected_device = st.selectbox("Device", ['All'] + sorted(df['Device'].dropna().unique()))
with col3:
    selected_traffic = st.selectbox("Traffic", ['All'] + sorted(df['Traffic'].dropna().unique()))

# ---------- Apply Filters ----------
filtered_df = df.copy()
if selected_rssi != 'All':
    filtered_df = filtered_df[filtered_df['RSSI_Category'] == selected_rssi]
if selected_device != 'All':
    filtered_df = filtered_df[filtered_df['Device'] == selected_device]
if selected_traffic != 'All':
    filtered_df = filtered_df[filtered_df['Traffic'] == selected_traffic]

# ---------- Layout: 2 Rows × 4 Columns ----------
row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

# ---------- (1,1) Pie Chart ----------
with row1_col1:
    st.markdown("<h4>Timing Breakdown (Pie)</h4>", unsafe_allow_html=True)
    timing_cols = ['Mgnt_overheads', 'Ctrl Overheads', 'data0', 'data1', 'Unrelated', 'Other_BSS', 'Idle']
    if not filtered_df.empty:
        avg_vals = filtered_df[timing_cols].astype(float).mean()
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.pie(avg_vals, labels=timing_cols, autopct='%1.1f%%', startangle=140)
        ax.set_title("Time Split")
        st.pyplot(fig)
    else:
        st.info("No data for pie chart.")

# ---------- (1,2) CDF: Throughput ----------
with row1_col2:
    st.markdown("<h4>CDF: Throughput</h4>", unsafe_allow_html=True)
    fig, ax = plt.subplots()
    if not filtered_df.empty:
        data = filtered_df['Throughput(iperf)'].dropna().astype(float)
        sorted_data = np.sort(data)
        yvals = np.linspace(0, 1, len(sorted_data))
        ax.plot(sorted_data, yvals, label='Throughput (iperf)')
        ax.set_xlabel("Mbps")
        ax.set_ylabel("CDF")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1)
        ax.grid(True, linestyle=':')
        st.pyplot(fig)
    else:
        st.info("No data for throughput.")

# ---------- (1,3) CDF: Jitter ----------
with row1_col3:
    st.markdown("<h4>CDF: Jitter</h4>", unsafe_allow_html=True)
    fig, ax = plt.subplots()
    if 'Jitter' in filtered_df.columns and filtered_df['Jitter'].dropna().shape[0] > 0:
        data = filtered_df['Jitter'].dropna().astype(float)
        sorted_data = np.sort(data)
        yvals = np.linspace(0, 1, len(sorted_data))
        ax.plot(sorted_data, yvals, label='Jitter')
        ax.set_xlabel("ms")
        ax.set_ylabel("CDF")
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 1)
        ax.grid(True, linestyle=':')
        st.pyplot(fig)
    else:
        st.info("No jitter data.")

# ---------- (1,4) CDF: Retry Rate ----------
with row1_col4:
    st.markdown("<h4>CDF: Retry Rate</h4>", unsafe_allow_html=True)
    fig, ax = plt.subplots()
    if not filtered_df.empty:
        app = filtered_df['Retry_perc(iperf)'].dropna().astype(float)
        mac = filtered_df['TXOP_retry_rate'].dropna().astype(float)
        if not app.empty:
            sorted_app = np.sort(app)
            y_app = np.linspace(0, 1, len(sorted_app))
            #y_app = np.arange(len(sorted_app)) / len(sorted_app)
            ax.plot(sorted_app, y_app, label='Retry % (App)')
        if not mac.empty:
            sorted_mac = np.sort(mac)
            y_mac = np.linspace(0, 1, len(sorted_mac))
           # y_mac = np.arange(len(sorted_mac)) / len(sorted_mac)
            ax.plot(sorted_mac, y_mac, label='Retry Rate (MAC)', linestyle='--')
        ax.set_xlabel("%")
        ax.set_ylabel("CDF")
        ax.set_xlim(0, 30)
        ax.set_ylim(0, 1)
        ax.grid(True, linestyle=':')
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("No retry data.")

# ---------- (2,1) MCS % Bar Chart ----------
with row2_col1:
    st.markdown("<h4>MCS Usage (%)</h4>", unsafe_allow_html=True)
    if 'R0_Max_MCS' in filtered_df.columns and 'R1_Max_MCS' in filtered_df.columns:
        target_mcs = [8, 7, 6, 5, 4, 3, 2, 1]
        r0 = filtered_df['R0_Max_MCS'].dropna().astype(int)
        r1 = filtered_df['R1_Max_MCS'].dropna().astype(int)
        r0_counts = r0[r0.isin(target_mcs)].value_counts().reindex(target_mcs, fill_value=0)
        r1_counts = r1[r1.isin(target_mcs)].value_counts().reindex(target_mcs, fill_value=0)
        total_r0, total_r1 = r0_counts.sum(), r1_counts.sum()
        r0_perc = (r0_counts / total_r0 * 100) if total_r0 else r0_counts
        r1_perc = (r1_counts / total_r1 * 100) if total_r1 else r1_counts
        x = np.arange(len(target_mcs))
        width = 0.35
        fig, ax = plt.subplots()
        ax.bar(x - width/2, r0_perc, width, label='R0', color='blue')
        ax.bar(x + width/2, r1_perc, width, label='R1', color='red')
        ax.set_xticks(x)
        ax.set_xticklabels(target_mcs)
        ax.set_xlabel("MCS Index")
        ax.set_ylabel("Percentage (%)")
        ax.set_ylim(0, 100)
        ax.legend()
        st.pyplot(fig)
    else:
        st.info("No MCS data.")

# ---------- (2,4) SGI + Retry as Metrics ----------
with row2_col4:
    st.markdown("<h4>SGI & Retry Rate</h4>", unsafe_allow_html=True)
    col_sgi, col_retry = st.columns(2)

    with col_sgi:
        if not filtered_df.empty and 'sgi' in filtered_df.columns and 'lgi' in filtered_df.columns:
            sgi_sum = filtered_df['sgi'].sum()
            lgi_sum = filtered_df['lgi'].sum()
            total = sgi_sum + lgi_sum
            sgi_pct = round((sgi_sum / total) * 100, 2) if total > 0 else 0
            st.metric("SGI %", f"{sgi_pct} %")
        else:
            st.info("Missing SGI/LGI")

    with col_retry:
        if 'Retry_perc(iperf)' in filtered_df.columns:
            retry_avg = filtered_df['Retry_perc(iperf)'].dropna().astype(float).mean()
            retry_avg = round(retry_avg, 2)
            st.metric("Retry %", f"{retry_avg} %")
        else:
            st.info("No retry data")

# ---------- (2,3) MSDU / AMPDU Most Frequent ----------
with row2_col3:
    st.markdown("<h4>Most Frequent MSDU / AMPDU</h4>", unsafe_allow_html=True)
    if not filtered_df.empty:
        msdu_mode = filtered_df['Most_MSDU_per_TXOP'].mode()
        ampdu_mode = filtered_df['Most_AMPDU_per_TXOP'].mode()
        msdu_val = msdu_mode.iloc[0] if not msdu_mode.empty else "N/A"
        ampdu_val = ampdu_mode.iloc[0] if not ampdu_mode.empty else "N/A"
        st.metric("MSDU per TXOP", f"{msdu_val}")
        st.metric("AMPDU per TXOP", f"{ampdu_val}")
    else:
        st.info("No data.")

# ---------- (2,2) Correlation Heatmap ----------
with row2_col2:
    st.markdown("<h4>Correlation Map</h4>", unsafe_allow_html=True)
    corr_cols = ['Throughput(iperf)', 'Jitter', 'Retry_perc(iperf)', 'TXOP_retry_rate', 'RSSI_avg(dBm)']
    df_corr = filtered_df[corr_cols].dropna().astype(float)
    if df_corr.empty:
        st.info("No data for correlation.")
    else:
        corr = df_corr.corr()
        fig, ax = plt.subplots()
        im = ax.imshow(corr, cmap='coolwarm')
        for i in range(len(corr.columns)):
            for j in range(len(corr.columns)):
                ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha='center', va='center', color='black')
        fig.colorbar(im, ax=ax)
        ax.set_xticks(np.arange(len(corr.columns)))
        ax.set_yticks(np.arange(len(corr.columns)))
        ax.set_xticklabels(corr.columns, rotation=45, ha='right')
        ax.set_yticklabels(corr.columns)
        ax.tick_params(top=False, bottom=True, labeltop=False, labelbottom=True)
        st.pyplot(fig)
