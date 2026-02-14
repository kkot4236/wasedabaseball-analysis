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

    # --- 共通描画関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00', 'Unknown': '#AAAAAA'}

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        x_offset = 60 if (view_mode == "投手目線" and batter_side == 'Right') or (view_mode == "捕手目線" and batter_side == 'Left') else -60
        color, alpha = '#333333', 0.1
        ax.add_patch(plt.Circle((x_offset, 140), 8, color=color, alpha=alpha))
        ax.add_patch(plt.Polygon(np.array([[x_offset-15, 80], [x_offset+15, 80], [x_offset+18, 135], [x_offset-18, 135]]), color=color, alpha=alpha))

    # --- データ読み込み ---
    @st.cache_data
    def load_all_data():
        DATA_DIR = "data"
        files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
        return files

    files = load_all_data()
    
    # タブ設定
    tab_p, tab_b = st.tabs(["🔥 投手分析", "⚾ 打者分析"])

    # ==========================================
    # 🔥 投手分析タブ
    # ==========================================
    with tab_p:
        st.sidebar.title("🔥 PITCHER SETTINGS")
        sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="p_file")
        df = pd.read_csv(os.path.join("data", sel_file))
        
        # 数値変換と単位補正
        for c in ['PlateLocSide', 'PlateLocHeight', 'HorzBreak', 'InducedVertBreak']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        if df['PlateLocSide'].abs().max() < 10:
            df['PlateLocSide'] *= 30.48; df['PlateLocHeight'] *= 30.48

        p_col = 'Pitcher' if 'Pitcher' in df.columns else 'Pitcher Name'
        p_list = sorted(df[p_col].dropna().unique())
        sel_p = st.sidebar.selectbox("投手を選択", p_list)
        
        p_mode = st.sidebar.radio("分析モード", ["総合レポート", "詳細分析", "比較分析"])
        p_df = df[df[p_col] == sel_p].copy()

        if p_mode == "総合レポート":
            st.header(f"📊 {sel_p} : 総合レポート")
            c1, c2 = st.columns(2)
            with c1:
                fig, ax = plt.subplots(); ax.axvline(0, color='k'); ax.axhline(0, color='k')
                for pt in df['TaggedPitchType'].unique():
                    d = p_df[p_df['TaggedPitchType']==pt]
                    ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                ax.set_title("変化量(cm)"); ax.legend(); st.pyplot(fig)
            
            # 球種別スタッツ表
            st.subheader("📋 球種別スタッツ")
            stats = p_df.groupby('TaggedPitchType').agg({'RelSpeed':'mean', 'SpinRate':'mean', p_col:'count'}).reset_index()
            st.dataframe(stats.style.format(precision=1))

        elif p_mode == "詳細分析":
            st.header(f"🎯 {sel_p} : コース詳細分析")
            v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"], key="v_p")
            c1, c2 = st.columns(2)
            for side, col in [('Right', c1), ('Left', c2)]:
                with col:
                    fig, ax = plt.subplots(); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                    draw_stylish_batter(ax, side, v_p)
                    d_s = p_df[p_df['BatterSide']==side]
                    px = d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1)
                    ax.scatter(px, d_s['PlateLocHeight'], c='red', alpha=0.5)
                    ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"対 {side}打者"); st.pyplot(fig)

        elif p_mode == "比較分析":
            st.header("⚖️ 投手比較分析")
            comp_p = st.sidebar.selectbox("比較対象を選択", p_list)
            # 比較用ロジック...

    # ==========================================
    # ⚾ 打者分析タブ
    # ==========================================
    with tab_b:
        st.sidebar.title("⚾ BATTER SETTINGS")
        sel_file_b = st.sidebar.selectbox("分析ファイルを選択", files, key="b_file")
        df_b = pd.read_csv(os.path.join("data", sel_file_b))
        
        b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
        b_list = sorted(df_b[b_col].dropna().unique())
        sel_b = st.sidebar.selectbox("打者を選択", b_list)
        v_b = st.sidebar.radio("視点", ["投手目線", "捕手目線"], key="v_b")
        b_df = df_b[df_b[b_col] == sel_b].copy()

        # 座標補正
        if b_df['PlateLocSide'].abs().max() < 10:
            b_df['PlateLocSide'] *= 30.48; b_df['PlateLocHeight'] *= 30.48

        st.header(f"🎯 {sel_b} : 打撃分析")

        # 1. 角度・スプレー
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📐 角度別飛距離＆頻度")
            # 扇形チャートの描画 (前述の修正版ロジック)
            angle_data = b_df.dropna(subset=['Angle', 'Distance']).copy()
            if not angle_data.empty:
                bins = np.arange(-30, 81, 10)
                angle_data['bin'] = pd.cut(angle_data['Angle'], bins=bins)
                bin_stats = angle_data.groupby('bin', observed=False).agg({'Distance':'mean', 'Angle':'count'}).reset_index()
                bin_stats[['Distance', 'Angle']] = bin_stats[['Distance', 'Angle']].fillna(0)
                theta = np.deg2rad(bins[:-1] + 5)
                fig_p = plt.figure(figsize=(6, 6)); ax_p = fig_p.add_subplot(111, polar=True)
                ax_p.set_theta_zero_location('E'); ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                ax_p.bar(theta, bin_stats['Distance'], width=np.deg2rad(10), color='orange', edgecolor='black', alpha=0.7)
                st.pyplot(fig_p)

        with c2:
            st.subheader("🏹 打球方向分布")
            spray_df = b_df.dropna(subset=['Bearing', 'Distance'])
            if not spray_df.empty:
                fig_s, ax_s = plt.subplots(figsize=(6, 6))
                ax_s.plot([0, 90], [0, 90], color="gray"); ax_s.plot([0, -90], [0, 90], color="gray")
                rad = np.deg2rad(spray_df['Bearing'])
                ax_s.scatter(spray_df['Distance']*np.sin(rad), spray_df['Distance']*np.cos(rad), c='blue', alpha=0.6)
                ax_s.set_aspect('equal'); ax_s.axis('off'); st.pyplot(fig_s)

        st.markdown("---")
        # 2. コース別詳細ヒートマップ
        st.subheader("🎯 コース別データ")
        metric = st.selectbox("表示指標", ["ExitSpeed", "Angle", "Distance"])
        fig_h, ax_h = plt.subplots(figsize=(8, 8))
        draw_stylish_batter(ax_h, 'Right', v_b)
        x_edges, y_edges = np.linspace(-21.5, 21.5, 4), np.linspace(45, 105, 4)
        b_df['px'] = b_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
        for i in range(3):
            for j in range(3):
                mask = (b_df['px'] >= x_edges[j]) & (b_df['px'] < x_edges[j+1]) & (b_df['PlateLocHeight'] >= y_edges[i]) & (b_df['PlateLocHeight'] < y_edges[i+1])
                cell = b_df[mask].dropna(subset=[metric])
                if not cell.empty:
                    val = cell[metric].mean()
                    ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], color='red', alpha=0.3))
                    ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{val:.1f}\n(n={len(cell)})", ha='center', va='center')
        ax_h.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black'))
        ax_h.set_xlim(-70, 70); ax_h.set_ylim(10, 160); ax_h.axis('off'); st.pyplot(fig_h)
