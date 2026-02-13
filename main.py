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

    # --- 2. 共通設定・描画関数 ---
    PITCH_LIST = ['Fastball', 'Slider', 'Cutter', 'Curveball', 'Splitter', 'ChangeUp', 'Sinker', 'TwoSeamFastBall']
    PITCH_COLORS = {'Fastball': '#FF4B4B', 'Slider': '#1E90FF', 'Cutter': '#FF1493', 'Curveball': '#32CD32', 'Splitter': '#40E0D0', 'ChangeUp': '#8A2BE2', 'Sinker': '#FFA500', 'TwoSeamFastBall': '#FF8C00'}

    def get_marker(pitch_type, throws):
        if pitch_type == 'Fastball': return 'o'
        if pitch_type in ['Slider', 'Cutter']: return '<' if throws == 'Right' else '>'
        if pitch_type == 'Splitter': return 's'
        if pitch_type in ['ChangeUp', 'Sinker']: return 'v'
        if pitch_type in ['Curveball']: return '^'
        return 'o'

    def draw_stylish_batter(ax, batter_side='Right', view_mode="投手目線"):
        if view_mode == "投手目線":
            x_offset, flip = (55, -1) if batter_side == 'Right' else (-55, 1)
        else:
            x_offset, flip = (-55, 1) if batter_side == 'Right' else (55, -1)
        color, alpha = '#333333', 0.15
        ax.add_patch(plt.Circle((x_offset, 140), 6, color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-12, 85], [x_offset+12, 85], [x_offset+15, 135], [x_offset-15, 135]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset-10, 85], [x_offset-2, 85], [x_offset-15, 20], [x_offset-25, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+2, 85], [x_offset+10, 85], [x_offset+25, 20], [x_offset+15, 20]]), color=color, alpha=alpha, zorder=1))
        ax.add_patch(plt.Polygon(np.array([[x_offset+(15*flip), 125], [x_offset+(40*flip), 170], [x_offset+(48*flip), 167], [x_offset+(18*flip), 122]]), color=color, alpha=0.25, zorder=1))

    def display_full_pro_table(df):
        if df.empty: return
        total = len(df)
        df = df.copy()
        df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        df['is_whiff'] = df['PitchCall'] == 'StrikeSwinging'
        df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlayOut', 'Single', 'Double', 'Triple', 'HomeRun'])
        agg_map = {'RelSpeed': 'mean', 'SpinRate': 'mean', 'InducedVertBreak': 'mean', 'HorzBreak': 'mean'}
        actual_agg = {k: v for k, v in agg_map.items() if k in df.columns}
        actual_agg['Pitcher'] = 'count'
        res = df.groupby('TaggedPitchType', observed=True).agg(actual_agg).reset_index()
        whiff_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: (x['is_whiff'].sum() / x['is_swing'].sum() * 100) if x['is_swing'].sum() > 0 else 0).reset_index(name='Whiff%')
        strike_res = df.groupby('TaggedPitchType', observed=True).apply(lambda x: x['is_strike'].mean() * 100).reset_index(name='Strike%')
        res = res.merge(whiff_res, on='TaggedPitchType').merge(strike_res, on='TaggedPitchType')
        res['投球割合'] = res['Pitcher'].apply(lambda x: f"{x/total*100:.1f}% ({x}球)")
        res['TaggedPitchType'] = pd.Categorical(res['TaggedPitchType'], categories=PITCH_LIST, ordered=True)
        res = res.sort_values('TaggedPitchType').dropna(subset=['TaggedPitchType'])
        st.dataframe(res.rename(columns={'TaggedPitchType':'球種','RelSpeed':'平均(km/h)','SpinRate':'回転数','InducedVertBreak':'縦変化','HorzBreak':'横変化'}).style.format(precision=1), use_container_width=True, hide_index=True)

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
                    df['SeasonFile'] = f
                    all_data.append(df)
                except: pass
        return pd.concat(all_data, ignore_index=True) if all_data else None

    df_full = load_data()

    if df_full is not None:
        p_col, b_col = 'Pitcher', 'Batter Name'
        if p_col not in df_full.columns: p_col = 'Pitcher Name'
        if b_col not in df_full.columns: b_col = 'Batter'
        df_full['TaggedPitchType'] = df_full['TaggedPitchType'].replace('FourSeamFastBall', 'Fastball').fillna('Unknown')
        df_full['Date_str'] = pd.to_datetime(df_full['Date'], errors='coerce').dt.strftime('%Y-%m-%d')

        mode = st.radio("🏠 分析モード", ["🔥 投手分析", "⚾ 打者分析"], horizontal=True, label_visibility="collapsed")

        # --- 4. 投手分析 ---
        if mode == "🔥 投手分析":
            st.sidebar.title("🔥 PITCHER MENU")
            sel_p = st.sidebar.selectbox("投手を選択", sorted(df_full[p_col].unique()))
            p_mode = st.sidebar.radio("レポート形式", ["総合レポート", "詳細分析"])
            p_full = df_full[df_full[p_col] == sel_p].copy()
            target_p_df = p_full.copy()
            p_throws = target_p_df['PitcherThrows'].iloc[0] if not target_p_df.empty and 'PitcherThrows' in target_p_df.columns else 'Right'
            
            st.header(f"📊 {sel_p} 投手：分析結果")
            if p_mode == "総合レポート":
                c1, c2 = st.columns(2)
                with c1:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k'); ax.axhline(0, color='k')
                    for pt in PITCH_LIST:
                        d = target_p_df[target_p_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzBreak'], d['InducedVertBreak'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.set_xlim(-80,80); ax.set_ylim(-80,80); ax.set_title("変化量(cm)"); st.pyplot(fig)
                with c2:
                    fig, ax = plt.subplots(); ax.axvline(0, color='k'); ax.axhline(0, color='k')
                    for pt in PITCH_LIST:
                        d = target_p_df[target_p_df['TaggedPitchType']==pt]
                        if not d.empty: ax.scatter(d['HorzRelAngle'], d['VertRelAngle'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6, marker=get_marker(pt, p_throws))
                    ax.set_xlim(-6,6); ax.set_ylim(-6,6); ax.set_title("リリース角"); st.pyplot(fig)
                display_full_pro_table(target_p_df)
            else:
                p_item = st.sidebar.radio("項目", ["到達位置", "3Dリリース", "カウント別"])
                if p_item == "到達位置":
                    c1, c2 = st.columns(2)
                    for side, col in [('Right', c1), ('Left', c2)]:
                        with col:
                            fig, ax = plt.subplots(); ax.add_patch(plt.Rectangle((-21.5, 45), 43, 60, fill=False, lw=2))
                            d_s = target_p_df[target_p_df['BatterSide']==side]
                            for pt in target_p_df['TaggedPitchType'].unique():
                                d_p = d_s[d_s['TaggedPitchType']==pt]
                                if not d_p.empty: ax.scatter(d_p['PlateLocSide'], d_p['PlateLocHeight'], color=PITCH_COLORS.get(pt,'gray'), label=pt, alpha=0.6)
                            ax.set_xlim(-100,100); ax.set_ylim(0,200); ax.set_title(f"対 {side}打者"); st.pyplot(fig)
                display_full_pro_table(target_p_df)

        # --- 5. 打者分析 (レイアウト修正版) ---
        elif mode == "⚾ 打者分析":
            st.sidebar.title("⚾ BATTER MENU")
            sel_b = st.sidebar.selectbox("打者を選択", sorted(df_full[b_col].unique()))
            analysis_target = st.sidebar.radio("指標選択", ["打球速度", "打球角度 (deg)", "飛距離 (m)"])
            view_mode = st.sidebar.radio("表示視点", ["投手目線", "捕手目線"])
            
            b_full = df_full[df_full[b_col] == sel_b].copy()
            st.header(f"🎯 {sel_b} 打者：総合分析レポート")

            if not b_full.empty:
                b_full['PlateLocSide_Plot'] = b_full['PlateLocSide'] * (-1 if view_mode == "捕手目線" else 1)
                b_hand = b_full['BatterSide'].mode()[0] if not b_full['BatterSide'].dropna().empty else 'Right'
                if analysis_target == "打球速度": target_col, v_min, v_max, cmap, unit = 'ExitSpeed', 100, 165, 'Reds', ""
                elif analysis_target == "打球角度 (deg)": target_col, v_min, v_max, cmap, unit = 'Angle', 0, 45, 'viridis', "°"
                else: target_col, v_min, v_max, cmap, unit = 'Distance', 30, 110, 'Blues', "m"

                # A. TOTALレイアウト（ヒートマップ | 角度分布）
                st.subheader("📊 全体傾向 (TOTAL)")
                col_heat, col_angle = st.columns([1.2, 0.8]) # 左を少し広めに

                with col_heat:
                    fig_t, ax_t = plt.subplots(figsize=(7, 6))
                    draw_stylish_batter(ax_t, b_hand, view_mode)
                    x_edges = [-36.5, -21.5, -7.17, 7.17, 21.5, 36.5]
                    y_edges = [30.0, 45.0, 65.0, 85.0, 105.0, 120.0]
                    for r in range(5):
                        for c in range(5):
                            x_min, x_max, y_min, y_max = x_edges[c], x_edges[c+1], y_edges[4-r], y_edges[5-r]
                            z_data = b_full[(b_full['PlateLocSide_Plot'] >= x_min) & (b_full['PlateLocSide_Plot'] < x_max) & (b_full['PlateLocHeight'] >= y_min) & (b_full['PlateLocHeight'] < y_max)]
                            if not z_data.empty:
                                val = z_data[target_col].mean()
                                norm = (val - v_min) / (v_max - v_min)
                                color = plt.get_cmap(cmap)(np.clip(norm, 0, 1))
                                ax_t.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.8, ec='white', lw=0.5, zorder=2))
                                ax_t.text((x_min+x_max)/2, (y_min+y_max)/2, f"{val:.1f}{unit}\nn={len(z_data)}", ha='center', va='center', fontsize=9, fontweight='bold', color='white' if norm > 0.6 and cmap!='Reds' else 'black', zorder=3)
                    ax_t.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2, zorder=4))
                    ax_t.set_xlim(-90, 90); ax_t.set_ylim(10, 180); ax_t.set_aspect('equal'); ax_t.axis('off'); ax_t.set_title(f"コース別 {analysis_target}", fontsize=12)
                    st.pyplot(fig_t)

                with col_angle:
                    angle_data = b_full.dropna(subset=['Angle'])
                    if not angle_data.empty:
                        bins = np.arange(-30, 80, 10)
                        counts, _ = np.histogram(angle_data['Angle'], bins=bins)
                        percentages = (counts / len(angle_data)) * 100
                        theta = np.deg2rad(np.arange(-25, 75, 10))
                        
                        fig_p = plt.figure(figsize=(6, 5))
                        ax_p = fig_p.add_subplot(111, polar=True)
                        ax_p.set_theta_zero_location('E'); ax_p.set_theta_direction(1)
                        colors = ['#FF8C00' if 10<=b<30 else '#ADD8E6' if b>=30 else '#90EE90' for b in np.arange(-30, 70, 10)]
                        ax_p.bar(theta, percentages, width=np.deg2rad(10), color=colors, edgecolor='black', alpha=0.8)
                        ax_p.plot(0, 0, marker='o', markersize=10, color='black', zorder=5)
                        ax_p.set_thetamin(-40); ax_p.set_thetamax(90)
                        ax_p.set_xticks(np.deg2rad(np.arange(-30, 81, 20)))
                        ax_p.set_xticklabels([f"{i}°" for i in range(-30, 81, 20)], fontsize=8)
                        ax_p.set_yticklabels([])
                        ax_p.set_title("打球角度分布", fontsize=12)
                        for t, p in zip(theta, percentages):
                            if p > 2: ax_p.text(t, p + 3, f"{int(p)}%", ha='center', fontsize=8, fontweight='bold')
                        st.pyplot(fig_p)

                st.markdown("---")
                # B. 左右別比較
                st.subheader("⚔️ 左右別比較")
                cl, cr = st.columns(2)
                for side, col in [('Right', cl), ('Left', cr)]:
                    with col:
                        subset = b_full[b_full['PitcherThrows'] == side]
                        fig_s, ax_s = plt.subplots(figsize=(8, 6))
                        draw_stylish_batter(ax_s, b_hand, view_mode)
                        for r in range(5):
                            for c in range(5):
                                x_min, x_max, y_min, y_max = x_edges[c], x_edges[c+1], y_edges[4-r], y_edges[5-r]
                                z_data = subset[(subset['PlateLocSide_Plot'] >= x_min) & (subset['PlateLocSide_Plot'] < x_max) & (subset['PlateLocHeight'] >= y_min) & (subset['PlateLocHeight'] < y_max)]
                                if not z_data.empty:
                                    val = z_data[target_col].mean()
                                    color = plt.get_cmap(cmap)(np.clip((val - v_min) / (v_max - v_min), 0, 1))
                                    ax_s.add_patch(plt.Rectangle((x_min, y_min), x_max-x_min, y_max-y_min, color=color, alpha=0.8, ec='white', lw=0.5))
                                    ax_s.text((x_min+x_max)/2, (y_min+y_max)/2, f"{val:.1f}\nn={len(z_data)}", ha='center', va='center', fontsize=8, fontweight='bold')
                        ax_s.add_patch(plt.Rectangle((-21.5, 45.0), 43.0, 60.0, fill=False, edgecolor='black', lw=2))
                        ax_s.set_xlim(-90, 90); ax_s.set_ylim(10, 180); ax_s.axis('off'); ax_s.set_title(f"VS {side.upper()} P", fontsize=13)
                        st.pyplot(fig_s)
    else:
        st.error("データが読み込めませんでした。")
