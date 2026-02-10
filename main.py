import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import plotly.express as px
import numpy as np

# --- 1. パスワード保護 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    def password_entered():
        if st.session_state["password_input"] == "wbc1901":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
    st.title("🔐 早稲田大学野球部 データ分析 Pro+")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    return st.session_state["password_correct"]

if check_password():
    st.set_page_config(layout="wide", page_title="野球部データ分析 Pro+")

    # --- 2. 基本設定・描画関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'}

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type == 'Curveball': return '^'
        return 'o'

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset = 55 if batter_side == 'Right' else -55
            flip = -1 if batter_side == 'Right' else 1
        else:
            x_offset = -55 if batter_side == 'Right' else 55
            flip = 1 if batter_side == 'Right' else -1
        color, alpha = '#333333', 0.15
        ax.add_patch(plt.Circle((x_offset, 140), 6, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-12, 85], [x_offset+12, 85], [x_offset+15, 135], [x_offset-15, 135]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-10, 85], [x_offset-2, 85], [x_offset-15, 20], [x_offset-25, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+2, 85], [x_offset+10, 85], [x_offset+25, 20], [x_offset+15, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(15*flip), 125], [x_offset+(40*flip), 170], [x_offset+(48*flip), 167], [x_offset+(18*flip), 122]]), color=color, alpha=0.25, zorder=1))

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f))
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Balls', 'Strikes']
                    for c in cols:
                        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                    for c in ['RelHeight', 'RelSide', 'Extension', 'PlateLocSide', 'PlateLocHeight']:
                        if c in df.columns: df[c] *= 100
                    if 'Distance' in df.columns: df['Distance'] *= 0.3048 # m変換
                    df['SeasonFile'] = f
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        df_full['TaggedPitchType'] = df_full['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown').astype(str)
        df_full['Date_str'] = pd.to_datetime(df_full['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
        b_col = 'Batter Name' if 'Batter Name' in df_full.columns else 'Batter'

        mode = st.radio("🏠 モード選択", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True, label_visibility="collapsed")

        if mode == "🔥 投手分析":
            # --- 投手分析メニュー ---
            st.sidebar.title("🔥 PITCHER MENU")
            p_list = sorted([str(p) for p in df_full[p_col].unique() if pd.notna(p)])
            sel_p = st.sidebar.selectbox("投手を選択", p_list, key="p_sel")
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "1人集中分析"], key="p_report_mode")
            p_full = df_full[df_full[p_col].astype(str) == sel_p].copy()
            target_p_df = p_full.copy()
            st.header(f"📊 {sel_p} 投手：分析結果")
            # (投手分析機能を表示...)
            st.info("投手分析の詳細は総合レポートから確認してください。")

        elif mode == "⚾ 打者分析":
            # --- 打者分析メニュー ---
            st.sidebar.title("⚾ BATTER MENU")
            b_list = sorted([str(b) for b in df_full[b_col].unique() if pd.notna(b)])
            sel_b = st.sidebar.selectbox("打者を選択", b_list, key="b_sel")
            analysis_target = st.sidebar.radio("分析指標を選択", ["打球速度 (km/h)", "打球角度 (deg)", "飛距離 (m)"], key="b_target")
            view_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="b_view")
            
            b_full = df_full[df_full[b_col] == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：コース別分析")

            if not b_full.empty:
                b_full['PlateLocSide_Plot'] = b_full['PlateLocSide'] * (-1 if view_mode == "捕手目線" else 1)
                b_hand = b_full['BatterSide'].mode()[0] if not b_full['BatterSide'].dropna().empty else 'Right'
                
                # 指標設定
                if analysis_target == "打球速度 (km/h)": target_col, v_min, v_max, cmap, unit = 'ExitSpeed', 100, 165, 'Reds', "km/h"
                elif analysis_target == "打球角度 (deg)": target_col, v_min, v_max, cmap, unit = 'Angle', 0, 45, 'viridis', "°"
                else: target_col, v_min, v_max, cmap, unit = 'Distance', 30, 110, 'Blues', "m"

                def plot_heatmap(subset, title, ax):
                    draw_stylish_batter(ax, b_hand, view_mode)
                    x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                    y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max = x_edges[c], x_edges[c+1]
                            y_min, y_max = y_edges[4-r], y_edges[5-r]
                            zone_data = subset[(subset['PlateLocSide_Plot'] >= x_min) & (subset['PlateLocSide_Plot'] < x_max) &
                                               (subset['PlateLocHeight'] >= y_min) & (subset['PlateLocHeight'] < y_max)]
                            if not zone_data.empty:
                                val = zone_data[target_col].mean()
                                if pd.notna(val):
                                    norm = (val - v_min) / (v_max - v_min)
                                    color = plt.get_cmap(cmap)(np.clip(norm, 0, 1))
                                    ax.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.8, ec='white', lw=0.5, zorder=2))
                                    txt_c = 'white' if norm > 0.6 and cmap != 'viridis' else 'black'
                                    ax.text((x_min + x_max)/2, (y_min + y_max)/2, f"{val:.1f}{unit}\n$n$={len(zone_data)}", ha='center', va='center', fontweight='bold', fontsize=9, color=txt_c, zorder=3)
                    ax.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2, zorder=4))
                    ax.set_xlim(-90, 90); ax.set_ylim(10, 180); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, fontsize=15, fontweight='bold')

                # --- レイアウト変更：TOTALを上、対左右を下に ---
                st.subheader(f"📊 全体傾向 (TOTAL)")
                fig_top, ax_top = plt.subplots(figsize=(8, 6))
                plot_heatmap(b_full, "TOTAL", ax_top)
                st.pyplot(fig_top)

                st.markdown("---")
                st.subheader(f"⚔️ 左右別比較")
                col_left, col_right = st.columns(2)
                
                with col_left:
                    fig_r, ax_r = plt.subplots(figsize=(8, 6))
                    plot_heatmap(b_full[b_full['PitcherThrows'] == 'Right'], "VS RIGHT P", ax_r)
                    st.pyplot(fig_r)
                
                with col_right:
                    fig_l, ax_l = plt.subplots(figsize=(8, 6))
                    plot_heatmap(b_full[b_full['PitcherThrows'] == 'Left'], "VS LEFT P", ax_l)
                    st.pyplot(fig_l)
            else:
                st.warning("データが見つかりません。")

    else:
        st.error("dataフォルダにCSVが見つかりません。")
