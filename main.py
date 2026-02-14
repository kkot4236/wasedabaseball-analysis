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

    def draw_strike_zone(ax, side='Right', view="投手目線"):
        # ストライクゾーン枠 (cm基準)
        ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=3, ec='black', zorder=5))
        # 打者シルエットの位置計算
        x_off = 60 if (view == "投手目線" and side == 'Right') or (view == "捕手目線" and side == 'Left') else -60
        ax.add_patch(plt.Circle((x_off, 140), 8, color='#333333', alpha=0.15))
        ax.add_patch(plt.Polygon(np.array([[x_off-15, 80], [x_off+15, 80], [x_off+18, 135], [x_off-18, 135]]), color='#333333', alpha=0.15))

    def draw_field(ax):
        ax.plot([0, 90], [0, 90], color="gray", lw=1.5) 
        ax.plot([0, -90], [0, 90], color="gray", lw=1.5) 
        arc = np.linspace(-np.pi/4, np.pi/4, 100)
        ax.plot(120*np.sin(arc), 120*np.cos(arc), color="gray", lw=2)
        ax.set_aspect('equal'); ax.axis('off')

    @st.cache_data
    def load_csv(file_path):
        df = pd.read_csv(file_path)
        # 数値への強制変換
        cols = ['PlateLocSide', 'PlateLocHeight', 'HorzBreak', 'InducedVertBreak', 'RelSpeed', 'SpinRate', 'ExitSpeed', 'Angle', 'Distance', 'Bearing']
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        # 単位変換 ft -> cm (Trackman)
        # 板の端が21.5cmなので、値が小さい場合はftと判断して変換
        if 'PlateLocSide' in df.columns and df['PlateLocSide'].abs().max() < 10:
            df['PlateLocSide'] *= 30.48
            df['PlateLocHeight'] *= 30.48
        return df

    # ==========================================
    # 📝 メインナビゲーション (サイドバー連動型)
    # ==========================================
    st.sidebar.title("🚀 メインメニュー")
    mode = st.sidebar.radio("分析対象を選択", ["🔥 投手分析", "⚾ 打者分析"])
    DATA_DIR = "data"
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')] if os.path.exists(DATA_DIR) else []

    # ==========================================
    # 🔥 投手分析セクション
    # ==========================================
    if mode == "🔥 投手分析":
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔥 PITCHER SETTINGS")
        if files:
            sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="p_file_nav")
            df = load_csv(os.path.join(DATA_DIR, sel_file))
            p_col = 'Pitcher' if 'Pitcher' in df.columns else 'Pitcher Name'
            p_list = sorted(df[p_col].dropna().unique())
            sel_p = st.sidebar.selectbox("投手を選択", p_list)
            p_sub = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析（左右別）", "比較分析"])
            p_df = df[df[p_col] == sel_p].copy()

            if p_sub == "総合レポート":
                st.header(f"📊 {sel_p} : 総合レポート")
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(figsize=(6,6))
                    ax.axvline(0, color='k', lw=0.5); ax.axhline(0, color='k', lw=0.5)
                    for pt in p_df['TaggedPitchType'].unique():
                        d = p_df[p_df['TaggedPitchType']==pt]
                        ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                    ax.set_xlim(-80, 80); ax.set_ylim(-80, 80); ax.set_title("変化量(cm)"); ax.legend(); st.pyplot(fig)
                with c2:
                    st.subheader("📋 球種別スタッツ")
                    summary = p_df.groupby('TaggedPitchType').agg({'RelSpeed':'mean','SpinRate':'mean',p_col:'count'}).rename(columns={p_col:'球数'}).reset_index()
                    st.dataframe(summary.style.format(precision=1), use_container_width=True)

            elif p_sub == "詳細分析（左右別）":
                st.header(f"🎯 {sel_p} : 左右別コース分布")
                v_p = st.sidebar.radio("視点", ["投手目線", "捕手目線"])
                c1, c2 = st.columns(2)
                for side, col in [('Right', c1), ('Left', c2)]:
                    with col:
                        fig, ax = plt.subplots(figsize=(6,7))
                        draw_strike_zone(ax, side, v_p)
                        d_s = p_df[p_df['BatterSide'] == side]
                        px = d_s['PlateLocSide'] * (-1 if v_p == "捕手目線" else 1)
                        for pt in d_s['TaggedPitchType'].unique():
                            m = d_s['TaggedPitchType'] == pt
                            ax.scatter(px[m], d_s.loc[m, 'PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                        ax.set_xlim(-100, 100); ax.set_ylim(0, 200); ax.set_title(f"対 {side}打者"); ax.legend(); st.pyplot(fig)

            elif p_sub == "比較分析":
                st.header("⚖️ 投手比較")
                sel_p2 = st.sidebar.selectbox("比較相手を選択", [p for p in p_list if p != sel_p])
                p2_df = df[df[p_col] == sel_p2].copy()
                col1, col2 = st.columns(2)
                for name, data, c in [(sel_p, p_df, col1), (sel_p2, p2_df, col2)]:
                    with c:
                        fig, ax = plt.subplots(); ax.axvline(0, color='k'); ax.axhline(0, color='k')
                        for pt in data['TaggedPitchType'].unique():
                            d = data[data['TaggedPitchType']==pt]
                            ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.5)
                        ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title(name); st.pyplot(fig)

    # ==========================================
    # ⚾ 打者分析セクション
    # ==========================================
    elif mode == "⚾ 打者分析":
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚾ BATTER SETTINGS")
        if files:
            sel_file = st.sidebar.selectbox("分析ファイルを選択", files, key="b_file_nav")
            df_b = load_csv(os.path.join(DATA_DIR, sel_file))
            b_col = 'Batter' if 'Batter' in df_b.columns else 'Batter Name'
            b_list = sorted(df_b[b_col].dropna().unique())
            sel_b = st.sidebar.selectbox("打者を選択", b_list)
            v_b = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"], key="v_b_nav")
            t_side = st.sidebar.radio("投手左右", ["すべて", "対右投手", "対左投手"])
            
            b_df = df_b[df_b[b_col] == sel_b].copy()
            if t_side == "対右投手": b_df = b_df[b_df['PitcherThrows'] == 'Right']
            elif t_side == "対左投手": b_df = b_df[b_df['PitcherThrows'] == 'Left']

            st.header(f"🎯 {sel_b} : {t_side} 分析")
            
            # --- 上段: 角度分布 & スプレーチャート ---
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("📐 角度別飛距離＆頻度")
                ang_d = b_df.dropna(subset=['Angle', 'Distance'])
                if not ang_d.empty:
                    bins = np.arange(-30, 81, 10)
                    ang_d['bin'] = pd.cut(ang_d['Angle'], bins=bins)
                    stats = ang_d.groupby('bin', observed=False).agg({'Distance':'mean', 'Angle':'count'}).reset_index()
                    theta = np.deg2rad(bins[:-1] + 5)
                    fig_p = plt.figure(figsize=(6, 6)); ax_p = fig_p.add_subplot(111, polar=True)
                    ax_p.set_theta_zero_location('E'); ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                    ax_p.bar(theta, stats['Distance'].fillna(0), width=np.deg2rad(10), color='orange', edgecolor='black', alpha=0.7)
                    st.pyplot(fig_p)

            with c2:
                st.subheader("🏹 打球方向分布")
                sp_d = b_df.dropna(subset=['Bearing', 'Distance'])
                if not sp_d.empty:
                    fig_s, ax_s = plt.subplots(figsize=(6, 6)); draw_field(ax_s)
                    rad = np.deg2rad(sp_d['Bearing'])
                    ax_s.scatter(sp_d['Distance']*np.sin(rad), sp_d['Distance']*np.cos(rad), c='blue', alpha=0.6, edgecolors='k')
                    st.pyplot(fig_s)

            st.markdown("---")
            # --- 下段: コース別詳細ヒートマップ (修正版) ---
            st.subheader("🎯 コース別打球速度 (km/h)")
            
            # 指標の選択
            metric = "ExitSpeed" 
            fig_h, ax_h = plt.subplots(figsize=(8, 8))
            draw_strike_zone(ax_h, 'Right', v_b)
            
            # グリッド定義 (左右は-21.5~21.5, 高さは45~105)
            x_edges = np.linspace(-21.5, 21.5, 4)
            y_edges = np.linspace(45, 105, 4)
            
            # 視点による座標反転
            b_df['px'] = b_df['PlateLocSide'] * (-1 if v_b == "捕手目線" else 1)
            
            for i in range(3): # 高さ
                for j in range(3): # 横
                    # セル範囲を少し広めに設定して境界上のデータを拾う
                    mask = (b_df['px'] >= x_edges[j]-1) & (b_df['px'] < x_edges[j+1]+1) & \
                           (b_df['PlateLocHeight'] >= y_edges[i]-1) & (b_df['PlateLocHeight'] < y_edges[i+1]+1)
                    cell = b_df[mask].dropna(subset=[metric])
                    
                    if not cell.empty:
                        val = cell[metric].mean()
                        count = len(cell)
                        # 色の設定 (100km/h以下は薄く、160km/h以上は濃く)
                        color = cm.Reds(np.clip((val - 100) / 60, 0.1, 0.9))
                        ax_h.add_patch(plt.Rectangle((x_edges[j], y_edges[i]), x_edges[j+1]-x_edges[j], y_edges[i+1]-y_edges[i], facecolor=color, alpha=0.8, ec='white'))
                        ax_h.text((x_edges[j]+x_edges[j+1])/2, (y_edges[i]+y_edges[i+1])/2, f"{val:.1f}\n(n={count})", ha='center', va='center', fontweight='bold', fontsize=12)

            ax_h.set_xlim(-70, 70); ax_h.set_ylim(20, 160); ax_h.axis('off')
            st.pyplot(fig_h)

        else:
            st.warning("dataフォルダにCSVファイルを入れてください。")
