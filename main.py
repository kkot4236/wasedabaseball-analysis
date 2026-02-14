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

    # --- 2. 描画用共通関数 ---
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

    # ==========================================
    # 📝 ナビゲーション管理 (タブとサイドバーの連動)
    # ==========================================
    # URLやセッション状態に依存せず、サイドバーのラジオボタンを主軸にします
    # これにより「タブの切り替え」＝「モードの切り替え」を明示的に行います
    st.sidebar.title("🚀 メインメニュー")
    mode = st.sidebar.radio("分析対象を選択", ["🔥 投手分析", "⚾ 打者分析"])

    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    if not files:
        st.error("dataフォルダにCSVファイルが見つかりません。")
    else:
        # ==========================================
        # 🔥 投手分析モード
        # ==========================================
        if mode == "🔥 投手分析":
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔥 投手用設定")
            sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="p_file")
            df = load_csv(os.path.join(DATA_DIR, sel_file))
            
            p_col = 'Pitcher' if 'Pitcher' in df.columns else 'Pitcher Name'
            p_list = sorted(df[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            p_sub = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析", "比較分析"])
            
            p_df = df[df[p_col] == sel_p].copy()
            st.title(f"📊 {sel_p} 投手：{p_sub}")

            if p_sub == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in p_df['TaggedPitchType'].unique():
                        d = p_df[p_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_title("変化量(cm)"); ax.legend(); st.pyplot(fig)
                with c2:
                    summary = p_df.groupby('TaggedPitchType').agg({'RelSpeed':'mean','SpinRate':'mean'}).reset_index()
                    st.table(summary.style.format(precision=1))

            elif p_sub == "詳細分析":
                v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"])
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(); draw_strike_zone(ax)
                        d_s = p_df[p_df['BatterSide'] == side]
                        ax.scatter(d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1), d_s['PlateLocHeight'], c='red', alpha=0.5)
                        ax.set_xlim(-80, 80); ax.set_ylim(0, 180); ax.set_title(f"対 {side}打者"); st.pyplot(fig)

        # ==========================================
        # ⚾ 打者分析モード
        # ==========================================
        elif mode == "⚾ 打者分析":
            st.sidebar.markdown("---")
            st.sidebar.subheader("⚾ 打者用設定")
            sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="b_file")
            df = load_csv(os.path.join(DATA_DIR, sel_file))
            
            b_col = 'Batter' if 'Batter' in df.columns else 'Batter Name'
            b_list = sorted(df[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            v_b = st.sidebar.radio("視点", ["投手目線", "捕手目線"])
            
            # --- 打者分析のメインメニュー：投手左右切り替え ---
            st.title(f"🎯 {sel_b} 打者分析")
            t_side = st.radio("表示する投手タイプ", ["全投手", "対右投手", "対左投手"], horizontal=True)

            b_df = df[df[b_col] == sel_b].copy()
            # 投手左右でデータを完全にフィルタリング
            if t_side == "対右投手":
                display_df = b_df[b_df['PitcherThrows'] == 'Right'].copy()
            elif t_side == "対左投手":
                display_df = b_df[b_df['PitcherThrows'] == 'Left'].copy()
            else:
                display_df = b_df.copy()

            # --- コース別打球速度ヒートマップ ---
            st.subheader(f"🎯 コース別平均打球速度 ({t_side})")
            if not display_df.empty:
                fig_h, ax_h = plt.subplots(figsize=(7, 7))
                draw_strike_zone(ax_h)
                
                # グリッド定義
                x_edges = np.linspace(-21.5, 21.5, 4)
                y_edges = np.linspace(45, 105, 4)
                px = display_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
                py = display_df['PlateLocHeight']
                
                for i in range(3): # 高さ
                    for j in range(3): # 横
                        mask = (px >= x_edges[j]) & (px < x_edges[j+1]) & (py >= y_edges[i]) & (py < y_edges[i+1])
                        cell = display_df[mask].dropna(subset=['ExitSpeed'])
                        if not cell.empty:
                            avg_v = cell['ExitSpeed'].mean()
                            color = cm.Reds(np.clip((avg_v - 100) / 60, 0.1, 0.9))
                            ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], facecolor=color, alpha=0.8, ec='white'))
                            ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{avg_v:.1f}\n(n={len(cell)})", ha='center', va='center', fontweight='bold', fontsize=12)
                
                ax_h.set_xlim(-70, 70); ax_h.set_ylim(10, 160); plt.axis('off')
                st.pyplot(fig_h)
            else:
                st.warning(f"{t_side}のデータが存在しません。")
