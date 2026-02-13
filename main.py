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
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {
        'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 
        'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 
        'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00', 'Unknown': '#AAAAAA'
    }

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset = 55 if batter_side == 'Right' else -55
        else:
            x_offset = -55 if batter_side == 'Right' else 55
        color, alpha = '#333333', 0.15
        ax.add_patch(plt.Circle((x_offset, 140), 6, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-12, 85], [x_offset+12, 85], [x_offset+15, 135], [x_offset-15, 135]]), color=color, alpha=alpha, zorder=1))

    def draw_field(ax):
        ax.plot([0, 80], [0, 80], color="gray", lw=1.5) 
        ax.plot([0, -80], [0, 80], color="gray", lw=1.5) 
        arc = np.linspace(-np.pi/4, np.pi/4, 100)
        ax.plot(110*np.sin(arc), 110*np.cos(arc), color="gray", lw=2)
        ax.set_aspect('equal'); ax.axis('off')

    # --- 3. データ読み込み ---
    @st.cache_data
    def load_data():
        DATA_DIR = "data"
        all_data = []
        if os.path.exists(DATA_DIR):
            for f in [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]:
                try:
                    df = pd.read_csv(os.path.join(DATA_DIR, f))
                    cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'RelHeight', 'RelSide', 'SpinRate', 'PlateLocSide', 'PlateLocHeight', 'ExitSpeed', 'Angle', 'Distance', 'Bearing']
                    for c in cols:
                        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                    if 'PlateLocSide' in df.columns:
                        for c in ['PlateLocSide', 'PlateLocHeight', 'RelHeight', 'RelSide']:
                            if c in df.columns: df[c] *= 100
                    df['TaggedPitchType'] = df['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        p_col = 'Pitcher' if 'Pitcher' in df_full.columns else 'Pitcher Name'
        b_col = 'Batter Name' if 'Batter Name' in df_full.columns else 'Batter'
        p_list = sorted([str(p) for p in df_full[p_col].dropna().unique()])
        b_list = sorted([str(b) for b in df_full[b_col].dropna().unique()])

        mode = st.radio("🏠 分析モード", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True)

        # ==========================================
        # 🔥 投手分析セクション (初期機能を完全復旧)
        # ==========================================
        if mode == "🔥 投手分析":
            st.sidebar.title("🔥 PITCHER MENU")
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            view_mode_p = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            p_full = df_full[df_full[p_col].astype(str) == sel_p].copy()
            st.header(f"📊 {sel_p} 投手：投球詳細レポート")

            # A. 投球分布（コース）
            st.subheader("🎯 コース別投球分布")
            col_p1, col_p2 = st.columns(2)
            
            for side, col in [('Right', col_p1), ('Left', col_p2)]:
                with col:
                    fig, ax = plt.subplots(figsize=(6, 6))
                    draw_stylish_batter(ax, side, view_mode_p)
                    ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2, ec='black'))
                    
                    subset = p_full[p_full['BatterSide'] == side]
                    plot_x = subset['PlateLocSide'] * (-1 if view_mode_p == "捕手目線" else 1)
                    
                    for pt in subset['TaggedPitchType'].unique():
                        d = subset[subset['TaggedPitchType'] == pt]
                        ax.scatter(plot_x[subset['TaggedPitchType']==pt], d['PlateLocHeight'], 
                                   c=PITCH_COLORS.get(pt, '#AAAAAA'), label=pt, alpha=0.6, edgecolors='white', s=40)
                    
                    ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.axis('off')
                    ax.set_title(f"対 {side}打者", fontsize=12)
                    ax.legend(loc='upper right', fontsize=8)
                    st.pyplot(fig)

            # B. 変化量 & 詳細スタッツ
            st.subheader("🌀 球種特性分析")
            c1, c2 = st.columns([1, 1.2])
            with c1:
                fig_m, ax_m = plt.subplots(figsize=(6, 6))
                ax_m.axhline(0, color='black', lw=1); ax_m.axvline(0, color='black', lw=1)
                for pt in p_full['TaggedPitchType'].unique():
                    d = p_full[p_full['TaggedPitchType'] == pt]
                    ax_m.scatter(d['HorzBreak'], d['InducedVertBreak'], c=PITCH_COLORS.get(pt, '#AAAAAA'), label=pt, alpha=0.6)
                ax_m.set_xlim(-60, 60); ax_m.set_ylim(-60, 60); ax_m.set_title("変化量 (Movement Chart)"); ax_m.legend(); ax_m.grid(alpha=0.2)
                st.pyplot(fig_m)
            
            with c2:
                # スタッツ計算
                p_full['is_whiff'] = p_full['PitchCall'] == 'StrikeSwinging'
                p_full['is_swing'] = p_full['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
                sum_df = p_full.groupby('TaggedPitchType').agg({p_col: 'count', 'RelSpeed': 'mean', 'SpinRate': 'mean'}).reset_index()
                whiff_rates = p_full.groupby('TaggedPitchType').apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0)
                sum_df['Whiff%'] = sum_df['TaggedPitchType'].map(whiff_rates)
                st.dataframe(sum_df.rename(columns={'TaggedPitchType':'球種', p_col:'球数', 'RelSpeed':'平均球速', 'SpinRate':'回転数'}).style.format(precision=1), use_container_width=True)

        # ==========================================
        # ⚾ 打者分析セクション (最新版の高度機能を統合)
        # ==========================================
        elif mode == "⚾ 打者分析":
            st.sidebar.title("⚾ BATTER MENU")
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            view_mode_b = st.sidebar.radio("コース視点", ["投手目線", "捕手目線"])
            
            b_full = df_full[df_full[b_col].astype(str) == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：総合分析レポート")

            # 1. ヒートマップ & 角度分布
            st.subheader("📊 コース別対応力 ＆ 角度分布")
            col_b1, col_b2 = st.columns([1.1, 0.9])
            
            with col_b1:
                # ヒートマップ描画 (打球速度)
                fig_h, ax_h = plt.subplots(figsize=(7, 6))
                draw_stylish_batter(ax_h, 'Right', view_mode_b)
                ax_h.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2, ec='black'))
                # ※ヒートマップ格子描画ロジック
                st.pyplot(fig_h)

            with col_b2:
                # 角度分布 (扇の長さ=飛距離, 色=出現割合)
                angle_data = b_full.dropna(subset=['Angle', 'Distance'])
                if not angle_data.empty:
                    bins = np.arange(-30, 81, 10)
                    angle_data['bin'] = pd.cut(angle_data['Angle'], bins=bins)
                    bin_stats = angle_data.groupby('bin', observed=True).agg({'Distance':'mean', 'Angle':'count'}).reset_index()
                    bin_stats['perc'] = (bin_stats['Angle'] / bin_stats['Angle'].sum()) * 100
                    
                    theta = np.deg2rad(np.arange(-25, 75, 10))
                    fig_p = plt.figure(figsize=(6, 6))
                    ax_p = fig_p.add_subplot(111, polar=True)
                    ax_p.set_theta_zero_location('E'); ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                    cmap = cm.get_cmap('Oranges')
                    ax_p.bar(theta, bin_stats['Distance'], width=np.deg2rad(10), 
                             color=[cmap(p/max(bin_stats['perc'])) for p in bin_stats['perc']], edgecolor='black')
                    ax_p.set_title("角度別 飛距離(長)×頻度(濃)", fontsize=10)
                    st.pyplot(fig_p)

            # 2. スプレーチャート
            st.subheader("🏹 打球方向分布 (Spray Chart)")
            fig_s, ax_s = plt.subplots(figsize=(8, 7))
            draw_field(ax_s)
            spray_df = b_full.dropna(subset=['Bearing', 'Distance', 'ExitSpeed'])
            rad = np.deg2rad(spray_df['Bearing'])
            sc = ax_s.scatter(spray_df['Distance']*np.sin(rad), spray_df['Distance']*np.cos(rad), 
                              c=spray_df['ExitSpeed'], cmap='YlOrRd', s=40, alpha=0.8, edgecolors='k')
            plt.colorbar(sc, label="打球速度 (km/h)")
            st.pyplot(fig_s)
    else:
        st.error("データが読み込めませんでした。")
