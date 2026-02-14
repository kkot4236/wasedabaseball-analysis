import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import os
import numpy as np
import matplotlib.cm as cm

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

    # --- 2. 共通描画関数 ---
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00', 'Unknown': '#AAAAAA'
    }

    def draw_strike_zone(ax):
        ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black', zorder=5))
        ax.axvline(0, color='gray', lw=0.5, ls='--')
        ax.axhline(75, color='gray', lw=0.5, ls='--')

    @st.cache_data
    def load_csv(file_path):
        df = pd.read_csv(file_path)
        cols = ['PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing', 'HorzBreak', 'InducedVertBreak']
        for c in cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
        if 'PlateLocSide' in df.columns and df['PlateLocSide'].abs().max() < 10:
            df['PlateLocSide'] *= 30.48; df['PlateLocHeight'] *= 30.48
        return df

    # --- 3. データファイルの確認 ---
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if not files:
        st.error("dataフォルダにCSVファイルが見つかりません。ファイルをアップロードしてください。")
    else:
        # ==========================================
        # 📝 メインナビゲーション
        # ==========================================
        # タブを設置
        tab_p, tab_b = st.tabs(["🔥 投手分析", "⚾ 打者分析"])

        # ==========================================
        # 🔥 投手分析タブ
        # ==========================================
        with tab_p:
            st.sidebar.title("🔥 PITCHER SETTINGS")
            sel_file_p = st.sidebar.selectbox("分析ファイルを選択", files, key="p_file_select")
            df_p_all = load_csv(os.path.join(DATA_DIR, sel_file_p))
            
            p_col = 'Pitcher' if 'Pitcher' in df_p_all.columns else 'Pitcher Name'
            p_list = sorted(df_p_all[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list, key="p_name_select")
            
            p_sub = st.sidebar.radio("分析モード", ["総合レポート", "詳細分析", "比較分析"], key="p_mode_select")
            
            p_df = df_p_all[df_p_all[p_col] == sel_p].copy()
            st.header(f"📊 {sel_p} 投手 : {p_sub}")

            if p_sub == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in p_df['TaggedPitchType'].unique():
                        d = p_df[p_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_title("変化量(cm)"); ax.legend(); st.pyplot(fig)
                with c2:
                    st.subheader("球種別平均")
                    summary = p_df.groupby('TaggedPitchType').agg({'RelSpeed':'mean','SpinRate':'mean'}).reset_index()
                    st.dataframe(summary.style.format(precision=1))

            elif p_sub == "詳細分析":
                v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"], key="p_view_select")
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(); draw_strike_zone(ax)
                        d_s = p_df[p_df['BatterSide'] == side]
                        px = d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1)
                        ax.scatter(px, d_s['PlateLocHeight'], c='red', alpha=0.5, s=20)
                        ax.set_xlim(-80, 80); ax.set_ylim(0, 180); ax.set_title(f"対 {side}打者"); st.pyplot(fig)

        # ==========================================
        # ⚾ 打者分析タブ
        # ==========================================
        with tab_b:
            st.sidebar.markdown("---")
            st.sidebar.title("⚾ BATTER SETTINGS")
            sel_file_b = st.sidebar.selectbox("分析ファイルを選択", files, key="b_file_select")
            df_b_all = load_csv(os.path.join(DATA_DIR, sel_file_b))
            
            b_col = 'Batter' if 'Batter' in df_b_all.columns else 'Batter Name'
            b_list = sorted(df_b_all[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list, key="b_name_select")
            v_b = st.sidebar.radio("視点", ["投手目線", "捕手目線"], key="b_view_select")
            
            b_df = df_b_all[df_b_all[b_col] == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者分析")

            # コース別分析のフィルタ
            t_side = st.radio("表示対象（投手）", ["全投手", "対右投手", "対左投手"], horizontal=True, key="b_filter_radio")
            
            display_df = b_df.copy()
            if t_side == "対右投手": display_df = display_df[display_df['PitcherThrows'] == 'Right']
            elif t_side == "対左投手": display_df = display_df[display_df['PitcherThrows'] == 'Left']

            # --- コース別打球速度ヒートマップ ---
            st.subheader(f"🎯 コース別打球速度 (km/h) : {t_side}")
            if not display_df.empty:
                fig_h, ax_h = plt.subplots(figsize=(7, 7))
                draw_strike_zone(ax_h)
                
                # 3x3グリッド
                x_edges = np.linspace(-21.5, 21.5, 4)
                y_edges = np.linspace(45, 105, 4)
                px = display_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
                py = display_df['PlateLocHeight']
                
                for i in range(3):
                    for j in range(3):
                        mask = (px >= x_edges[j]) & (px < x_edges[j+1]) & (py >= y_edges[i]) & (py < y_edges[i+1])
                        cell = display_df[mask].dropna(subset=['ExitSpeed'])
                        if not cell.empty:
                            avg_v = cell['ExitSpeed'].mean()
                            color = cm.Reds(np.clip((avg_v - 100) / 60, 0.1, 0.9))
                            ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], facecolor=color, alpha=0.8, ec='white'))
                            ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{avg_v:.1f}\n(n={len(cell)})", ha='center', va='center', fontweight='bold')
                
                ax_h.set_xlim(-60, 60); ax_h.set_ylim(10, 160); plt.axis('off')
                st.pyplot(fig_h)
            else:
                st.info("該当するデータがありません。")
