import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(layout="wide")  # Landscape mode

# ---------- Load Data ----------
df = pd.read_csv("all_data_timing_edited.csv")
df.columns = df.columns.str.strip()

# Clean jitter
if 'Jitter' in df.columns:
    df['Jitter'] = df['Jitter'].astype(str).str.replace('ms', '').str.strip()
    df['Jitter'] = pd.to_numeric(df['Jitter'], errors='coerce')

# Clean device & traffic
df['Device'] = df['Device'].str.lower()
df['Traffic'] = df['Traffic'].str.upper()

# RSSI categories
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

# ---------- Filters (BOTTOM layout) ----------
with st.container():
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        selected_rssi = st.selectbox("RSSI Quality", ['All'] + sorted(df['RSSI_Category'].unique()))
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
# ---------- Layout: Pie + CDFs ----------
st.title("Performance Dashboard")

# ---------- Layout: 2 Rows × 3 Columns ----------
row1_col1, row1_col2, row1_col3 = st.columns(3)
row2_col1, row2_col2, row2_col3 = st.columns(3)

# ---------- (1,1) Pie Chart ----------
with row1_col1:
    st.markdown("<h3 style='font-size:20px;'>Timing Breakdown (Pie)", unsafe_allow_html=True)
    #st.subheader("Timing Breakdown (Pie)")
    timing_cols = ['Mgnt_overheads', 'Ctrl Overheads', 'data0', 'data1', 'Unrelated', 'Other_BSS', 'Idle']
    if filtered_df.empty:
        st.warning("No data.")
    else:
        avg_vals = filtered_df[timing_cols].astype(float).mean()
        fig1, ax1 = plt.subplots(figsize=(4, 4))
        ax1.pie(avg_vals, labels=timing_cols, autopct='%1.1f%%', startangle=140)
        ax1.set_title("Time Split")
        st.pyplot(fig1)

# ---------- (1,2) CDF: Throughput ----------
with row1_col2:
    st.markdown("<h3 style='font-size:20px;'>CDF: Throughput</h3>", unsafe_allow_html=True)
   # st.subheader("CDF: Throughput")
    fig2, ax2 = plt.subplots()
    if not filtered_df.empty:
        data = filtered_df['Throughput(iperf)'].dropna().astype(float)
        sorted_data = np.sort(data)
        yvals = np.arange(len(sorted_data)) / float(len(sorted_data))
        ax2.plot(sorted_data, yvals, label='Throughput (iperf)')
        ax2.set_xlabel("Mbps")
        ax2.set_ylabel("CDF")
        ax2.grid(True, linestyle=':')
        st.pyplot(fig2)
    else:
        st.info("No data.")

# ---------- (1,3) CDF: Jitter ----------
with row1_col3:
    st.markdown("<h3 style='font-size:20px;'>CDF: Jitter</h3>", unsafe_allow_html=True)

   # st.subheader("CDF: Jitter")
    fig3, ax3 = plt.subplots()
    if 'Jitter' in filtered_df.columns and filtered_df['Jitter'].dropna().shape[0] > 0:
        data = filtered_df['Jitter'].dropna().astype(float)
        sorted_data = np.sort(data)
        yvals = np.arange(len(sorted_data)) / float(len(sorted_data))
        ax3.plot(sorted_data, yvals, label='Jitter')
        ax3.set_xlabel("ms")
        ax3.set_ylabel("CDF")
        ax3.grid(True, linestyle=':')
        st.pyplot(fig3)
    else:
        st.info("No jitter data.")

# ---------- (2,1) MCS % Bar Chart: R0 vs R1 ----------
with row2_col1:
    st.markdown("<h3 style='font-size:20px;'>MCS Usage (%) - Initial vs Retry</h3>", unsafe_allow_html=True)

    #st.subheader("MCS Usage (%) - Initial vs Retry")

    if 'R0_Max_MCS' in filtered_df.columns and 'R1_Max_MCS' in filtered_df.columns:
        # Filter only MCS 1 to 8
        target_mcs = [8, 7, 6, 5, 4, 3, 2, 1]

        r0_vals_raw = filtered_df['R0_Max_MCS'].dropna().astype(int)
        r1_vals_raw = filtered_df['R1_Max_MCS'].dropna().astype(int)

        r0_counts = r0_vals_raw[r0_vals_raw.isin(target_mcs)].value_counts().reindex(target_mcs, fill_value=0)
        r1_counts = r1_vals_raw[r1_vals_raw.isin(target_mcs)].value_counts().reindex(target_mcs, fill_value=0)

        total_r0 = r0_counts.sum()
        total_r1 = r1_counts.sum()

        r0_perc = (r0_counts / total_r0 * 100).round(2) if total_r0 > 0 else r0_counts
        r1_perc = (r1_counts / total_r1 * 100).round(2) if total_r1 > 0 else r1_counts

        x = np.arange(len(target_mcs))
        width = 0.35

        fig, ax = plt.subplots()
        ax.bar(x - width/2, r0_perc, width, label='Initial (R0)', color='blue')
        ax.bar(x + width/2, r1_perc, width, label='Retry (R1)', color='red')

        ax.set_xticks(x)
        ax.set_xticklabels(target_mcs)
        ax.set_xlabel("MCS Index")
        ax.set_ylabel("Percentage (%)")
        ax.set_title("MCS Usage Distribution (R0 vs R1)")
        ax.legend()
        ax.set_ylim(0, 100)
        st.pyplot(fig)
    else:
        st.info("MCS columns not available.")


# ---------- (2,2) CDF: Retry Rate ----------
with row2_col2:
    st.markdown("<h3 style='font-size:20px;'>CDF: Retry Rate</h3>", unsafe_allow_html=True)
   # st.subheader("CDF: Retry Rate")
    fig5, ax5 = plt.subplots()
    if not filtered_df.empty:
        app = filtered_df['Retry_perc(iperf)'].dropna().astype(float)
        mac = filtered_df['TXOP_retry_rate'].dropna().astype(float)
        if not app.empty:
            sorted_app = np.sort(app)
            y_app = np.arange(len(sorted_app)) / len(sorted_app)
            ax5.plot(sorted_app, y_app, label='Retry % (App)')
        if not mac.empty:
            sorted_mac = np.sort(mac)
            y_mac = np.arange(len(sorted_mac)) / len(sorted_mac)
            ax5.plot(sorted_mac, y_mac, label='Retry Rate (MAC)')
        ax5.set_xlabel("%")
        ax5.set_ylabel("CDF")
        ax5.grid(True, linestyle=':')
        ax5.legend()
        st.pyplot(fig5)
    else:
        st.info("No retry data.")

# ---------- (2,3) Correlation Heatmap ----------
with row2_col3:
    st.markdown("<h3 style='font-size:20px;'>Correlation Map</h3>", unsafe_allow_html=True)
   # st.subheader("Correlation Map")
    corr_cols = ['Throughput(iperf)', 'Jitter', 'Retry_perc(iperf)', 'TXOP_retry_rate', 'RSSI_avg(dBm)']
    df_corr = filtered_df[corr_cols].dropna().copy()
    df_corr = df_corr.astype(float)
    if df_corr.empty:
        st.info("No data for correlation.")
    else:
        corr = df_corr.corr()
        fig6, ax6 = plt.subplots()
        cax = ax6.matshow(corr, cmap='coolwarm')
        fig6.colorbar(cax)
        ticks = range(len(corr.columns))
        ax6.set_xticks(ticks)
        ax6.set_yticks(ticks)
        ax6.set_xticklabels(corr.columns, rotation=45, ha='left')
        ax6.set_yticklabels(corr.columns)
        st.pyplot(fig6)
