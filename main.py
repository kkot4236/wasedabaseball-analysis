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
        ax.add_patch(plt.Circle((x_offset, 140), 8, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-15, 80], [x_offset+15, 80], [x_offset+18, 135], [x_offset-18, 135]]), color=color, alpha=alpha, zorder=1))

    def draw_field(ax):
        ax.plot([0, 90], [0, 90], color="gray", lw=1.5) 
        ax.plot([0, -90], [0, 90], color="gray", lw=1.5) 
        arc = np.linspace(-np.pi/4, np.pi/4, 100)
        ax.plot(120*np.sin(arc), 120*np.cos(arc), color="gray", lw=2)
        ax.set_aspect('equal'); ax.axis('off')

    # --- データ読み込み設定 ---
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    # ==========================================
    # 📝 サイドバー：メインナビゲーション
    # ==========================================
    st.sidebar.title("🚀 メインメニュー")
    mode = st.sidebar.radio("分析対象を選択", ["🔥 投手分析", "⚾ 打者分析"])

    # ==========================================
    # 🔥 投手分析モード
    # ==========================================
    if mode == "🔥 投手分析":
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔥 PITCHER SETTINGS")
        
        if files:
            sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="p_file_sel")
            df = pd.read_csv(os.path.join(DATA_DIR, sel_file))
            
            # データ補正
            for c in ['PlateLocSide', 'PlateLocHeight', 'HorzBreak', 'InducedVertBreak']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
            if 'PlateLocSide' in df.columns and df['PlateLocSide'].abs().max() < 10:
                df['PlateLocSide'] *= 30.48; df['PlateLocHeight'] *= 30.48
            
            p_col = 'Pitcher' if 'Pitcher' in df.columns else 'Pitcher Name'
            p_list = sorted(df[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            
            p_sub_mode = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析", "比較分析"])
            p_df = df[df[p_col] == sel_p].copy()
            p_throws = p_df['PitcherThrows'].iloc[0] if 'PitcherThrows' in p_df.columns else 'Right'

            # メイン表示
            st.title(f"📊 {sel_p} 投手：{p_sub_mode}")

            if p_sub_mode == "総合レポート":
                col1, col2 = st.columns(2)
                with col1:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in df['TaggedPitchType'].unique():
                        d = p_df[p_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_title("変化量(cm)"); ax.legend(fontsize=8); st.pyplot(fig)
                
                with col2:
                    st.subheader("📋 球種別パフォーマンス")
                    p_df['is_whiff'] = p_df['PitchCall'] == 'StrikeSwinging'
                    p_df['is_swing'] = p_df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
                    res = p_df.groupby('TaggedPitchType', observed=True).agg({'RelSpeed':'mean', 'SpinRate':'mean', p_col:'count'}).reset_index()
                    st.dataframe(res.style.format(precision=1), use_container_width=True)

            elif p_sub_mode == "詳細分析":
                v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"])
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                        draw_stylish_batter(ax, side, v_p)
                        d_s = p_df[p_df['BatterSide']==side]
                        px = d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1)
                        ax.scatter(px, d_s['PlateLocHeight'], c='red', alpha=0.5)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"対 {side}打者分布"); st.pyplot(fig)

        else:
            st.warning("dataフォルダにCSVファイルを入れてください。")

    # ==========================================
    # ⚾ 打者分析モード
    # ==========================================
    elif mode == "⚾ 打者分析":
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚾ BATTER SETTINGS")
        
        if files:
            sel_file_b = st.sidebar.selectbox("分析ファイルを選択", files, key="b_file_sel")
            df_b = pd.read_csv(os.path.join(DATA_DIR, sel_file_b))
            
            b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
            b_list = sorted(df_b[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="v_b_sel")
            
            b_df = df_b[df_b[b_col] == sel_b].copy()
            if 'PlateLocSide' in b_df.columns and b_df['PlateLocSide'].abs().max() < 10:
                b_df['PlateLocSide'] *= 30.48; b_df['PlateLocHeight'] *= 30.48

            st.title(f"🎯 {sel_b} 打者：総合分析")

            # 角度 & スプレー
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📐 角度別飛距離＆頻度")
                angle_data = b_df.dropna(subset=['Angle', 'Distance']).copy()
                if not angle_data.empty:
                    bins = np.arange(-30, 81, 10)
                    angle_data['bin'] = pd.cut(angle_data['Angle'], bins=bins)
                    bin_stats = angle_data.groupby('bin', observed=False).agg({'Distance':'mean', 'Angle':'count'}).reset_index()
                    bin_stats[['Distance', 'Angle']] = bin_stats[['Distance', 'Angle']].fillna(0)
                    total_cnt = bin_stats['Angle'].sum()
                    bin_stats['perc'] = (bin_stats['Angle'] / total_cnt * 100) if total_cnt > 0 else 0
                    
                    theta = np.deg2rad(bins[:-1] + 5)
                    fig_p = plt.figure(figsize=(6, 6)); ax_p = fig_p.add_subplot(111, polar=True)
                    ax_p.set_theta_zero_location('E'); ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                    cmap = cm.get_cmap('Oranges')
                    max_p = max(bin_stats['perc']) if max(bin_stats['perc']) > 0 else 1
                    ax_p.bar(theta, bin_stats['Distance'], width=np.deg2rad(10), color=[cmap(p/max_p) for p in bin_stats['perc']], edgecolor='black')
                    st.pyplot(fig_p)

            with c2:
                st.subheader("🏹 打球方向分布")
                spray_df = b_df.dropna(subset=['Bearing', 'Distance'])
                if not spray_df.empty:
                    fig_s, ax_s = plt.subplots(figsize=(6, 6))
                    draw_field(ax_s)
                    rad = np.deg2rad(spray_df['Bearing'])
                    ax_s.scatter(spray_df['Distance']*np.sin(rad), spray_df['Distance']*np.cos(rad), c='red', alpha=0.6, edgecolors='k')
                    st.pyplot(fig_s)

            st.markdown("---")
            # コース別ヒートマップ
            st.subheader("🎯 コース別詳細ヒートマップ")
            metric = st.selectbox("表示指標を選択", ["ExitSpeed", "Angle", "Distance"])
            m_map = {"ExitSpeed": ("Reds", 110, 160), "Angle": ("YlGn", 0, 40), "Distance": ("Blues", 40, 110)}
            cmap_n, vmin, vmax = m_map[metric]

            fig_h, ax_h = plt.subplots(figsize=(8, 8))
            draw_stylish_batter(ax_h, 'Right', v_b)
            x_edges = np.linspace(-21.5, 21.5, 4)
            y_edges = np.linspace(45, 105, 4)
            b_df['px'] = b_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
            
            for i in range(3):
                for j in range(3):
                    mask = (b_df['px'] >= x_edges[j]) & (b_df['px'] < x_edges[j+1]) & (b_df['PlateLocHeight'] >= y_edges[i]) & (b_df['PlateLocHeight'] < y_edges[i+1])
                    cell = b_df[mask].dropna(subset=[metric])
                    if not cell.empty:
                        val = cell[metric].mean()
                        color = plt.get_cmap(cmap_n)((val-vmin)/(vmax-vmin) if vmax!=vmin else 0.5)
                        ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], facecolor=color, alpha=0.8, ec='white'))
                        ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{val:.1f}\n(n={len(cell)})", ha='center', va='center', fontweight='bold')
            
            ax_h.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black', zorder=5))
            ax_h.set_xlim(-70, 70); ax_h.set_ylim(10, 160); ax_h.axis('off'); st.pyplot(fig_h)

        else:
            st.warning("dataフォルダにCSVファイルを入れてください。")
